@echo off
chcp 65001 > nul
REM Flash AI Coding Agent - Docker Compose 시작 스크립트 (Windows)

echo.
echo ============================================
echo Flash AI Coding Agent - Docker Setup
echo ============================================
echo.

REM .env 파일 확인
if not exist .env (
    echo [경고] .env 파일이 없습니다.
    echo .env.example 파일을 .env로 복사하고 필요한 값을 입력하세요.
    copy .env.example .env
    echo [완료] .env 파일이 생성되었습니다.
    echo.
)

REM Docker 설치 확인
docker --version >nul 2>&1
if errorlevel 1 (
    echo [에러] Docker가 설치되어 있지 않습니다.
    echo Docker를 먼저 설치해주세요: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Docker Compose 버전 확인
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [경고] Docker Compose가 설치되어 있지 않습니다.
    echo Docker Desktop을 설치하면 Docker Compose가 함께 설치됩니다.
    pause
    exit /b 1
)

echo [OK] Docker 및 Docker Compose 설치 확인됨
echo.

REM 컨테이너 시작
echo [시작] Docker Compose 시작 중...
docker-compose build --no-cache
docker-compose up -d

if errorlevel 1 (
    echo [에러] Docker Compose 시작에 실패했습니다.
    pause
    exit /b 1
)

echo [완료] 모든 서비스가 시작되었습니다!
echo.
echo ============================================
echo 접근 가능한 서비스
echo ============================================
echo.
echo Django API:             http://localhost:8000
echo API 헬스 체크:          http://localhost:8000/api/v1/health
echo Streamlit 프런트엔드:   http://localhost:8501
echo LangChain FastAPI 서버: http://localhost:8001
echo PostgreSQL:             localhost:5432
echo ============================================
echo.
echo 유용한 명령어:
echo.
echo 로그 확인:
echo   docker-compose logs -f
echo   docker-compose logs -f django-api
echo   docker-compose logs -f streamlit-frontend
echo   docker-compose logs -f agent-backend
echo.
echo 서비스 상태 확인:
echo   docker-compose ps
echo.
echo 서비스 중지:
echo   docker-compose down
echo.
echo 데이터 초기화 (주의!):
echo   docker-compose down -v
echo.
echo 참고: 로컬 SLM 서버(local_llm_server.py)는 호스트에서 별도로 실행해야 합니다.
echo   예) MODEL_PATH 설정 후: python local_llm_server.py
echo.
pause
