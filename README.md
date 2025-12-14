# Flash AI Coding Agent

## 프로젝트 개요

Flash AI Coding Agent는 AI 기반 코딩 어시스턴트 시스템으로, 사용자가 코딩 문제를 풀고 퀴즈를 통해 학습하며 게이미피케이션을 통해 동기부여받는 통합 플랫폼입니다.

## 🚀 빠른 시작

### 권장 실행 방식: Docker Compose

```bash
# Windows
start.bat

# Linux/Mac
./start.sh
```

**접속 주소:**
- 🌐 **Streamlit Frontend:** http://localhost:8501
- 🔧 **Django REST API 헬스 체크:** http://localhost:8000/api/v1/health

### 로컬 개발(LLM/생성서버 분리 실행)

```bash
# 1) 로컬 LLM 서버 (OpenAI 호환 API, 기본 포트 8008)
python local_llm_server.py

# 2) FastAPI 코드/퀴즈 생성 서버 (기본 포트 8001)
start_fastapi.bat
```

**접속 주소:**
- ⚡ **FastAPI Docs:** http://127.0.0.1:8001/docs

**✨ 중요:** `OPENAI_API_KEY`가 없으면 FastAPI 서버가 `LOCAL_LLM_URL`로 지정된 로컬 LLM(OpenAI 호환)로 자동 폴백합니다.

---

## 문서

프로젝트에 필요한 최소 문서만 `docs/` 폴더에 유지합니다.

- [실행 가이드 (SETUP_AND_RUN_ko.md)](docs/SETUP_AND_RUN_ko.md)
- [보안/환경변수 가이드 (SECURITY_AND_ENV.md)](docs/SECURITY_AND_ENV.md)

추가로, API 명세/흐름도 자료가 필요하면 아래 문서를 참고하세요.

- [API 가이드 (Flash_API_guide.md)](docs/Flash_API_guide.md)
- [API 목록 (Flash_API_list.csv)](docs/Flash_API_list.csv)
- [OpenAPI 스펙 (openapi.yaml)](docs/openapi.yaml)
- [Flowchart (flow_chart_ko.txt)](docs/flow_chart_ko.txt)
- [Flowchart MVP (flow_chart_mvp_ko.txt)](docs/flow_chart_mvp_ko.txt)
