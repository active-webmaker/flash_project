# 실행 가이드 (SETUP_AND_RUN_ko)

이 문서는 현재 리포지토리의 기본 실행 방법을 정리합니다. **API Key 값은 문서에 작성하지 않습니다.**

## 1) 사전 준비

- Python 설치(로컬 개발 시)
- Docker Desktop 설치(권장 실행 방식)

## 2) 환경 변수(.env)

- 프로젝트 루트의 `.env.example`을 `.env`로 복사해서 사용합니다.
- 필요한 값들은 `.env.example`에 정의된 **변수 이름을 기준으로** 설정합니다.

## 3) 권장 실행 방식: Docker Compose

프로젝트 루트에서 실행:

- Windows:

```bash
start.bat
```

- Linux/Mac:

```bash
./start.sh
```

### 주요 접속 주소

- Streamlit Frontend: http://localhost:8501
- Django REST API Health: http://localhost:8000/api/v1/health

### 중지

```bash
stop.bat
```

## 4) 로컬 개발(LLM/생성 서버 분리)

Docker 대신(또는 Docker와 병행해서) 호스트에서 로컬 LLM과 생성 서버를 별도로 올릴 수 있습니다.

### 4.1 로컬 LLM 서버

프로젝트 루트에서:

```bash
python local_llm_server.py
```

- OpenAI 호환 엔드포인트: `http://<host>:8008/v1` (기본값)
- `MODEL_PATH` 등은 `.env`에서 설정합니다.

### 4.2 FastAPI 코드/퀴즈 생성 서버

Windows:

```bash
start_fastapi.bat
```

- FastAPI Docs: http://127.0.0.1:8001/docs

## 5) 참고(LLM 선택 로직)

- `OPENAI_API_KEY`가 설정되어 있으면 외부 OpenAI를 사용합니다.
- 설정되어 있지 않으면 `LOCAL_LLM_URL`(기본 `http://127.0.0.1:8008/v1`)로 로컬 LLM(OpenAI 호환)로 폴백합니다.
