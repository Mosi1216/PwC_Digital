# [DART API 모듈] DART 연동, 기업정보/공시/재무데이터 수집 기능을 담당합니다.
import requests
import os
from dotenv import load_dotenv
import zipfile
import xml.etree.ElementTree as ET

load_dotenv()
DART_API_KEY = os.getenv("DART_API_KEY")

def get_corp_code(api_key, company_name):
    """회사명을 입력받아 DART corp_code를 반환"""
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    
    r = requests.get(url, params={"crtfc_key": api_key})
    if r.status_code != 200:
        raise Exception(f"Failed to download corpCode.xml: {r.status_code}")
    with open("corpCode.zip", "wb") as f:
        f.write(r.content)
    with zipfile.ZipFile("corpCode.zip", 'r') as zip_ref:
        zip_ref.extractall(".")
    tree = ET.parse("CORPCODE.xml")
    root = tree.getroot()
    for corp in root.findall('list'):
        if corp.find('corp_name').text == company_name:
            return corp.find('corp_code').text
    raise Exception(f"Company '{company_name}' not found in corpCode.xml.")

def get_company_info(api_key, corp_code):
    """corp_code로 DART에서 회사 기본정보 조회"""
    url = "https://opendart.fss.or.kr/api/company.json"
    params = {"crtfc_key": api_key, "corp_code": corp_code}
    r = requests.get(url, params=params)
    if r.status_code != 200:
        raise Exception(f"Failed to get company info: {r.status_code}")
    return r.json()

def get_disclosures(api_key, corp_code, bgn_de='20240101', end_de=None, page_count=10):
    """corp_code로 DART에서 최근 공시목록 조회"""
    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": bgn_de,
        "page_count": page_count
    }
    if end_de:
        params["end_de"] = end_de
    r = requests.get(url, params=params)
    if r.status_code != 200:
        raise Exception(f"Failed to get disclosures: {r.status_code}")
    return r.json()

def filter_disclosures(disclosures, years, max_count=20):
    import re
    year_set = set(str(y) for y in years)
    wanted_reports = ['사업보고서', '감사보고서', '재무제표']
    filtered = []
    for item in disclosures.get('list', []):
        report_nm = item.get('report_nm', '')
        rcept_dt = item.get('rcept_dt', '')
        year = rcept_dt[:4]
        if year in year_set and any(w in report_nm for w in wanted_reports):
            filtered.append(item)
        if len(filtered) >= max_count:
            break
    if len(filtered) < max_count:
        for item in disclosures.get('list', []):
            rcept_dt = item.get('rcept_dt', '')
            year = rcept_dt[:4]
            if year in year_set and item not in filtered:
                filtered.append(item)
            if len(filtered) >= max_count:
                break
    return filtered[:max_count]

def fetch_financial_statements(api_key, corp_code, year):
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": year,
        "reprt_code": "11011",
        "fs_div": "CFS"
    }
    r = requests.get(url, params=params)
    if r.status_code != 200:
        print(f"Failed to get financials for year {year}: {r.status_code}")
        return None
    return r.json()

def get_recent_filings(api_key, corp_code, since_date, count=40, max_length=600, return_count=False):
    """
    종류 무관 최신순 공시 count개 반환
    """
    filings = []
    used = set()
    page = 1
    while len(filings) < count:
        disclosures = get_disclosures(api_key, corp_code, bgn_de=since_date, page_count=100, end_de=None)
        for item in disclosures.get('list', []):
            key = (item.get('rcept_dt',''), item.get('report_nm',''))
            if key in used:
                continue
            date = item.get('rcept_dt', '')
            title = item.get('report_nm', '')
            summary = item.get('title', '') if 'title' in item else ''
            text = f"[{date}] {title} {summary}"
            filings.append(text[:max_length])
            used.add(key)
            if len(filings) >= count:
                break
        if len(disclosures.get('list', [])) < 100:
            break
        page += 1
    warn = ''
    if len(filings) < count:
        warn = f"[경고] 최근 공시가 {len(filings)}건으로 {count}건 미만입니다."
    result = ('\n'.join(filings), len(filings)) if return_count else '\n'.join(filings)
    if warn:
        if return_count:
            return (warn + '\n' + result[0], len(filings))
        else:
            return warn + '\n' + result
    return result

def get_yearly_key_reports(api_key, corp_code, years, max_length=1000):
    """
    각 연도별 사업보고서/감사보고서/재무제표만 추출(최대 3*len(years))
    반환값: [(연도, 보고서명, 텍스트)]
    """
    wanted_reports = ['사업보고서', '감사보고서', '재무제표']
    result = []
    for year in years:
        disclosures = get_disclosures(api_key, corp_code, bgn_de=f'{year}0101', end_de=f'{year}1231', page_count=100)
        for report in wanted_reports:
            for item in disclosures.get('list', []):
                if report in item.get('report_nm', ''):
                    date = item.get('rcept_dt', '')
                    title = item.get('report_nm', '')
                    summary = item.get('title', '') if 'title' in item else ''
                    text = f"[{date}] {title} {summary}"
                    result.append((year, title, text[:max_length]))
                    break  # 연도별 각 보고서 1개만
    return result

