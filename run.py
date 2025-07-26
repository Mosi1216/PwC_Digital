# [메인 실행 스크립트] 재무분석, 뉴스요약, 리스크 요약 등 전체 워크플로우를 실행합니다.
from financial import analyze_financial_ratios_multi_year, export_to_csv, plot_financial_ratios
from news import news_search_and_summary_with_risk
from risk_summary import summarize_company_risks
import os

# 아래에 본인의 API 키를 직접 입력하세요.
# 예시)
# DART_API_KEY = ""
# OPENAI_API_KEY = "sk-..."
# NAVER_CLIENT_ID = "..."
# NAVER_CLIENT_SECRET = "..."
DART_API_KEY = ""
OPENAI_API_KEY = ""
NAVER_CLIENT_ID = ""
NAVER_CLIENT_SECRET = ""

import os
import re

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def main():
    import time
    import sys
    from dart_api import get_corp_code
    
    # 명령행 인수가 있는지 확인
    if len(sys.argv) > 1:
        company_name = sys.argv[1].strip()
        print(f"[INFO] 명령행에서 회사명 입력: {company_name}")
    else:
        # 대화형 입력
        try:
            company_name = input("분석할 회사명을 정확히 입력하세요 (예: 삼성전자): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("[ERROR] 입력이 중단되었습니다.")
            return
    
    # 입력 검증
    if not company_name or len(company_name) < 2:
        print("[ERROR] 유효한 회사명을 입력해주세요.")
        return
    
    # 명령행 문자열이 잘못 입력된 경우 감지
    if '/' in company_name or '\\' in company_name or '.exe' in company_name:
        print("[ERROR] 잘못된 입력이 감지되었습니다. 회사명만 입력해주세요.")
        return
    
    print(f"[INFO] 회사명 입력 완료: {company_name}")
    safe_company_name = sanitize_filename(company_name)
    os.makedirs(f"results/{safe_company_name}", exist_ok=True)
    current_year = int(time.strftime('%Y'))
    years = [current_year - 1 - i for i in range(5)]  # 최근 5개년 (올해 제외)
    try:
        print("[INFO] corp_code 추출 시도...")
        corp_code = get_corp_code(DART_API_KEY, company_name)
        print(f"[INFO] corp_code 추출 성공: {corp_code}")
    except Exception as e:
        print(f"[ERROR] corp_code 추출 실패: {e}")
        import traceback
        traceback.print_exc()
        return
    print("[INFO] 재무비율 분석 시작...")
    df = analyze_financial_ratios_multi_year(DART_API_KEY, corp_code, years)
    print("[INFO] 재무비율 분석 완료")
    export_to_csv(df, safe_company_name, f"{safe_company_name}_재무비율.csv")
    print("[INFO] 재무비율 CSV 저장 완료")
    plot_financial_ratios(df, safe_company_name, filename=f"{safe_company_name}_재무비율.png")
    print("[INFO] 재무비율 그래프 저장 완료")
    print("[INFO] 리스크 요약 시작...")
    # 1. 리스크 요약 생성 및 저장
    try:
        from risk_summary import summarize_company_risks
        since_date = f"{current_year - 5}0101"  # 최근 5년치 시작일
        print("[INFO] 뉴스 요약 시작...")
        news = news_search_and_summary_with_risk(company_name, since_date, df, OPENAI_API_KEY, naver_client_id=NAVER_CLIENT_ID, naver_client_secret=NAVER_CLIENT_SECRET, min_news=10)
        print("[INFO] 뉴스 요약 완료")
        print("[INFO] 리스크 통합 요약 시작...")
        risk_summary = summarize_company_risks(company_name, DART_API_KEY, OPENAI_API_KEY, since_date, df, naver_client_id=NAVER_CLIENT_ID, naver_client_secret=NAVER_CLIENT_SECRET)
        print("[INFO] 리스크 통합 요약 완료")
        print(f"[최종리스크요약 저장 완료] results/{safe_company_name}/{safe_company_name}_최종리스크요약.txt")
    except Exception as e:
        print(f"[ERROR] 최종리스크요약 생성 실패: {e}")
        import traceback
        traceback.print_exc()
    # 2. 결과 저장 경로 안내
    print(f"\n모든 결과가 results/{safe_company_name}/ 폴더에 저장되었습니다. (CSV, PNG, 최종리스크요약)")

if __name__ == "__main__":
    main()