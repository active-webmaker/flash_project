
import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# 로그 디렉터리 생성
LOG_DIR = "/app/log"
os.makedirs(LOG_DIR, exist_ok=True)

# 로깅 설정 (파일 + 콘솔)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# 포맷터 정의
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 콘솔 핸들러
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 파일 핸들러 (회전식)
log_file = os.path.join(LOG_DIR, "agent.log")
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=10  # 최대 10개 파일 보관
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

main_logger = logging.getLogger(__name__)

def main():
    """
    Desktop Backend 에이전트의 메인 실행 함수.
    환경 변수를 로드하고 에이전트 루프를 시작합니다.
    """
    # .env 파일에서 환경 변수 로드
    load_dotenv()

    main_logger.info("Initializing Desktop Backend Agent...")

    # --- 환경 변수 유효성 검사 ---
    api_base_url = os.getenv("API_BASE_URL")
    local_llm_url = os.getenv("LOCAL_LLM_URL")
    repo_path = os.getenv("REPO_PATH")

    if not all([api_base_url, local_llm_url, repo_path]):
        main_logger.error("필수 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
        main_logger.error("필요: API_BASE_URL, LOCAL_LLM_URL, REPO_PATH")
        return

    main_logger.info(f"API Server URL: {api_base_url}")
    main_logger.info(f"Local LLM URL: {local_llm_url}")
    main_logger.info(f"Target Git Repo Path: {repo_path}")

    # --- 에이전트 실행 ---
    # agent.py가 로드될 때 이미 모든 설정이 완료되므로, run_agent 함수만 호출합니다.
    try:
        from agent import run_agent
        run_agent()
    except ImportError as e:
        main_logger.error(f"에이전트 모듈을 임포트하는 데 실패했습니다: {e}")
    except Exception as e:
        main_logger.critical(f"에이전트 실행 중 치명적인 오류 발생: {e}", exc_info=True)

if __name__ == "__main__":
    main()
