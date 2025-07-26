# LLM 연동 및 텍스트 요약/분석 유틸리티
import requests
import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def extract_risk_related_chunks(chunk_summaries, risk_keywords, max_count=10):
    # chunk 요약에서 리스크 관련 chunk 우선 추출
    def contains_risk(chunk):
        chunk_l = chunk.lower()
        return any(kw.lower() in chunk_l for kw in risk_keywords if kw.strip())
    # 1. Select all risk-related chunks (no duplicates, preserve order)
    risk_chunks = [c for c in chunk_summaries if contains_risk(c)]
    # 2. Fill up to max_count with non-risk chunks (preserve order, skip if already included)
    rest_chunks = [c for c in chunk_summaries if c not in risk_chunks]
    selected = risk_chunks[:max_count]
    for c in rest_chunks:
        if len(selected) >= max_count:
            break
        selected.append(c)
    return selected

def query_llm(llm_api_key, prompt, temperature=0.8):
    # OpenAI LLM 호출 (정상 동작 버전)
    import requests
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {llm_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": temperature
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            print(f"[LLM API ERROR] status={response.status_code}, body={response.text[:200]}")
            return ""
    except Exception as e:
        print(f"[LLM API EXCEPTION] {e}")
        return ""

def extract_risk_keywords_llm(disclosures, llm_api=None):
    # 공시에서 리스크 키워드 추출
    disclosure_texts = '\n'.join([
        item.get('report_nm', '') + ' ' + item.get('title', '')
        for item in disclosures.get('list', [])
    ])
    if not disclosure_texts.strip():
        return [], "공시 텍스트 없음"
    prompt_keywords = f"""
    아래는 최근 공시 내용입니다. 리스크 관련 키워드를 5개 이내로 추출해줘.\n[공시 텍스트]\n{disclosure_texts[:2000]}
    """
    risk_keywords_str = query_llm(llm_api, prompt_keywords, temperature=0.7)
    risk_keywords = [kw.strip() for kw in risk_keywords_str.split(',') if kw.strip()]
    prompt_summary = f"""
    아래는 최근 공시 내용입니다. 위에서 추출한 리스크 키워드별로 실제 언급된 부분을 중심으로 요약해줘.\n키워드별로 소제목을 붙여서 정리해줘.\n\n[키워드]\n{', '.join(risk_keywords)}\n[공시 텍스트]\n{disclosure_texts[:2000]}
    """
    summary = query_llm(llm_api, prompt_summary, temperature=0.8)
    return risk_keywords, summary

def extract_risk_keywords_from_disclosures(disclosures, keywords=None):
    # 공시에서 리스크 키워드 포함 항목 추출
    if keywords is None:
        keywords = ["핵심감사사항", "의견거절", "한정의견", "부적정의견", "내부회계관리제도", "리스크", "위험"]
    report = []
    for item in disclosures.get('list', []):
        text = item.get('report_nm', '') + ' ' + item.get('title', '')
        found = [kw for kw in keywords if kw in text]
        if found:
            report.append(f"[{item['rcept_dt']}] {item['report_nm']} - Keywords: {', '.join(found)}")
    if not report:
        return "No risk-related keywords found in recent disclosures."
    return '\n'.join(report)

def summarize_texts_in_chunks(texts, llm_api_key, chunk_size=5, max_chunk_chars=1500):
    # 여러 텍스트를 chunk별 병렬 LLM 요약
    import concurrent.futures
    def summarize_chunk(chunk):
        joined_chunk = "\n".join(chunk)
        if len(joined_chunk) > max_chunk_chars:
            joined_chunk = joined_chunk[:max_chunk_chars]
        prompt = f"아래 텍스트들을 2~3문장으로 요약해줘:\n{joined_chunk}"
        summary = query_llm(llm_api_key, prompt, temperature=0.8)
        return summary.strip() if summary.strip() else '(LLM 요약 결과 없음)'

    summarized = []
    chunks = [texts[i:i+chunk_size] for i in range(0, len(texts), chunk_size)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(chunks))) as executor:
        results = list(executor.map(summarize_chunk, chunks))
    summarized.extend(results)
    return summarized
