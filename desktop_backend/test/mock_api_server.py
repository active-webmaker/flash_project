import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# In-memory state
STATE = {
    "jobs_available": True,
    "logs": [],
}

class Handler(BaseHTTPRequestHandler):
    server_version = "MockAPIServer/1.0"

    def _send_json(self, code:int, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_no_content(self, code:int=204):
        self.send_response(code)
        self.end_headers()

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            return {}

    def log_message(self, fmt, *args):
        # Collect logs in memory instead of printing to stderr
        STATE["logs"].append(fmt % args)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/v1/health":
            return self._send_json(200, {"status": "ok"})
        return self._send_json(404, {"detail": "Not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        body = self._read_json()

        # Minimal endpoints used by agent.py
        if parsed.path == "/api/v1/agent/jobs/request":
            # Return a single job once, then 204
            if STATE.get("jobs_available", True):
                STATE["jobs_available"] = False
                job = {
                    "job_id": "job-1",
                    "job_type": "test",
                    "payload": {
                        "description": "You are an assistant. If you can, analyze repository and then finish.",
                        "metadata": {"result_url": None}
                    }
                }
                return self._send_json(200, {"jobs": [job]})
            else:
                return self._send_no_content(204)

        if parsed.path.endswith("/start"):
            return self._send_json(200, {"status": "started"})

        if parsed.path.endswith("/progress"):
            return self._send_json(200, {"status": "ok"})

        if parsed.path.endswith("/complete"):
            return self._send_json(200, {"status": "completed"})

        if parsed.path == "/api/v1/agent/callbacks/tool":
            return self._send_json(200, {"status": "logged"})

        if parsed.path == "/api/v1/agent/telemetry":
            return self._send_json(200, {"status": "ok"})

        if parsed.path == "/api/v1/agent/heartbeat":
            return self._send_json(200, {"status": "alive"})

        return self._send_json(404, {"detail": "Not found"})


def run(host="127.0.0.1", port=8000):
    server = HTTPServer((host, port), Handler)
    print(f"Mock API server running at http://{host}:{port}/api/v1 ... (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    run()
