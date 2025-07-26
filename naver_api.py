# [네이버 API 모듈] 네이버 오픈API(뉴스, 백과) 연동 기능을 담당합니다.
import requests
import os
from dotenv import load_dotenv

load_dotenv()
# run.py에서 직접 입력한 키를 import해서 사용합니다.
def get_news_from_naver(company_name, since_date, max_news=10, max_length=600, return_count=False, naver_client_id=None, naver_client_secret=None):
    if naver_client_id is None or naver_client_secret is None:
        raise ValueError("naver_client_id와 naver_client_secret을 반드시 인자로 전달해야 합니다.")
    headers = {"X-Naver-Client-Id": naver_client_id, "X-Naver-Client-Secret": naver_client_secret}
    url = "https://openapi.naver.com/v1/search/news.json"
    params = {"query": company_name, "sort": "date", "display": max_news, "start": 1}
    response = requests.get(url, headers=headers, params=params)
    response.encoding = 'utf-8'  # 인코딩 명시

    if response.status_code == 200:
        # 인코딩 문제 진단용: response.text를 잠시 출력
        try:
            items = response.json().get('items', [])[:max_news]
        except Exception as e:
            print('response.text:', response.text[:500])
            print('response.content:', response.content[:500])
            print('JSON decode error:', e)
            return ("(뉴스 응답 인코딩 오류)", 0) if return_count else "(뉴스 응답 인코딩 오류)"
        texts = [(item['title'] + ' ' + item['description'])[:max_length] for item in items]
        count = len(texts)
        if not texts:
            return ("(최근 1년 뉴스 없음)", 0) if return_count else "(최근 1년 뉴스 없음)"
        return ("\n".join(texts), count) if return_count else "\n".join(texts)
    else:
        print("네이버 뉴스 API 호출 실패", response.status_code)
        return ("", 0) if return_count else ""