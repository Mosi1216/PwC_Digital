# 기업 통합 리스크 요약 프로그램

## 프로그램 개요

이 프로그램은 한국 상장기업의 최근 5개년 재무비율 분석, 네이버 뉴스 및 공시 요약, 산업별 리스크 키워드 도출 등 종합적인 리스크 요약 리포트를 자동으로 생성합니다.

- **재무비율 분석**: DART API를 활용해 5개년 주요 재무지표를 분석하고 시각화
- **뉴스 요약**: 네이버 뉴스 API와 OpenAI LLM을 활용해 최근 뉴스의 위험 이슈 자동 요약
- **산업별 리스크 키워드/이슈 도출**: 산업/카테고리 추출 및 LLM 기반 주요 리스크 키워드 자동 도출
- **최종 리스크요약 파일 자동 저장**: 모든 결과를 `results/회사명/` 폴더에 CSV, PNG, TXT로 저장

---

## 실행 가이드

1. **Python 가상환경 준비(최초 1회만 실행)**
    - 아래 명령어는 프로젝트 폴더에서 최초 1회만 실행하면 됩니다.
    - 만약 PowerShell에서 실행 정책 오류가 발생하면, 아래 명령어로 실행 정책을 완화한 뒤 진행하세요.
    ```powershell
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    ```
    - 그 후 가상환경을 생성 및 활성화합니다.
    ```bash
    python -m venv venv
    
    # Windows
    venv\Scripts\activate

    # macOS/Linux
    source venv/bin/activate
    ```
2. **필수 패키지 설치(최초 1회만 실행)**
    - 가상환경을 활성화한 후, 아래 명령어를 통해 필요한 패키지를 한 번만 설치하면 됩니다.
    ```bash
    pip install -r requirements.txt
    ```
3. **API Key 입력**
    - `run.py` 파일 상단에 본인의 API 키를 직접 입력합니다.
        ```python
        DART_API_KEY = "..."
        OPENAI_API_KEY = "sk-..."
        NAVER_CLIENT_ID = "..."
        NAVER_CLIENT_SECRET = "..."
        ```
4. **프로그램 실행**
    ```bash
    python run.py
    ```
5. **회사명 입력**
    - 안내에 따라 분석할 회사명을 정확히 입력합니다. (예: 삼성전자)
6. **결과 확인**
    - 모든 결과 파일은 `results/회사명/` 폴더에 자동 저장됩니다.
        - 재무비율: CSV, PNG
        - 최종 리스크요약: TXT

---

## API Key 발급 방법 요약

### 1. DART API Key
- [DART 오픈API](https://opendart.fss.or.kr/)
- 회원가입 및 로그인 → 마이페이지 → API Key 발급 → 24자리 영문/숫자 키 복사

### 2. OpenAI API Key
- [OpenAI 플랫폼](https://platform.openai.com/account/api-keys)
- 회원가입/로그인 → API Keys 메뉴 → "Create new secret key" 클릭 → sk-로 시작하는 키 복사
- 유료 결제 필요

### 3. Naver Open API Client ID/Secret
- [네이버 개발자센터](https://developers.naver.com/apps/#/register)
- 네이버 계정 로그인 → "애플리케이션 등록" → 검색 > 뉴스 Open API 선택
- Client ID, Client Secret 확인 및 복사

---

## 사용 가이드라인 및 참고사항

- **API Key는 run.py 상단에 직접 입력**해야 하며, .env 파일은 사용하지 않습니다.
- 분석 대상 회사명은 DART 및 네이버 뉴스 기준 정확한 공식명칭을 입력해야 검색이 원활합니다.
- 실행 전 가상환경 활성화 및 requirements.txt 패키지 설치를 반드시 완료하세요.
- 최초 실행 시, 결과 폴더(`results/회사명/`)가 자동 생성됩니다.
- 네트워크 연결 필요: DART, OpenAI, Naver API 모두 인터넷 연결 필요
- OpenAI API 사용량에 따라 과금이 발생할 수 있습니다.
- 에러 발생 시 콘솔 메시지를 참고해 API 키 입력, 회사명, 패키지 설치 여부를 점검하세요.

---

## 문제 해결(Troubleshooting)

### 1. venv 생성 오류 (venvlauncher.exe 복사 실패)
- Python 설치가 손상되었거나, 권한 문제일 수 있습니다.
- [공식 Python 다운로드](https://www.python.org/downloads/)에서 최신 버전을 재설치 해주세요.

### 2. PowerShell 실행 정책 오류
- 아래와 같은 메시지가 뜨면:
    > 이 시스템에서 스크립트를 실행할 수 없으므로 ... Activate.ps1 파일을 로드할 수 없습니다.
- PowerShell에서 아래 명령어로 실행 정책을 일시적으로 완화한 뒤 다시 시도하세요.
    ```powershell
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    ```
- 이 변경은 현재 PowerShell 창에만 적용됩니다.

---

## 주요 파일 구조
- `run.py` : 메인 실행 스크립트 (API 키 입력, 전체 워크플로우)
- `requirements.txt` : 필수 패키지 목록
- `results/` : 결과 파일 저장 폴더

---

문의 및 추가 개선 요청은 언제든 환영합니다!


