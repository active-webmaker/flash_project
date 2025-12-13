# Flash AI Coding Agent

## 프로젝트 개요

Flash AI Coding Agent는 AI 기반 코딩 어시스턴트 시스템으로, 사용자가 코딩 문제를 풀고 퀴즈를 통해 학습하며 게이미피케이션을 통해 동기부여받는 통합 플랫폼입니다.

## 🚀 빠른 시작

### 로컬 개발 환경 (3개 터미널)

**📚 자세한 가이드:** [LOCAL_DEVELOPMENT_GUIDE.md](LOCAL_DEVELOPMENT_GUIDE.md)
**⚙️ FastAPI 설정:** [FASTAPI_SETUP_GUIDE.md](FASTAPI_SETUP_GUIDE.md)

```bash
# 터미널 1️⃣ : 로컬 LLM 서버 (포트 8001)
python local_llm_server.py

# 터미널 2️⃣ : FastAPI 서버 (포트 8008) - 퀴즈/코드 생성
start_fastapi.bat

# 터미널 3️⃣ : Django + Streamlit (포트 8000, 8501)
start.bat
```

**접속 주소:**
- 🌐 **Streamlit Frontend:** http://127.0.0.1:8501
- 🔧 **Django REST API:** http://127.0.0.1:8000/api/v1/health
- ⚡ **FastAPI Docs:** http://127.0.0.1:8008/docs

**✨ 중요:** OpenAI API 키 없이도 작동합니다! 로컬 LLM 서버가 자동으로 사용됩니다.

---

## 문서

이 프로젝트의 모든 관련 문서는 `docs/` 폴더에 정리되어 있습니다.

### 🚀 프로젝트 및 완료 보고서

-   [프로젝트 개요 (PROJECT_OVERVIEW.md)](docs/PROJECT_OVERVIEW.md)
-   [MVP 준비 상태 보고서 (MVP_READINESS_REPORT.md)](docs/MVP_READINESS_REPORT.md)
-   [프로젝트 완료 요약 (PROJECT_COMPLETION_SUMMARY.md)](docs/PROJECT_COMPLETION_SUMMARY.md)
-   [최종 완료 요약 (FINAL_COMPLETION_SUMMARY_ko.md)](docs/FINAL_COMPLETION_SUMMARY_ko.md)
-   [모듈 통합 기록 (integration_log.md)](docs/integration_log.md)

### 🧪 테스트 관련 문서

-   [테스트 계획 (TEST_PLAN.md)](docs/TEST_PLAN.md)
-   [테스트 결과 (TEST_RESULTS.md)](docs/TEST_RESULTS.md)
-   [종합 테스트 보고서 (COMPREHENSIVE_TEST_REPORT.md)](docs/COMPREHENSIVE_TEST_REPORT.md)
-   [최종 통합 테스트 보고서 (FINAL_INTEGRATION_REPORT.md)](docs/FINAL_INTEGRATION_REPORT.md)

### 🐳 Docker 관련 문서

-   [Docker 전략 (DOCKER_STRATEGY.md)](docs/DOCKER_STRATEGY.md)
-   [Docker 사용 가이드 (DOCKER_USAGE.md)](docs/DOCKER_USAGE.md)
-   [Docker 구현 보고서 (DOCKER_IMPLEMENTATION_REPORT_ko.md)](docs/DOCKER_IMPLEMENTATION_REPORT_ko.md)
-   [Docker 배포 가이드 (DOCKER_DEPLOYMENT_GUIDE_ko.md)](docs/DOCKER_DEPLOYMENT_GUIDE_ko.md)

### ⚙️ API 및 기술 문서

-   [API 가이드 (Flash_API_guide.md)](docs/Flash_API_guide.md)
-   [API 목록 (Flash_API_list.csv)](docs/Flash_API_list.csv)
-   [공통 개발 환경 규약 (Flash_common.md)](docs/Flash_common.md)
-   [빠른 시작 가이드 (SETUP_AND_RUN_ko.md)](docs/SETUP_AND_RUN_ko.md)

### 📊 순서도 (Flowcharts)

-   [전체 시스템 순서도 (flow_chart_ko.txt)](docs/flow_chart_ko.txt)
-   [MVP 아키텍처 순서도 (flow_chart_mvp_ko.txt)](docs/flow_chart_mvp_ko.txt)

---
*참고: 일부 문서는 원본 영어 파일과 한국어 번역본이 함께 존재합니다.*
