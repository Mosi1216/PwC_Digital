import pandas as pd
import os
from dart_api import fetch_financial_statements

def analyze_financial_ratios_multi_year(api_key, corp_code, years):
    results = []
    for year in years:
        data = fetch_financial_statements(api_key, corp_code, year)
        if not data or 'list' not in data:
            continue
        df = pd.DataFrame(data['list'])
        def get_account(df, names):
            if isinstance(names, str):
                names = [names]
            for name in names:
                vals = df[df['account_nm'] == name]['thstrm_amount']
                if not vals.empty:
                    try:
                        return float(vals.values[0].replace(",", ""))
                    except:
                        continue
            for name in names:
                vals = df[df['account_nm'].str.contains(name, na=False)]['thstrm_amount']
                if not vals.empty:
                    try:
                        return float(vals.values[0].replace(",", ""))
                    except:
                        continue
            return None
        # 주요 재무비율 계산 (예시)
        유동비율 = get_account(df, ["유동자산"]) / get_account(df, ["유동부채"]) * 100 if get_account(df, ["유동부채"]) else None
        부채비율 = get_account(df, ["부채총계"]) / get_account(df, ["자본총계"]) * 100 if get_account(df, ["자본총계"]) else None
        # ... (다른 비율도 추가)
        results.append({"연도": year, "유동비율": 유동비율, "부채비율": 부채비율})
    return pd.DataFrame(results)

def export_to_csv(df, company_name, filename):
    os.makedirs(f"results/{company_name}", exist_ok=True)
    full_path = os.path.join("results", company_name, filename)
    df.to_csv(full_path, index=False, encoding='utf-8-sig')
    print(f"[Tableau용 CSV 저장 완료] {full_path}")
