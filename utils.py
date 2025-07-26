# [유틸리티 모듈] 경로, 폰트, 설치 등 각종 유틸리티 함수를 제공합니다.
import sys
import subprocess
import importlib
import os

def pip_install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def import_or_install(package, import_name=None):
    try:
        return importlib.import_module(import_name or package)
    except ImportError:
        print(f"'{package}' 패키지가 없어 설치합니다...")
        pip_install(package)
        return importlib.import_module(import_name or package)

def ensure_korean_font():
    try:
        import matplotlib
        fm = importlib.import_module("matplotlib.font_manager")
        import platform
        if platform.system() == "Windows":
            fonts = [f.name for f in fm.fontManager.ttflist]
            if "Malgun Gothic" not in fonts:
                print("[경고] 'Malgun Gothic' 폰트가 시스템에 없습니다. 한글이 깨질 수 있습니다.")
                print("https://software.naver.com/software/summary.nhn?softwareId=GWS_000667 링크에서 폰트를 설치하세요.")
    except Exception as e:
        print(f"[ERROR] ensure_korean_font: {e}")

def get_unique_filepath(filepath):
    """If filepath exists, append _2 before extension. Else, return as is."""
    if not os.path.exists(filepath):
        return filepath
    base, ext = os.path.splitext(filepath)
    candidate = f"{base}_2{ext}"
    count = 2
    while os.path.exists(candidate):
        count += 1
        candidate = f"{base}_{count}{ext}"
    return candidate

def save_summary_to_file(company_name, summary):
    result_dir = os.path.join("results", company_name)
    os.makedirs(result_dir, exist_ok=True)
    filename = os.path.join(result_dir, f"{company_name}_최종리스크요약.txt")
    filename = get_unique_filepath(filename)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(summary)

def clean_news_text(text):
    """뉴스 원문 내 HTML 엔티티, 특수문자, 불필요한 공백/줄바꿈을 정제"""
    import html
    import re
    if not text:
        return ""
    # HTML 엔티티 변환
    text = html.unescape(text)
    # &8200; 등 숫자 엔티티 제거
    text = re.sub(r'&[a-zA-Z0-9#]+;', '', text)
    # 불필요한 기호/공백 정리
    text = re.sub(r'<[^>]+>', '', text)  # 태그 제거
    text = re.sub(r'[\r\n\t]+', '\n', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    return text.strip()
