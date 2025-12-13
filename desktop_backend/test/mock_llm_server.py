import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

class Handler(BaseHTTPRequestHandler):
    server_version = "MockLLMServer/1.0"

    def _send_json(self, code:int, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            return {}

    def log_message(self, fmt, *args):
        # silence default logs
        pass

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/v1/chat/completions":
            req = self._read_json()
            # Very simple policy: first call we return a function_call to scan_file_tree.
            # If the prompt already contains a FunctionMessage content mentioning scan results,
            # we return a normal assistant message to end the graph.
            messages = req.get("messages", [])
            tool_called = any(m.get("role") == "function" for m in messages)
            if not tool_called:
                resp = {
                    "id": "mockcmpl-1",
                    "object": "chat.completion",
                    "created": 0,
                    "model": req.get("model", "mock"),
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "function_call": {
                                    "name": "scan_file_tree",
                                    "arguments": "{}"
                                }
                            }
                        }
                    ]
                }
                return self._send_json(200, resp)
            else:
                resp = {
                    "id": "mockcmpl-2",
                    "object": "chat.completion",
                    "created": 0,
                    "model": req.get("model", "mock"),
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": "Repository analyzed. Finishing.",
                            }
                        }
                    ]
                }
                return self._send_json(200, resp)
        return self._send_json(404, {"error": "not found"})

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/v1/models":
            return self._send_json(200, {"data": [{"id": "mock"}]})
        return self._send_json(404, {"error": "not found"})


def run(host="127.0.0.1", port=8001):
    server = HTTPServer((host, port), Handler)
    print(f"Mock LLM server running at http://{host}:{port}/v1 ... (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    run()
