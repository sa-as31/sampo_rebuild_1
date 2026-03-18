import argparse
import json
import mimetypes
import sys
import traceback
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
REPO_ROOT = ROOT.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/api/defaults":
            from web_demo.inference import defaults_response

            self._send_json(HTTPStatus.OK, defaults_response())
            return

        if self.path == "/uav-icon.png":
            icon_path = REPO_ROOT / "无人机.png"
            if not icon_path.exists():
                self.send_error(HTTPStatus.NOT_FOUND, "UAV icon not found")
                return
            self._send_file(icon_path)
            return

        if self.path in ("/", "/index.html"):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/run-demo":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON payload"})
            return

        try:
            from web_demo.inference import build_rollout

            result = build_rollout(payload)
            self._send_json(HTTPStatus.OK, result)
        except Exception as exc:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "error": str(exc),
                    "traceback": traceback.format_exc(limit=6),
                },
            )

    def log_message(self, fmt, *args):
        return super().log_message("[web-demo] " + fmt, *args)

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path: Path):
        body = file_path.read_bytes()
        content_type, _ = mimetypes.guess_type(file_path.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="Serve the UAV inference demo UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), DemoHandler)
    print(f"Serving web demo at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
