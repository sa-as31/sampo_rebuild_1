import argparse
import json
import mimetypes
import sys
import traceback
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
REPO_ROOT = ROOT.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from web_demo.task_runtime import TaskRuntime

TASK_RUNTIME = TaskRuntime(REPO_ROOT / "results" / "mac_eval" / "task_runtime.sqlite3")


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        route, query = self._parse_request_path()

        if route == "/api/defaults":
            from web_demo.inference import defaults_response

            self._send_json(HTTPStatus.OK, defaults_response())
            return

        if route == "/api/tasks":
            limit = int((query.get("limit") or ["30"])[0])
            self._send_json(HTTPStatus.OK, TASK_RUNTIME.list_tasks(limit=limit))
            return

        if route == "/api/dashboard/summary":
            self._send_json(HTTPStatus.OK, self._build_dashboard_summary())
            return

        task_route = self._parse_task_route(route)
        if task_route:
            task_id, action = task_route
            if action == "events":
                after = int((query.get("after") or ["0"])[0])
                timeout = float((query.get("timeout") or ["15"])[0])
                self._stream_task_events(task_id, after_seq=after, timeout=timeout)
                return
            if action == "alerts":
                limit = int((query.get("limit") or ["20"])[0])
                payload = TASK_RUNTIME.get_alerts(task_id, limit=limit)
                if payload is None:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "Task not found"})
                    return
                self._send_json(HTTPStatus.OK, payload)
                return
            if action == "detail":
                payload = TASK_RUNTIME.get_task(task_id)
                if payload is None:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "Task not found"})
                    return
                self._send_json(HTTPStatus.OK, payload)
                return

        if route == "/uav-icon.png":
            icon_path = REPO_ROOT / "无人机.png"
            if not icon_path.exists():
                self.send_error(HTTPStatus.NOT_FOUND, "UAV icon not found")
                return
            self._send_file(icon_path)
            return

        if route in ("/", "/index.html"):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        route, _query = self._parse_request_path()
        payload = self._read_json_body()
        if payload is None:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON payload"})
            return

        if route == "/api/tasks":
            result = TASK_RUNTIME.create_task(payload)
            self._send_json(HTTPStatus.OK, result)
            return

        task_route = self._parse_task_route(route)
        if task_route:
            task_id, action = task_route
            if action == "control":
                command = str(payload.get("action") or "").lower()
                result = TASK_RUNTIME.control_task(task_id, command)
                if result is None:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "Task not found"})
                    return
                if result.get("error"):
                    self._send_json(HTTPStatus.BAD_REQUEST, result)
                    return
                self._send_json(HTTPStatus.OK, result)
                return

        if route != "/api/run-demo":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})
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

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _parse_request_path(self):
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query)
        return parsed.path, query

    def _parse_task_route(self, route: str):
        # Supported:
        #   /api/tasks/{task_id}
        #   /api/tasks/{task_id}/control
        #   /api/tasks/{task_id}/events
        #   /api/tasks/{task_id}/alerts
        parts = [part for part in route.split("/") if part]
        if len(parts) < 3 or parts[0] != "api" or parts[1] != "tasks":
            return None
        task_id = parts[2]
        if len(parts) == 3:
            return task_id, "detail"
        if len(parts) == 4 and parts[3] in ("control", "events", "alerts"):
            return task_id, parts[3]
        return None

    def _read_json_body(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def _stream_task_events(self, task_id: str, after_seq: int, timeout: float):
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        # Keep this handler thread open until client disconnects.
        while True:
            events = TASK_RUNTIME.wait_events(task_id, after_seq=after_seq, timeout=timeout)
            if events is None:
                self.wfile.write(b"data: {\"type\":\"error\",\"payload\":{\"error\":\"Task not found\"}}\n\n")
                self.wfile.flush()
                return
            try:
                if not events:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                    continue
                for event in events:
                    after_seq = int(event["seq"])
                    chunk = f"id: {after_seq}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return

    def _build_dashboard_summary(self):
        tasks = TASK_RUNTIME.list_tasks(limit=120)["tasks"]
        summary = {
            "total_tasks": len(tasks),
            "running_tasks": 0,
            "paused_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "stopped_tasks": 0,
            "avg_throughput": 0.0,
        }
        throughput_values = []
        for task in tasks:
            status = str(task.get("status") or "").upper()
            if status == "RUNNING":
                summary["running_tasks"] += 1
            elif status == "PAUSED":
                summary["paused_tasks"] += 1
            elif status == "COMPLETED":
                summary["completed_tasks"] += 1
            elif status == "FAILED":
                summary["failed_tasks"] += 1
            elif status == "STOPPED":
                summary["stopped_tasks"] += 1
            metrics = task.get("metrics") or {}
            throughput = metrics.get("throughput")
            if throughput is not None:
                try:
                    throughput_values.append(float(throughput))
                except (TypeError, ValueError):
                    pass
        if throughput_values:
            summary["avg_throughput"] = round(sum(throughput_values) / len(throughput_values), 4)
        return {"summary": summary}

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
