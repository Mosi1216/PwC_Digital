# [재무분석 모듈] 재무비율 분석, 계산 및 시각화 기능을 담당합니다.

import os
import pandas as pd
import numpy as np
from dart_api import fetch_financial_statements
from utils import ensure_korean_font

def fetch_financial_statements(api_key, corp_code, year, fs_div="CFS"):
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": year,
        "reprt_code": "11011",
        "fs_div": fs_div
    }
    import requests
    import json
    r = requests.get(url, params=params)
    if r.status_code != 200:
        print(f"Failed to get financials for year {year} ({fs_div}): {r.status_code}")
        return None
    try:
        return json.loads(r.content.decode('utf-8'))
    except UnicodeDecodeError:
        try:
            return json.loads(r.content.decode('euc-kr'))
        except Exception as e:
            print(f"[ERROR] JSON decode 실패(euc-kr): {e}")
            print(f"[DEBUG] 응답 일부: {r.content[:200]}")
            return None
    except Exception as e:
        print(f"[ERROR] JSON decode 실패: {e}")
        print(f"[DEBUG] 응답 일부: {r.content[:200]}")
        return None

def analyze_financial_ratios_multi_year(api_key, corp_code, years):
    results = {}
    prev_sales = None
    import difflib
    for year in years:
        # 1차: CFS(연결) 시도
        fin = fetch_financial_statements(api_key, corp_code, year, fs_div="CFS")
        used_fs_div = "CFS"
        if not fin or 'list' not in fin or not fin['list']:
            # 2차: OFS(별도) fallback
            fin = fetch_financial_statements(api_key, corp_code, year, fs_div="OFS")
            used_fs_div = "OFS"
        if not fin or 'list' not in fin or not fin['list']:
            # 해당 연도 데이터가 없으면 결과에 포함하지 않고 건너뜀 (경고 출력도 생략)
            continue
        
        if len(fin['list']) > 0:
            sample_accounts = list({item.get('account_nm','') for item in fin['list'] if 'account_nm' in item})[:20]
            
        df = pd.DataFrame(fin['list'])
        import re
        # 표구분별 계정명 후보군 설정
        account_candidates_by_sj = {
            '재무상태표': {
                'ca': ['유동자산','유동 자산','유동자산계','유동자산총계','CurrentAssets','TotalCurrentAssets'],
                'cl': ['유동부채','유동 부채','유동부채계','유동부채총계','CurrentLiabilities','TotalCurrentLiabilities'],
                'ta': ['자산총계','총자산','자산 총계','총 자산','자산총액','TotalAssets','AssetsTotal'],
                'tl': ['부채총계','총부채','부채 총계','총 부채','부채총액','TotalLiabilities','LiabilitiesTotal'],
                'eq': ['자본총계','총자본','자본 총계','총 자본','자본총액','TotalEquity','EquityTotal'],
            },
            '포괄손익계산서': {
                'ni': ['당기순이익','순이익','당기순이익(손실)','당기순손실','NetIncome','NetProfit','분기순이익','반기순이익','분기순손익','반기순손익'],
                'sales': ['매출액','매출','수익','영업수익','영업매출','매출총액','Revenue','Sales'],
                'op_profit': ['영업이익','영업손익','영업이익(손실)','영업손실','OperatingProfit','OperatingIncome'],
                'int_exp': ['이자비용','이자 비용','금융비용','이자','InterestExpense','Interest'],
            },
            '손익계산서': {
                'ni': ['당기순이익','순이익','당기순이익(손실)','당기순손실','NetIncome','NetProfit','분기순이익','반기순이익','분기순손익','반기순손익'],
                'sales': ['매출액','매출','수익','영업수익','영업매출','매출총액','Revenue','Sales'],
                'op_profit': ['영업이익','영업손익','영업이익(손실)','영업손실','OperatingProfit','OperatingIncome'],
                'int_exp': ['이자비용','이자 비용','금융비용','이자','InterestExpense','Interest'],
            },
        }
        # 표구분별 데이터 분리
        sj_groups = dict(tuple(df.groupby('sj_nm')))
        # get_account 함수(표별 적용)
        def get_account(subdf, names):
            if isinstance(names, str):
                names = [names]
            def normalize(s):
                return re.sub(r'[\s\(\)]', '', str(s)).lower()
            if 'account_nm' not in subdf:
                print(f"[경고] account_nm 컬럼 없음")
                return None
            subdf['account_nm_norm'] = subdf['account_nm'].apply(normalize)
            for name in names:
                name_norm = normalize(name)
                matched = subdf[subdf['account_nm_norm'].str.contains(name_norm)]
                if not matched.empty:
                    try:
                        val = matched.iloc[0]['thstrm_amount']
                        return float(str(val).replace(",", ""))
                    except Exception as e:
                        continue
            # 유사 계정명 추천
            candidates = list(subdf['account_nm'].unique())
            close_matches = []
            for name in names:
                close_matches += difflib.get_close_matches(name, candidates, n=3, cutoff=0.6)
            
            return None
        # 표별로 계정 추출
        ca = cl = ta = tl = eq = ni = sales = op_profit = int_exp = None
        # 재무상태표
        for sj in ['재무상태표']:
            if sj in sj_groups:
                subdf = sj_groups[sj]
                ca = get_account(subdf, account_candidates_by_sj[sj]['ca'])
                cl = get_account(subdf, account_candidates_by_sj[sj]['cl'])
                ta = get_account(subdf, account_candidates_by_sj[sj]['ta'])
                tl = get_account(subdf, account_candidates_by_sj[sj]['tl'])
                eq = get_account(subdf, account_candidates_by_sj[sj]['eq'])
        # 포괄손익계산서/손익계산서
        for sj in ['포괄손익계산서','손익계산서']:
            if sj in sj_groups:
                subdf = sj_groups[sj]
                ni = get_account(subdf, account_candidates_by_sj[sj]['ni'])
                sales = get_account(subdf, account_candidates_by_sj[sj]['sales'])
                op_profit = get_account(subdf, account_candidates_by_sj[sj]['op_profit'])
                int_exp = get_account(subdf, account_candidates_by_sj[sj]['int_exp'])

        ca = get_account(df, ['유동자산','유동 자산'])
        cl = get_account(df, ['유동부채','유동 부채'])
        ta = get_account(df, ['자산총계','총자산','자산 총계','총 자산'])
        tl = get_account(df, ['부채총계','총부채','부채 총계','총 부채'])
        eq = get_account(df, ['자본총계','총자본','자본 총계','총 자본'])
        ni = get_account(df, [
            '당기순이익','순이익','당기순이익(손실)','당기순손실','지배기업의 소유주에게 귀속되는 당기순이익(손실)',
            '지배기업 소유주지분', '지배기업의 소유주에게 귀속되는 당기순이익', '비지배지분에 귀속되는 당기순이익(손실)'])
        sales = get_account(df, [
            '매출액','매출','수익','영업수익','영업매출','매출총액','수익(매출액)','영업수익(손실)','영업수익(매출액)','영업수익(영업매출)','영업수익(수익)','영업수익(매출총액)'])
        op_profit = get_account(df, [
            '영업이익','영업손익','영업이익(손실)','영업손실','영업이익(이익)','영업이익(영업손실)','영업이익(영업이익)'])
        int_exp = get_account(df, ['이자비용','이자 비용','금융비용','이자'])
        current_ratio = ca / cl * 100 if ca and cl else None
        debt_ratio = tl / eq * 100 if tl and eq else None
        roa = ni / ta * 100 if ni and ta else None
        roe = ni / eq * 100 if ni and eq else None
        sales_growth = ((sales - prev_sales) / prev_sales * 100) if sales and prev_sales else None
        op_margin = op_profit / sales * 100 if op_profit and sales else None
        net_margin = ni / sales * 100 if ni and sales else None
        asset_turnover = sales / ta if sales and ta else None
        int_cov = op_profit / int_exp if op_profit and int_exp and int_exp != 0 else None
        results[year] = {
            '연도': year,
            '유동비율(%)': current_ratio,
            '부채비율(%)': debt_ratio,
            'ROA(%)': roa,
            'ROE(%)': roe,
            '매출액증가율(%)': sales_growth,
            '영업이익률(%)': op_margin,
            '순이익률(%)': net_margin,
            '총자산회전율(회)': asset_turnover,
            '이자보상배율(배)': int_cov
        }
        prev_sales = sales
    all_rows = []
    for year in years:
        if results.get(year) is None:
            all_rows.append({
                '연도': year,
                '유동비율(%)': np.nan,
                '부채비율(%)': np.nan,
                'ROA(%)': np.nan,
                'ROE(%)': np.nan,
                '매출액증가율(%)': np.nan,
                '영업이익률(%)': np.nan,
                '순이익률(%)': np.nan,
                '총자산회전율(회)': np.nan,
                '이자보상배율(배)': np.nan
            })
        else:
            all_rows.append(results[year])
    return pd.DataFrame(all_rows)

