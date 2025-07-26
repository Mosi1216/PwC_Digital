# 기업 리스크 요약 및 파일 저장
from llm_utils import query_llm, summarize_texts_in_chunks
from utils import save_summary_to_file
from industry_utils import map_to_category, search_industries_by_company
from dart_api import get_corp_code, get_recent_filings, get_yearly_key_reports
from news import news_search_and_summary_with_risk
import time
import pandas as pd

# 연도별 주요보고서 요약 및 키워드 추출
def format_yearly_key_reports(yearly_key_reports, llm_api_key, skip_llm=False):
    from collections import defaultdict
    results = []
    grouped = defaultdict(list)
    for year, report_name, text in yearly_key_reports:
        grouped[year].append((report_name, text))
    for year in sorted(grouped.keys(), reverse=True):
        results.append(f"[{year}]")
        for report_name, text in grouped[year]:
            if skip_llm:
                results.append(f"- {report_name}\n  원문: {text.strip()[:200]} ...")
                results.append(f"  (데이터 부족으로 LLM 요약/키워드 생략)")
            else:
                # LLM 요약
                prompt = f"아래는 {year}년 {report_name} 주요 내용입니다. 핵심 내용을 2-3문장으로 요약해줘.\n{text}"
                try:
                    summary = query_llm(llm_api_key, prompt, temperature=0.8).strip()
                except Exception:
                    summary = "(LLM 요약 실패)"
                kw_prompt = f"아래 텍스트에서 리스크(위험, 부정, 우려, 부실, 손실, 규제, 소송, 부채, 부정적 변화 등)와 관련된 핵심 키워드만 한글로 5개 이내로 추출해줘. 키워드만 콤마로 구분해서 답변해줘.\n{text}"
                try:
                    keywords = query_llm(llm_api_key, kw_prompt, temperature=0.7).strip()
                except Exception as e:
                    keywords = "(LLM 키워드 추출 실패)"
                    print(f"[ERROR] LLM 키워드 추출 실패: {e}")
                results.append(f"- {report_name}\n  요약: {summary}\n  리스크 키워드: {keywords}")
    return results

