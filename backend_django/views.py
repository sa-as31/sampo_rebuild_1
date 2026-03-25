import json
import traceback
from pathlib import Path

from django.http import FileResponse, Http404, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from web_demo.task_runtime import TaskRuntime


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "web_demo" / "static"
TASK_RUNTIME = TaskRuntime(BASE_DIR / "results" / "mac_eval" / "task_runtime.sqlite3")


def json_ok(payload, status=200):
    return JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})


def json_error(message, status=400, **extra):
    payload = {"error": message}
    payload.update(extra)
    return json_ok(payload, status=status)


def read_json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def build_dashboard_summary():
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


@require_GET
def index_view(_request):
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise Http404("index.html not found")
    return FileResponse(index_path.open("rb"), content_type="text/html; charset=utf-8")


@require_GET
def uav_icon_view(_request):
    icon_path = BASE_DIR / "无人机.png"
    if not icon_path.exists():
        raise Http404("UAV icon not found")
    return FileResponse(icon_path.open("rb"), content_type="image/png")


@require_GET
def defaults_view(_request):
    from web_demo.inference import defaults_response

    return json_ok(defaults_response())


@csrf_exempt
@require_http_methods(["POST"])
def run_demo_view(request):
    payload = read_json_body(request)
    if payload is None:
        return json_error("Invalid JSON payload", status=400)
    try:
        from web_demo.inference import build_rollout

        return json_ok(build_rollout(payload))
    except Exception as exc:
        return json_error(str(exc), status=500, traceback=traceback.format_exc(limit=6))


@require_GET
def auth_state_view(_request):
    return json_ok(TASK_RUNTIME.get_auth_state())


@require_GET
def auth_options_view(_request):
    return json_ok(TASK_RUNTIME.get_auth_options())


@csrf_exempt
@require_http_methods(["POST"])
def auth_login_view(request):
    payload = read_json_body(request)
    if payload is None:
        return json_error("Invalid JSON payload", status=400)
    role = str(payload.get("role") or "")
    username = str(payload.get("username") or "")
    password = str(payload.get("password") or "")
    if not username or not password:
        return json_error("Missing username or password", status=400)
    result = TASK_RUNTIME.login(role=role, username=username, password=password)
    if result is None:
        return json_error("Invalid credentials", status=401)
    return json_ok(result)


@csrf_exempt
@require_http_methods(["POST"])
def auth_logout_view(_request):
    return json_ok(TASK_RUNTIME.logout())


@require_GET
def identity_view(_request):
    return json_ok(TASK_RUNTIME.get_identity())


@csrf_exempt
@require_http_methods(["POST"])
def identity_switch_view(request):
    payload = read_json_body(request)
    if payload is None:
        return json_error("Invalid JSON payload", status=400)
    user_id = str(payload.get("user_id") or "").strip()
    if not user_id:
        return json_error("Missing user_id", status=400)
    result = TASK_RUNTIME.switch_identity(user_id)
    if result is None:
        return json_error("User not found", status=404)
    return json_ok(result)


@require_http_methods(["GET", "POST"])
@csrf_exempt
def tasks_view(request):
    if request.method == "GET":
        limit = int(request.GET.get("limit", "30"))
        return json_ok(TASK_RUNTIME.list_tasks(limit=limit))

    payload = read_json_body(request)
    if payload is None:
        return json_error("Invalid JSON payload", status=400)
    return json_ok(TASK_RUNTIME.create_task(payload))


@require_GET
def dashboard_summary_view(_request):
    return json_ok(build_dashboard_summary())


@require_GET
def task_detail_view(_request, task_id):
    payload = TASK_RUNTIME.get_task(task_id)
    if payload is None:
        return json_error("Task not found", status=404)
    if payload.get("error"):
        return json_error(payload["error"], status=int(payload.get("status") or 400))
    return json_ok(payload)


@csrf_exempt
@require_http_methods(["POST"])
def task_control_view(request, task_id):
    payload = read_json_body(request)
    if payload is None:
        return json_error("Invalid JSON payload", status=400)
    command = str(payload.get("action") or "").lower()
    result = TASK_RUNTIME.control_task(task_id, command, payload)
    if result is None:
        return json_error("Task not found", status=404)
    if result.get("error"):
        return json_error(result["error"], status=400)
    return json_ok(result)


@require_GET
def task_alerts_view(request, task_id):
    limit = int(request.GET.get("limit", "20"))
    payload = TASK_RUNTIME.get_alerts(task_id, limit=limit)
    if payload is None:
        return json_error("Task not found", status=404)
    if payload.get("error"):
        return json_error(payload["error"], status=int(payload.get("status") or 400))
    return json_ok(payload)


@require_GET
def task_replay_view(_request, task_id):
    payload = TASK_RUNTIME.get_replay(task_id)
    if payload is None:
        return json_error("Task not found", status=404)
    if payload.get("error"):
        return json_error(payload["error"], status=int(payload.get("status") or 400))
    return json_ok(payload)


@require_http_methods(["GET", "POST"])
@csrf_exempt
def task_feedback_view(request, task_id):
    if request.method == "GET":
        limit = int(request.GET.get("limit", "20"))
        payload = TASK_RUNTIME.get_feedback(task_id, limit=limit)
        if payload is None:
            return json_error("Task not found", status=404)
        if payload.get("error"):
            return json_error(payload["error"], status=int(payload.get("status") or 400))
        return json_ok(payload)

    payload = read_json_body(request)
    if payload is None:
        return json_error("Invalid JSON payload", status=400)
    result = TASK_RUNTIME.submit_feedback(task_id, payload)
    if result is None:
        return json_error("Task not found", status=404)
    if result.get("error"):
        return json_error(result["error"], status=400)
    return json_ok(result)


@require_GET
def task_events_view(request, task_id):
    after_seq = int(request.GET.get("after", "0"))
    timeout = float(request.GET.get("timeout", "15"))

    def event_stream():
        current_after = after_seq
        while True:
            events = TASK_RUNTIME.wait_events(task_id, after_seq=current_after, timeout=timeout)
            if events is None:
                yield 'data: {"type":"error","payload":{"error":"Task not found"}}\n\n'
                return
            if not events:
                yield ": heartbeat\n\n"
                continue
            for event in events:
                current_after = int(event["seq"])
                yield f"id: {current_after}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream; charset=utf-8")
    response["Cache-Control"] = "no-store"
    response["X-Accel-Buffering"] = "no"
    return response
