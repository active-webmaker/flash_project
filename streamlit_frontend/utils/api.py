import os
import json
import requests
import logging
from typing import Optional, Tuple
from datetime import datetime
import sys

# 로그 디렉토리 생성
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

# 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 파일 핸들러 (모든 로그)
log_file = os.path.join(LOG_DIR, f"api_client_{datetime.now().strftime('%Y%m%d')}.log")
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)

# 콘솔 핸들러 (INFO 이상)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# 포매터
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 핸들러 추가
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def login(self, username: str, password: str) -> dict:
        # Django custom login: /api/v1/auth/login
        url = self._url("/api/v1/auth/login")
        r = requests.post(url, json={"username": username, "password": password}, timeout=10)
        if r.status_code != 200:
            raise RuntimeError(f"{r.status_code} {r.text}")
        return r.json()

    def health(self) -> Tuple[bool, Optional[str]]:
        try:
            url = self._url("/api/v1/health")
            r = requests.get(url, timeout=5)
            return r.ok, r.text
        except Exception as e:
            return False, str(e)

    def me(self, access_token: Optional[str]) -> Optional[dict]:
        if not access_token:
            return None
        url = self._url("/api/v1/me")
        r = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        if r.status_code == 200:
            return r.json()
        return None

    # Gamification
    def gami_profile(self, access_token: str) -> Optional[dict]:
        url = self._url("/api/v1/gami/profile")
        r = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        return r.json() if r.status_code == 200 else None

    def gami_event(self, access_token: str, event_code: str, metadata: Optional[dict] = None) -> Optional[dict]:
        url = self._url("/api/v1/gami/events")
        payload = {"event_code": event_code, "metadata": metadata or {}}
        r = requests.post(url, json=payload, headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
        return r.json() if r.status_code in (200, 201) else None

    # Quiz
    def quiz_pools(self, access_token: str) -> Optional[dict]:
        url = self._url("/api/v1/quiz/pools")
        r = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        return r.json() if r.status_code == 200 else None

    def save_generated_quiz(self, access_token: str, questions: list, source: str = "code_generation", metadata: Optional[dict] = None) -> Optional[dict]:
        """
        Persist LLM-generated quiz questions to Django.
        """
        url = self._url("/api/v1/quiz/generated")
        payload = {"questions": questions, "source": source, "metadata": metadata or {}}
        r = requests.post(url, json=payload, headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
        return r.json() if r.status_code in (200, 201) else None

    # Projects
    def projects(self, access_token: str) -> list:
        url = self._url("/api/v1/projects")
        r = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        if r.status_code == 200:
            return r.json() or []
        return []

    def register_project(self, access_token: str, name: str, local_path: str = "", remote_url: str = "") -> Optional[dict]:
        url = self._url("/api/v1/git/projects/register")
        payload = {"name": name, "local_path": local_path, "remote_url": remote_url}
        r = requests.post(url, json=payload, headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
        return r.json() if r.status_code in (200, 201) else None

    # Jobs / Code generation
    def create_job(self, access_token: str, project_id: int, job_type: str, payload: dict) -> Optional[dict]:
        url = self._url(f"/api/v1/projects/{project_id}/jobs")
        r = requests.post(url, json={"job_type": job_type, "payload": payload}, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
        return r.json() if r.status_code in (200, 201) else None

    def get_job(self, access_token: str, project_id: int, job_id: int) -> Optional[dict]:
        url = self._url(f"/api/v1/projects/{project_id}/jobs/{job_id}")
        try:
            r = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=5)
            return r.json() if r.status_code == 200 else None
        except requests.exceptions.RequestException:
            return None

    def generate_quiz_from_code(self, code: str, num_questions: int = 5) -> Optional[dict]:
        base = os.getenv("STREAMLIT_LANGCHAIN_BASE_URL") or os.getenv("LANGCHAIN_BASE_URL")

        logger.info("=" * 80)
        logger.info("퀴즈 생성 요청 시작")
        logger.info("=" * 80)

        if not base:
            error_msg = "LANGCHAIN server base URL is not configured (set STREAMLIT_LANGCHAIN_BASE_URL or LANGCHAIN_BASE_URL)."
            logger.error(f"환경 변수 미설정: {error_msg}")
            logger.info("=" * 80)
            return {"error": error_msg}

        url = f"{base.rstrip('/')}/quiz_from_code"
        logger.info(f"대상 서버: {url}")
        logger.info(f"요청 데이터: num_questions={num_questions}, code_length={len(code)}")

        try:
            logger.debug(f"FastAPI 서버에 POST 요청 전송 중... (타임아웃: 30초)")
            r = requests.post(url, json={"code": code, "num_questions": num_questions}, timeout=30)

            logger.info(f"응답 상태 코드: {r.status_code}")

            if r.status_code == 200:
                response_data = r.json()
                questions_count = len(response_data.get("questions", []))
                logger.info(f"✅ 퀴즈 생성 성공! (생성된 문항: {questions_count}개)")
                logger.info("=" * 80)
                return response_data
            else:
                error_msg = f"HTTP {r.status_code}: {r.text[:200]}"
                logger.error(f"❌ 서버 오류: {error_msg}")
                logger.info("=" * 80)
                return {"error": f"HTTP {r.status_code}", "body": r.text}

        except requests.exceptions.Timeout as e:
            error_msg = f"요청 타임아웃 (30초 초과): {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"서버 주소: {url}")
            logger.info("=" * 80)
            return {"error": error_msg}

        except requests.exceptions.ConnectionError as e:
            error_msg = f"연결 오류 - FastAPI 서버에 접속할 수 없습니다: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"서버 주소: {url}")
            logger.info(f"💡 확인사항:")
            logger.info(f"   1. FastAPI 서버 실행 여부: 터미널에서 'start_fastapi.bat' 실행")
            logger.info(f"   2. 포트 8008이 다른 서비스에서 사용 중인지 확인")
            logger.info(f"   3. 환경 변수 설정 확인: STREAMLIT_LANGCHAIN_BASE_URL={base}")
            logger.info("=" * 80)
            return {"error": error_msg}

        except requests.exceptions.RequestException as e:
            error_msg = f"요청 오류: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.info("=" * 80)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"예상치 못한 오류: {str(e)}"
            logger.exception(f"❌ {error_msg}")
            logger.info("=" * 80)
            return {"error": error_msg}