def summarize_company_risks(company_name, api_key, llm_api_key, since_date, financial_summary, naver_client_id=None, naver_client_secret=None):
    # 산업/카테고리 및 리스크 키워드/이슈 추출
    corp_code = get_corp_code(api_key, company_name)
    industries = []
    industry_risk_keywords = ""
    # (1) LLM 기반 산업명 직접 추출
    import textwrap
    try:
        from llm_utils import query_llm
        
        print(f"[DEBUG] LLM 기반 산업명 추출 시작: {company_name}")
        
        # LLM에 회사명을 직접 질의하여 산업명 추출
        industry_prompt = f"""{company_name}의 주요 산업 분야를 2-3개 나열해주세요.
다음 규칙을 따라주세요:
1. 회사명이 아닌 실제 산업 분야만 나열해주세요
2. 각 산업명은 한 줄에 하나씩 나열해주세요
3. 불필요한 설명이나 부연 설명 없이 산업명만 간단히 나열해주세요

예시:
배터리
에너지저장
전기차"""
        
        llm_response = query_llm(llm_api_key, industry_prompt, temperature=0.3)
        
        if llm_response and llm_response.strip():
            # LLM 응답에서 산업명 추출
            industries = [line.strip() for line in llm_response.strip().split('\n') if line.strip()]
            # 빈 문자열이나 너무 짧은 것 제거
            industries = [ind for ind in industries if len(ind) >= 2 and len(ind) <= 20]
            print(f"[DEBUG] LLM에서 추출된 산업명: {industries}")
        else:
            print("[DEBUG] LLM 산업명 추출 실패, 기본값 사용")
            industries = ["기타"]

        
        if not industries:
            print("[DEBUG] 산업명 추출 실패, 추가 fallback 시도")
            # 추가 fallback: 회사명에서 직접 산업 추정
            company_lower = company_name.lower()
            if any(keyword in company_lower for keyword in ["에너지", "전지", "battery", "배터리"]):
                industries = ["에너지저장장치"]
                print(f"[DEBUG] 회사명 기반 산업 추정: {industries}")
            elif any(keyword in company_lower for keyword in ["전자", "electronics", "반도체", "semiconductor"]):
                industries = ["전자부품"]
                print(f"[DEBUG] 회사명 기반 산업 추정: {industries}")
            elif any(keyword in company_lower for keyword in ["제약", "pharma", "바이오", "bio"]):
                industries = ["제약업"]
                print(f"[DEBUG] 회사명 기반 산업 추정: {industries}")
            else:
                # 최종 fallback: LLM에 직접 질의
                try:
                    from llm_utils import query_llm
                    fallback_prompt = f"'{company_name}'은 어떤 산업에 속하는 회사인가요? 산업명 1-2개만 간단히 답해주세요. 예: 전자, 에너지, 제조, 금융 등"
                    llm_result = query_llm(llm_api_key, fallback_prompt, temperature=0.5).strip()
                    if llm_result and len(llm_result) > 2:
                        industries = [llm_result]
                        print(f"[DEBUG] LLM fallback 성공: {industries}")
                    else:
                        industries = ["기타"]
                        print("[DEBUG] LLM fallback 실패, 기타로 설정")
                except Exception as e:
                    print(f"[DEBUG] LLM fallback 예외: {e}")
                    industries = ["기타"]
        
        if not industries:
            industries = ["기타"]
        # LLM 기반 감사보고서와 산업명 연관성 판단 후 핵심감사사항 추출 함수
        def extract_audit_matters_from_reports(all_filings, industry_name):
            """감사보고서에서 LLM을 통해 해당 산업과 연관된 핵심감사사항을 추출"""
            try:
                from llm_utils import query_llm
                
                audit_matters = []
                
                # 핵심감사사항 관련 키워드
                audit_keywords = ["핵심감사사항", "핵심 감사사항", "key audit matter", "kam", "중요한 감사사항"]
                
                # 감사보고서에서 핵심감사사항 섹션 찾기
                audit_sections = []
                for filing in all_filings:
                    if any(keyword in filing.lower() for keyword in audit_keywords):
                        lines = filing.split('\n')
                        for i, line in enumerate(lines):
                            if any(keyword in line.lower() for keyword in audit_keywords):
                                # 핵심감사사항 섹션 이후 20줄 추출 (더 많은 컨텍스트)
                                context = '\n'.join(lines[i:i+20]).strip()
                                if len(context) > 100:  # 의미있는 내용인지 확인
                                    audit_sections.append(context[:1000])  # 최대 1000자
                
                if not audit_sections:
                    return []
                
                # LLM에 감사보고서와 산업명 연관성 판단 요청
                for section in audit_sections[:3]:  # 최대 3개 섹션만 처리
                    matching_prompt = f"""다음은 감사보고서의 핵심감사사항 내용입니다:

{section}

이 내용이 '{industry_name}' 산업과 연관이 있는지 판단해주세요.

만약 연관이 있다면, 해당 핵심감사사항의 핵심 내용만 간단히 요약해주세요.
만약 연관이 없다면 '연관없음'이라고 답해주세요.

답변 예시:
- 연관 있는 경우: "배터리 제조 공정의 원가 계산 및 재고 평가에 대한 감사 위험이 식별되었습니다."
- 연관 없는 경우: "연관없음"""
                    
                    llm_response = query_llm(llm_api_key, matching_prompt, temperature=0.3)
                    
                    if llm_response and llm_response.strip() and "연관없음" not in llm_response:
                        # 연관된 핵심감사사항 발견
                        audit_matters.append(llm_response.strip())
                
                return audit_matters[:3]  # 최대 3개만 반환
                
            except Exception as e:
                print(f"[DEBUG] LLM 기반 핵심감사사항 추출 실패 ({industry_name}): {e}")
                return []
        
        # LLM을 통한 회계리스크 이슈 생성 함수
        def generate_accounting_risks_for_industry(industry_name, llm_api_key):
            """특정 산업의 회계리스크 이슈를 LLM에 질의하여 생성"""
            try:
                from llm_utils import query_llm  # 함수 내부에서 import
                
                prompt = f"""{industry_name} 산업의 주요 회계리스크 이슈를 4-5개 나열해줘. 
각 항목은 다음과 같은 형식으로 작성해줘:
- (구체적인 회계리스크 이슈 설명)

실제 {industry_name} 산업의 특성을 반영하여 구체적이고 전문적으로 작성해줘.
예시: 매출 인식, 재고 평가, 자산 손상, 충당부채, 관계사 거래 등과 관련된 리스크"""
                
                response = query_llm(llm_api_key, prompt, temperature=0.7).strip()
                return response if response else "회계리스크 이슈 생성에 실패했습니다."
            except Exception as e:
                print(f"[DEBUG] 회계리스크 생성 실패 ({industry_name}): {e}")
                return "회계리스크 이슈 생성에 실패했습니다."
        
        # 산업별 리스크 처리는 all_filings 정의 이후로 이동
        industry_risk_keywords = "(산업별 리스크 처리는 데이터 로드 이후 수행됩니다)"
    except Exception as e:
        print(f"[DEBUG] 산업별 리스크 처리 중 예외 발생: {e}")
        # 정제된 산업명이 있으면 유지, 없으면 기타로 설정
        if not industries or industries == ["기타"]:
            print("[DEBUG] 산업명 추출 실패. 모든 Fallback 경로 실패.")
            industries = ["기타"]
            industry_risk_keywords = "(산업별 리스크 키워드 추출 실패)"
        else:
            print(f"[DEBUG] 정제된 산업명 유지: {industries}")
            # 산업명은 유지하고 기본 리스크 정보 제공
            industry_risk_keywords = ''
            for ind in industries:
                industry_risk_keywords += f"[{ind}]\n"
                industry_risk_keywords += "핵심감사사항:\n- 해당 내용 관련 핵심감사사항이 표기되지 않았습니다.\n"
                industry_risk_keywords += "\n주요 회계리스크 이슈:\n- 회계리스크 이슈 생성에 실패했습니다.\n\n"
            industry_risk_keywords = industry_risk_keywords.strip()
    categories_str = "- " + "\n- ".join(industries)

    # 공시/보고서 chunk 생성
    filings, filings_count = get_recent_filings(api_key, corp_code, since_date, count=40, max_length=600, return_count=True)
    filings_list = []
    if isinstance(filings, list):
        for f in filings:
            date = f.get('date', '') if isinstance(f, dict) else ''
            title = f.get('title', '') if isinstance(f, dict) else str(f)
            content = f.get('content', '') if isinstance(f, dict) else ''
            chunk = f"[{date}] {title}\n{content.strip()[:800]}"
            if chunk.strip():
                filings_list.append(chunk)
    else:
        filings_list = [line for line in filings.split('\n') if not line.startswith('[경고]') and line.strip()]

    # 연도별 주요보고서 chunk 생성
    import time
    current_year = int(time.strftime('%Y'))
    years = [current_year - 1 - i for i in range(5)]
    yearly_key_reports = get_yearly_key_reports(api_key, corp_code, years, max_length=1000)
    yearly_key_texts = [f"[{year}] {report_name}\n{text[:800]}" for year, report_name, text in yearly_key_reports if text.strip()]
    all_filings = filings_list + yearly_key_texts

    # 뉴스 chunk 생성
    from news import news_search_and_summary_with_risk
    news_texts = news_search_and_summary_with_risk(company_name, since_date, financial_summary, llm_api_key, naver_client_id=naver_client_id, naver_client_secret=naver_client_secret, min_news=40)
    news_list = []
    if isinstance(news_texts, list):
        for n in news_texts:
            title = n.get('title', '') if isinstance(n, dict) else str(n)
            content = n.get('content', '') if isinstance(n, dict) else ''
            chunk = f"{title}\n{content.strip()[:800]}"
            if chunk.strip():
                news_list.append(chunk)
    else:
        news_list = [line for line in news_texts.split('\n') if not line.startswith('[경고]') and line.strip()]

    max_item_length = 1000
    all_filings = [item[:max_item_length] for item in all_filings]
    news_list = [item[:max_item_length] for item in news_list]

    # 산업별 리스크 처리 (이제 all_filings가 정의되었으므로 안전하게 수행 가능)
    try:
        print(f"[DEBUG] 산업별 리스크 처리 시작: {industries}")
        
        # 중복 방지를 위한 처리된 산업 추적
        processed_industries = set()
        
        # 모든 관련 산업별로 리스크 키워드/이슈 출력, 줄바꿈 40~50자
        def wrap_lines(text, width=45):
            lines = []
            for l in text.split('\n'):
                lines.extend(textwrap.wrap(l, width=width, replace_whitespace=False))
            return '\n'.join(lines)
        
        industry_risk_keywords = ''
        
        # 각 산업별로 개별 처리 (중복 방지)
        for ind in industries:
            # 이미 처리된 산업인지 확인 (유사한 산업명 중복 방지)
            if any(processed_ind in ind or ind in processed_ind for processed_ind in processed_industries):
                continue
                
            processed_industries.add(ind)
            
            # 항상 원래 산업명 표시
            industry_risk_keywords += f"[{ind}]\n"
            
            # 1. 핵심감사사항: 감사보고서에서 추출
            audit_matters = extract_audit_matters_from_reports(all_filings, ind)
            
            industry_risk_keywords += "핵심감사사항:\n"
            if audit_matters:
                for matter in audit_matters[:3]:  # 최대 3개만 표시
                    # 간단히 정리하여 표시
                    clean_matter = matter.replace('\n', ' ').strip()[:200] + "..."
                    industry_risk_keywords += f"- {clean_matter}\n"
            else:
                industry_risk_keywords += "- 해당 내용 관련 핵심감사사항이 표기되지 않았습니다.\n"
            
            # 2. 주요 회계리스크 이슈: LLM에 질의
            industry_risk_keywords += "\n주요 회계리스크 이슈:\n"
            accounting_risks = generate_accounting_risks_for_industry(ind, llm_api_key)
            
            # 응답을 정리하여 표시
            if accounting_risks and "실패" not in accounting_risks:
                # LLM 응답에서 불필요한 부분 제거 및 정리
                risk_lines = accounting_risks.split('\n')
                for line in risk_lines:
                    line = line.strip()
                    if line and not line.startswith(ind) and not line.startswith('주요'):
                        if not line.startswith('-'):
                            line = f"- {line}"
                        industry_risk_keywords += f"{line}\n"
            else:
                industry_risk_keywords += "- 회계리스크 이슈 생성에 실패했습니다.\n"
            
            industry_risk_keywords += "\n"  # 산업 간 구분을 위한 빈 줄
        
        industry_risk_keywords = industry_risk_keywords.strip()
        print(f"[DEBUG] 산업별 리스크 처리 완료")
        
    except Exception as e:
        print(f"[DEBUG] 산업별 리스크 처리 중 예외: {e}")
        # 기본 리스크 정보 제공
        industry_risk_keywords = ''
        for ind in industries:
            industry_risk_keywords += f"[{ind}]\n"
            industry_risk_keywords += "핵심감사사항:\n- 해당 내용 관련 핵심감사사항이 표기되지 않았습니다.\n"
            industry_risk_keywords += "\n주요 회계리스크 이슈:\n- 회계리스크 이슈 생성에 실패했습니다.\n\n"
        industry_risk_keywords = industry_risk_keywords.strip()

    # 공시/보고서 요약 스킵 여부
    skip_llm = False
    if len(all_filings) == 0 and len(news_list) == 0:
        skip_llm = True

    # 공시/보고서 요약 (최신 공시 40개 + 최근 5년 재무제표/감사/사업보고서, 최소 7개 chunk)
    filings_list_limited = filings_list[:40] if len(filings_list) > 40 else filings_list
    yearly_key_texts_limited = yearly_key_texts[:5] if len(yearly_key_texts) > 5 else yearly_key_texts
    all_filings_limited = filings_list_limited + yearly_key_texts_limited
    # 최소 7개 chunk가 나오도록 분할
    min_chunks = 7
    chunk_size = max(1, len(all_filings_limited) // min_chunks)
    if chunk_size * min_chunks < len(all_filings_limited):
        chunk_size += 1
    summarized_filings = summarize_texts_in_chunks(all_filings_limited, llm_api_key, chunk_size=chunk_size) if (all_filings_limited and not skip_llm) else []
    if summarized_filings and len(summarized_filings) < min_chunks:
        # 부족할 경우 chunk_size=1로 재요약
        summarized_filings = summarize_texts_in_chunks(all_filings_limited, llm_api_key, chunk_size=1)
    def format_alpha_chunks(chunks):
        alpha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        return '\n\n'.join([f"{alpha[i%26]}. {chunk}" for i, chunk in enumerate(chunks)])

    # 뉴스 요약 (최신 40개, 최소 7개 chunk)
    news_list_limited = news_list[:40] if len(news_list) > 40 else news_list
    news_min_chunks = 7
    news_max_chunks = 10
    # chunk_size를 조정해 7~10개 chunk가 되도록 분할
    if len(news_list_limited) < news_min_chunks:
        news_chunk_size = 1
    else:
        news_chunk_size = max(1, len(news_list_limited) // news_max_chunks)
    summarized_news = summarize_texts_in_chunks(news_list_limited, llm_api_key, chunk_size=news_chunk_size) if (news_list_limited and not skip_llm) else []
    # 부족하면 chunk_size=1로 재분할
    if summarized_news and len(summarized_news) < news_min_chunks:
        summarized_news = summarize_texts_in_chunks(news_list_limited, llm_api_key, chunk_size=1)
    # 10개 초과하지 않도록 슬라이싱
    summarized_news = summarized_news[:news_max_chunks] if summarized_news else []

    if summarized_filings:
        summarized_filings = [s if s.strip() else f'(원문 일부) {all_filings_limited[i][:200]}' for i, s in enumerate(summarized_filings)]
    wrapped_filings_summary = format_alpha_chunks(summarized_filings[:10]) if summarized_filings else '\n'.join([f'(원문 일부) {item[:200]}' for item in all_filings[:10]]) if all_filings else '(요약 없음)'
    filings_summary_str = wrapped_filings_summary

    # 뉴스 요약
    news_list_limited = news_list[:10] if len(news_list) > 10 else news_list
    summarized_news = summarize_texts_in_chunks(news_list_limited, llm_api_key, chunk_size=1) if (news_list_limited and not skip_llm) else []
    def format_alpha_news(chunks):
        alpha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        return '\n\n'.join([f"{alpha[i%26]}. {chunk}" for i, chunk in enumerate(chunks)])
    if summarized_news:
        summarized_news = [s if s.strip() else f'(원문 일부) {news_list_limited[i][:200]}' for i, s in enumerate(summarized_news)]
    wrapped_news_summary = format_alpha_news(summarized_news[:10]) if summarized_news else '\n'.join([f'(원문 일부) {item[:200]}' for item in news_list[:10]]) if news_list else '(요약 없음)'
    news_summary_str = wrapped_news_summary

    # 재무비율 표 생성 및 LLM 해설/통합분석 복원
    ratios_table = ""
    wrapped_finratio_llm_analysis = ""
    finratio_llm_analysis = ""
    wrapped_integrated_llm_analysis = ""
    # financial_summary가 DataFrame 또는 dict/list 형태로 올 수 있음
    import pandas as pd
    # 재무비율 표는 반드시 DataFrame에서 생성
    if isinstance(financial_summary, pd.DataFrame) and not financial_summary.empty:
        try:
            ratios_table = financial_summary.to_markdown(index=False, tablefmt="github")
        except Exception:
            ratios_table = financial_summary.to_string(index=False, col_space=12, justify='center')
    else:
        print("[DEBUG] 재무비율 DataFrame이 비어있거나 올바르지 않습니다.")
        ratios_table = "(재무비율 데이터 없음)"
    # LLM 해설: 표가 있으면 항상 분석
    try:
        from llm_utils import query_llm  # 함수 내부에서 import
        
        if ratios_table.strip() and ratios_table.strip() != "(재무비율 데이터 없음)":
            finratio_llm_analysis = query_llm(llm_api_key, f"아래는 주요 재무비율 표입니다. 표를 참고하여 최근 5개년의 재무 건전성, 성장성, 수익성, 위험성, 주요 리스크 신호를 5문장 이내로 요약해줘:\n{ratios_table}", temperature=0.7)
            wrapped_finratio_llm_analysis = finratio_llm_analysis.strip() if finratio_llm_analysis else "(LLM 해설 없음)"
        else:
            wrapped_finratio_llm_analysis = "(재무비율 데이터 없음)"
    except Exception as e:
        print(f"[DEBUG] 재무비율 LLM 해설 실패: {e}")
        wrapped_finratio_llm_analysis = "(LLM 해설 실패)"
    
    # 통합 LLM 분석
    try:
        from llm_utils import query_llm  # 함수 내부에서 import
        
        integrated_prompt = f"산업/카테고리: {industries}\n공시/보고서 요약: {filings_summary_str}\n뉴스 요약: {news_summary_str}\n주요 재무비율: {ratios_table}\n\n위 정보를 참고하여, 해당 기업의 최근 5년간 주요 리스크 요인과 시사점, 향후 주의해야 할 점을 5문장 이내로 종합 요약해줘."
        integrated_llm_analysis = query_llm(llm_api_key, integrated_prompt, temperature=0.7)
        wrapped_integrated_llm_analysis = integrated_llm_analysis.strip() if integrated_llm_analysis else "(LLM 통합분석 없음)"
    except Exception as e:
        print(f"[DEBUG] LLM 산업명 추출 실패: {e}")
        industries = ["기타"]
        wrapped_integrated_llm_analysis = "(LLM 통합분석 실패)"
    # 최종 요약 파일 생성 및 저장
    # (4) 전체 줄바꿈 및 가독성 개선
    # 모든 주요 요약/분석 텍스트에 줄바꿈 적용 (표 제외)
    filings_summary_wrapped = wrap_lines(filings_summary_str, width=45)
    news_summary_wrapped = wrap_lines(news_summary_str, width=45)
    finratio_llm_analysis_wrapped = wrap_lines(wrapped_finratio_llm_analysis, width=45)
    integrated_llm_analysis_wrapped = wrap_lines(wrapped_integrated_llm_analysis, width=45)

    risk_summary = f"""
[산업/카테고리]
{categories_str}

[산업별 리스크 키워드/이슈]
{industry_risk_keywords}

[공시/보고서 기반 리스크 요약]
{filings_summary_wrapped}

[뉴스 기반 리스크 요약]
{news_summary_wrapped}

[재무비율 표]
{ratios_table}

[재무비율 해설]
{finratio_llm_analysis_wrapped}

[통합 LLM 분석]
{integrated_llm_analysis_wrapped}
"""
    save_summary_to_file(company_name, risk_summary)
    return risk_summary

  