def export_to_csv(df, company_name, filename):
    if df is not None:
        # 연도 기준 오름차순(과거→최신) 정렬
        if '연도' in df.columns:
            df = df.sort_values('연도', ascending=True)
        os.makedirs(f"results/{company_name}", exist_ok=True)
        df.to_csv(f"results/{company_name}/{filename}", index=False, encoding='utf-8-sig')
    full_path = os.path.join("results", company_name, filename)
    print(f"[Tableau용 CSV 저장 완료] {full_path}")

def plot_financial_ratios(df, company_name, filename=None):
    ensure_korean_font()
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False
    df = df.sort_values('연도', ascending=True)  # 연도 오름차순 정렬
    years = df['연도'].astype(str)
    metrics = ['유동비율(%)', '부채비율(%)', 'ROA(%)', 'ROE(%)', '매출액증가율(%)', '영업이익률(%)', '순이익률(%)', '총자산회전율(회)', '이자보상배율(배)']
    n = len(metrics)
    ncols = 3
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(5*ncols, 4*nrows))
    axes = axes.flatten()
    for i, metric in enumerate(metrics):
        ax = axes[i]
        if metric in df.columns:
            ax.plot(years, df[metric], marker='o', label=metric)
            ax.set_title(metric)
            ax.set_xlabel('연도')
            ax.set_ylabel(metric)
            ax.legend()
    # 빈 subplot 숨기기
    for j in range(i+1, len(axes)):
        fig.delaxes(axes[j])
    plt.suptitle(f'{company_name} 주요 재무비율 추이', fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    if filename is None:
        filename = f"results/{company_name}/{company_name}_재무비율.png"
    else:
        filename = f"results/{company_name}/{filename}"
    plt.savefig(filename)
    plt.close()
    print(f"[재무비율 그래프 저장 완료] {filename}")
