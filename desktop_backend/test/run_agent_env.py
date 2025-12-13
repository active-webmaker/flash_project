import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TMP_REPO = (PROJECT_ROOT / 'desktop_backend' / '.tmp_repo_integration').resolve()
TMP_REPO.mkdir(parents=True, exist_ok=True)

os.environ.setdefault('API_BASE_URL', 'http://127.0.0.1:8000/api/v1')
os.environ.setdefault('LOCAL_LLM_URL', 'http://127.0.0.1:8001/v1')
os.environ['REPO_PATH'] = str(TMP_REPO)

# Ensure project on path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DESKTOP_BACKEND_DIR = PROJECT_ROOT / 'desktop_backend'
if str(DESKTOP_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(DESKTOP_BACKEND_DIR))

from desktop_backend.main import main

if __name__ == '__main__':
    main()
