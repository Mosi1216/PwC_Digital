# [시각화 모듈] 재무비율 등 데이터 플롯/시각화 전용 함수입니다.
import os
import matplotlib.pyplot as plt
from utils import ensure_korean_font

def plot_financial_ratios(df, company_name, filename=None):
    try:
        ensure_korean_font()
        plt.rcParams['font.family'] = 'Malgun Gothic'
        plt.rcParams['axes.unicode_minus'] = False
        # ... (이하 기존 코드와 동일하게 시각화)
        if filename:
            os.makedirs(f"results/{company_name}", exist_ok=True)
            save_path = os.path.join("results", company_name, filename)
            plt.savefig(save_path, bbox_inches='tight')
            print(f"[재무비율 그래프 저장 완료] {filename}")
            plt.close()
        else:
            plt.show()
    except Exception as e:
        print(f"[ERROR] plot_financial_ratios: {e}")
