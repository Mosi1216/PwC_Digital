# 뉴스 요약 모듈] 네이버 뉴스 수집 및 LLM 뉴스 요약 기능을 제공합니다.
from naver_api import get_news_from_naver
from llm_utils import query_llm
from utils import clean_news_text

def news_search_and_summary_with_risk(company_name, since_date, financial_summary, llm_api_key=None, naver_client_id=None, naver_client_secret=None, min_news=40):
    # 뉴스 검색 및 요약 (정상 동작 버전)
    from naver_api import get_news_from_naver
    import datetime
    news_list = []
    warn = ''
    cur_since = since_date
    try:
        cur_date = datetime.datetime.strptime(since_date, '%Y%m%d')
    except Exception:
        cur_date = datetime.datetime.now() - datetime.timedelta(days=365)
        cur_since = cur_date.strftime('%Y%m%d')
    for attempt in range(5):
        raw_news = get_news_from_naver(company_name, cur_since, max_news=40, naver_client_id=naver_client_id, naver_client_secret=naver_client_secret)
        from utils import clean_news_text
        cleaned_news = clean_news_text(raw_news)
        news_list = [n.strip() for n in cleaned_news.split('\n') if n.strip()]
        if len(news_list) >= 40:
            break
        cur_date = cur_date - datetime.timedelta(days=180)
        cur_since = cur_date.strftime('%Y%m%d')
    if len(news_list) < min_news:
        warn = f"[경고] 최근 뉴스가 {len(news_list)}건으로 40건 미만입니다."
    # LLM 뉴스 chunk 요약 적용
    from llm_utils import summarize_texts_in_chunks, extract_risk_related_chunks
    risk_keywords = ["리스크", "위험", "부정", "손실", "소송", "규제", "부실", "우려", "사고", "불법", "하락", "적자"]
    if news_list:
        news_min_chunks = 7
        news_max_chunks = 10
        news_list_limited = news_list[:40] if len(news_list) > 40 else news_list
        if len(news_list_limited) < news_min_chunks:
            news_chunk_size = 1
        else:
            news_chunk_size = max(1, len(news_list_limited) // news_max_chunks)
        chunk_summaries = summarize_texts_in_chunks(news_list_limited, llm_api_key, chunk_size=news_chunk_size)
        if chunk_summaries and len(chunk_summaries) < news_min_chunks:
            chunk_summaries = summarize_texts_in_chunks(news_list_limited, llm_api_key, chunk_size=1)
        chunk_summaries = chunk_summaries[:news_max_chunks] if chunk_summaries else []
        selected_chunks = extract_risk_related_chunks(chunk_summaries, risk_keywords, max_count=news_max_chunks)
        news_summary = "\n".join([f"[뉴스 chunk {i+1}] {s}" for i, s in enumerate(selected_chunks)])
    else:
        news_summary = "(요약 없음)"
    if warn:
        return warn + "\n" + news_summary
    return news_summary

    