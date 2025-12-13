@echo off
chcp 65001 > nul
REM FastAPI 개발 서버 시작 스크립트 (Windows)

echo.
echo ============================================
echo FastAPI 서버 시작 (로컬 개발 모드)
echo ============================================
echo.

REM .env 파일 확인
if not exist .env (
    echo [경고] .env 파일이 없습니다.
    echo 프로젝트 루트 디렉토리에서 실행하세요.
    pause
    exit /b 1
)

REM Python 버전 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [에러] Python이 설치되어 있지 않습니다.
    echo Python 3.9 이상을 설치해주세요.
    pause
    exit /b 1
)

echo [OK] Python 설치 확인됨
echo.

REM 로그 폴더 생성
if not exist logs (
    mkdir logs
    echo [생성] logs 폴더가 생성되었습니다.
)

REM FastAPI 서버 시작
echo [시작] FastAPI 서버를 시작합니다...
echo [주소] http://127.0.0.1:8008
echo [문서] http://127.0.0.1:8008/docs
echo.

cd /d "%~dp0\server\fastapi"
python -m uvicorn app:app --host 127.0.0.1 --port 8001 --reload

if errorlevel 1 (
    echo [에러] FastAPI 서버 시작에 실패했습니다.
    pause
    exit /b 1
)

pause
