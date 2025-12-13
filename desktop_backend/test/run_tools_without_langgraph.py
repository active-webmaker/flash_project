import os
import time
import json
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

# Use project modules
import sys
import types

# --- Stub langchain.tools.tool to avoid installing langchain ---
if 'langchain' not in sys.modules:
    langchain = types.ModuleType('langchain')
    sys.modules['langchain'] = langchain
if 'langchain.tools' not in sys.modules:
    tools_mod = types.ModuleType('langchain.tools')
    def tool(name=None):
        def decorator(fn):
            return fn
        return decorator
    tools_mod.tool = tool
    sys.modules['langchain.tools'] = tools_mod

# --- Ensure project root is on sys.path ---
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from desktop_backend.git_analyzer import GitAnalyzer
from desktop_backend.git_commit_module import GitCommitModule

# Do not load external .env that might set REPO_PATH to an absolute user path
# Only rely on API_BASE_URL if user explicitly exported; otherwise use default
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
TMP_REPO = (PROJECT_ROOT / "desktop_backend" / ".tmp_repo_integration").resolve()


def run(cmd, cwd=None):
    return subprocess.check_output(cmd, cwd=cwd, shell=True, text=True)


def ensure_repo(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    if not (path / ".git").exists():
        run("git init", cwd=str(path))
        (path / "README.md").write_text("temp repo for desktop_backend tests\n", encoding="utf-8")
        run("git add README.md", cwd=str(path))
        run("git -c user.email=test@example.com -c user.name=Tester commit -m 'init'", cwd=str(path))


def post(endpoint, payload):
    try:
        r = requests.post(f"{API_BASE_URL}{endpoint}", json=payload, timeout=5)
        return r.status_code, r.text
    except Exception as e:
        return -1, str(e)


def main():
    print(f"API_BASE_URL={API_BASE_URL}")
    print(f"TMP_REPO={TMP_REPO}")

    ensure_repo(TMP_REPO)

    analyzer = GitAnalyzer(repo_path=str(TMP_REPO))
    committer = GitCommitModule(repo_path=str(TMP_REPO))

    job_id = "manual-job-1"
    post("/agent/heartbeat", {"agent_id": "manual-agent", "status": "idle", "agent_version": "test"})
    post(f"/agent/jobs/{job_id}/start", {"agent_id": "manual-agent", "start_time": "2024-01-01T00:00:00Z"})
    post(f"/agent/jobs/{job_id}/progress", {"agent_id": "manual-agent", "log_message": "Scanning file tree"})

    files = analyzer.scan_file_tree()
    print(f"scan_file_tree -> {len(files)} files")
    requests.post(f"{API_BASE_URL}/agent/callbacks/tool", json={
        "run_id": job_id,
        "tool_name": "scan_file_tree",
        "tool_input": {},
        "tool_output": files[:5],
    })

    # Create a new test file and commit
    test_rel = "integration_test.txt"
    (TMP_REPO / test_rel).write_text("hello integration test\n", encoding="utf-8")
    post(f"/agent/jobs/{job_id}/progress", {"agent_id": "manual-agent", "log_message": "Creating commit"})
    result = committer.create_commit(message="test: add integration_test.txt", files_to_add=[test_rel])
    print(f"create_commit -> {result}")

    requests.post(f"{API_BASE_URL}/agent/callbacks/tool", json={
        "run_id": job_id,
        "tool_name": "create_commit",
        "tool_input": {"message": "test: add integration_test.txt", "files_to_add": [test_rel]},
        "tool_output": result,
    })

    # Get diff for the created commit if success
    diff_text = committer.get_diff(result.get("commit_hash", "HEAD"))
    print("get_diff ->\n" + diff_text[:500])

    post(f"/agent/jobs/{job_id}/progress", {"agent_id": "manual-agent", "log_message": "Finishing", "percent_complete": 100})
    post(f"/agent/jobs/{job_id}/complete", {"agent_id": "manual-agent", "status": "success", "summary": "OK"})
    requests.post(f"{API_BASE_URL}/agent/telemetry", json={
        "agent_id": "manual-agent",
        "metrics": [{"name": "tool_calls", "value": 2.0, "job_id": job_id}],
    })

    print("Done. Check mock API server logs for received events.")


if __name__ == "__main__":
    main()
