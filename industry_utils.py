# [산업 추출 모듈] 산업/업종 추출 및 카테고리 매핑 기능을 담당합니다.
from bs4 import BeautifulSoup
import requests

INDUSTRY_CODE_MAP = {
    "28202": "이차전지 제조업",
    "26101": "반도체 제조업",
}

INDUSTRY_CATEGORY_MAP = {
    "반도체 제조업": "반도체",
    "자동차 부품 제조업": "제조",
    "디스플레이 제조업": "전자",
    "은행업": "금융",
    "제약업": "바이오",
    "석유화학": "화학",
    "화학의 전지사업": "화학",
    "배터리업": "에너지",
    "태양광 사업": "에너지",
    "바이오산업": "바이오",
    "철강 제조업": "철강",
    "전자부품 제조업": "전자",
    "정보통신업": "IT",
}

def search_ksic_industry_name(ksic_code):
    url = f"https://kssc.kostat.go.kr/spss/search/ksicSearch.do?searchWord={ksic_code}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            result = soup.find("td", class_="left")
            if result:
                return result.text.strip()
    except Exception as e:
        print("KSIC 검색 실패:", e)
    return None

def search_industries_by_company(company_name, naver_client_id=None, naver_client_secret=None, dart_api_key=None, llm_api_key=None):
    """
    1. 네이버 백과사전에서 산업명 추출
    2. DART 회사정보에서 업종명 추출 시도
    3. KSIC 코드로 산업명 추출 시도
    4. 그래도 없으면 LLM에 회사명+뉴스로 산업 추정 프롬프트 호출
    """
    import re
    industries = set()
    # 1) 네이버 백과사전 시도
    try:
        headers = {"X-Naver-Client-Id": naver_client_id, "X-Naver-Client-Secret": naver_client_secret}
        url = "https://openapi.naver.com/v1/search/encyc.json"
        params = {"query": f"{company_name} 산업", "display": 3}
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            items = response.json().get('items', [])
            for item in items:
                desc = item.get('description', '')
                found = re.findall(r"([가-힣A-Za-z0-9 ]{2,}(제조업|업|서비스|산업|업종))", desc)
                for (industry, _) in found:
                    clean = industry.strip()
                    if len(clean) > 3:
                        industries.add(clean)
    except Exception as e:
        print("[DEBUG] 네이버 백과사전 산업 추출 예외:", e)
    # 2) DART 회사정보 업종명 시도
    if not industries and dart_api_key is not None:
        try:
            from dart_api import get_corp_code, get_company_info
            corp_code = get_corp_code(dart_api_key, company_name)
            info = get_company_info(dart_api_key, corp_code)
            biz = info.get('company', {}).get('biz_name') or info.get('company', {}).get('industry')
            if biz and isinstance(biz, str) and len(biz) > 2:
                industries.add(biz.strip())
        except Exception as e:
            print("[DEBUG] DART 업종명 추출 예외:", e)
    # 3) KSIC 코드로 산업명 시도
    if not industries and dart_api_key is not None:
        try:
            from dart_api import get_corp_code, get_company_info
            corp_code = get_corp_code(dart_api_key, company_name)
            info = get_company_info(dart_api_key, corp_code)
            ksic_code = info.get('company', {}).get('ksic_code')
            if ksic_code:
                industry_ksic = search_ksic_industry_name(ksic_code)
                if industry_ksic:
                    industries.add(industry_ksic)
        except Exception as e:
            print("[DEBUG] KSIC 산업 추출 예외:", e)
    # 4) LLM 산업 추정 프롬프트 (최대 4개, 쉼표 구분)
    if not industries and llm_api_key is not None:
        try:
            from llm_utils import query_llm
            prompt = f"'{company_name}'의 주요 산업(업종)명을 한글로 최대 4개까지, 쉼표로 구분해서 추정해줘. 예시: 반도체, IT, 바이오, 제조, 전자, 금융, 화학, 철강, 에너지 등. 반드시 산업명만 답변해줘."
            industry_llm = query_llm(llm_api_key, prompt, temperature=0.7).strip()
            if industry_llm and len(industry_llm) > 1:
                for ind in industry_llm.split(','):
                    clean = ind.strip()
                    if len(clean) > 1:
                        industries.add(clean)
        except Exception as e:
            print("[DEBUG] LLM 산업 추정 예외:", e)
    # 유사/중복 제거: 완전일치/부분일치 우선, 최대 4개
    def dedup_similar(ind_list):
        result = []
        for ind in ind_list:
            if not any(ind in r or r in ind for r in result):
                result.append(ind)
            if len(result) >= 4:
                break
        return result
    if not industries:
        print("[DEBUG] 산업명 추출 실패. 모든 Fallback 경로 실패.")
    return dedup_similar(list(industries))

def map_to_category(industry_name, llm_api_key=None):
    if industry_name in INDUSTRY_CATEGORY_MAP:
        return INDUSTRY_CATEGORY_MAP[industry_name]
    if llm_api_key:
        from llm_utils import query_llm
        prompt = (
            f"'{industry_name}'을(를) 아래 카테고리 중 가장 적합한 하나로 분류해줘. 반드시 한 단어만 반환.\n"
            f"카테고리 후보: 에너지, 철강, 바이오, 제조, 금융, IT, 전자, 화학, 반도체"
        )
        cat = query_llm(llm_api_key, prompt, temperature=0.8).strip()
        for allowed in ["에너지", "철강", "바이오", "제조", "금융", "IT", "전자", "화학", "반도체"]:
            if allowed in cat:
                return allowed
        return "기타"
    return "기타"
