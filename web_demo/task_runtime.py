import json
import sqlite3
import threading
import time
import uuid
import hashlib
import hmac
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple


ALLOWED_TEMPLATES = {"warehouse", "campus", "emergency"}
ALLOWED_SOURCES = {"sample", "model"}
FINAL_STATUSES = {"COMPLETED", "FAILED", "STOPPED"}
RESTORABLE_STATUSES = {"PREPARING", "READY", "RUNNING", "PAUSED"}
REVIEW_STATUSES = {"PENDING_REVIEW", "REJECTED"}
DEFAULT_TASK_TICK_MS = 600

ROLE_PRIORITY = {"admin": 0, "requester": 1, "executor": 2}

TASK_CATEGORY_CONFIGS = {
    "patrol": {
        "label": "巡逻",
        "template": "campus",
        "default_mission_name": "campus_patrol_request",
    },
    "show": {
        "label": "表演",
        "template": "campus",
        "default_mission_name": "show_request",
    },
    "transport": {
        "label": "运输",
        "template": "emergency",
        "default_mission_name": "transport_request",
    },
}

TEMPLATE_CONFIGS = {
    "warehouse": {
        "map_name": "warehouse-grid-v1",
        "starts": [
            (1, 1, 10, 10),
            (10, 1, 2, 10),
            (1, 10, 10, 2),
            (10, 10, 2, 2),
        ],
    },
    "campus": {
        "map_name": "campus-road-v1",
        "starts": [
            (1, 2, 10, 9),
            (10, 2, 2, 9),
            (2, 10, 9, 2),
            (9, 10, 2, 2),
        ],
    },
    "emergency": {
        "map_name": "emergency-block-v1",
        "starts": [
            (1, 1, 10, 10),
            (10, 1, 1, 10),
            (1, 10, 10, 1),
            (10, 10, 1, 1),
        ],
    },
}

DEFAULT_USER_ACCOUNTS = [
    {
        "user_id": "u_admin_001",
        "username": "admin",
        "display_name": "系统管理员",
        "role": "admin",
        "department": "调度中心",
        "title": "平台运维负责人",
        "password": "1",
    },
    {
        "user_id": "u_req_001",
        "username": "requester01",
        "display_name": "申请人01",
        "role": "requester",
        "department": "任务申请组",
        "title": "飞行任务申请员",
        "password": "1",
    },
    {
        "user_id": "u_exec_001",
        "username": "executor01",
        "display_name": "飞手01",
        "role": "executor",
        "department": "运营飞行组",
        "title": "无人机飞手",
        "password": "1",
    },
    {
        "user_id": "u_exec_002",
        "username": "executor02",
        "display_name": "飞手02",
        "role": "executor",
        "department": "运营飞行组",
        "title": "无人机飞手",
        "password": "1",
    },
    {
        "user_id": "u_exec_003",
        "username": "executor03",
        "display_name": "飞手03",
        "role": "executor",
        "department": "运营飞行组",
        "title": "无人机飞手",
        "password": "1",
    },
    {
        "user_id": "u_exec_004",
        "username": "executor04",
        "display_name": "飞手04",
        "role": "executor",
        "department": "运营飞行组",
        "title": "无人机飞手",
        "password": "1",
    },
    {
        "user_id": "u_exec_005",
        "username": "executor05",
        "display_name": "飞手05",
        "role": "executor",
        "department": "运营飞行组",
        "title": "无人机飞手",
        "password": "1",
    },
    {
        "user_id": "u_exec_006",
        "username": "executor06",
        "display_name": "飞手06",
        "role": "executor",
        "department": "运营飞行组",
        "title": "无人机飞手",
        "password": "1",
    },
    {
        "user_id": "u_exec_007",
        "username": "executor07",
        "display_name": "飞手07",
        "role": "executor",
        "department": "运营飞行组",
        "title": "无人机飞手",
        "password": "1",
    },
    {
        "user_id": "u_exec_008",
        "username": "executor08",
        "display_name": "飞手08",
        "role": "executor",
        "department": "运营飞行组",
        "title": "无人机飞手",
        "password": "1",
    },
    {
        "user_id": "u_exec_009",
        "username": "executor09",
        "display_name": "飞手09",
        "role": "executor",
        "department": "运营飞行组",
        "title": "无人机飞手",
        "password": "1",
    },
    {
        "user_id": "u_exec_010",
        "username": "executor10",
        "display_name": "飞手10",
        "role": "executor",
        "department": "运营飞行组",
        "title": "无人机飞手",
        "password": "1",
    },
]
DEFAULT_ACTIVE_USER_ID = "u_exec_001"


def now_ts() -> float:
    return time.time()


def clamp_int(value: Any, default: int, lower: int, upper: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(lower, min(upper, parsed))


def normalize_username(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_role(value: Any) -> str:
    role = str(value or "").strip().lower()
    if role == "admin":
        return "admin"
    if role == "requester":
        return "requester"
    return "executor"


def normalize_task_category(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in TASK_CATEGORY_CONFIGS:
        return raw
    alias_map = {
        "巡逻": "patrol",
        "表演": "show",
        "运输": "transport",
    }
    return alias_map.get(raw, "patrol")


def hash_password(raw: str) -> str:
    return hashlib.sha256(str(raw or "").encode("utf-8")).hexdigest()


@dataclass
class LiveTask:
    task_id: str
    mission_name: str
    template: str
    source: str
    params: Dict[str, Any]
    status: str = "PREPARING"
    created_at: float = field(default_factory=now_ts)
    updated_at: float = field(default_factory=now_ts)
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    error: Optional[str] = None
    environment: Optional[Dict[str, Any]] = None
    frames: List[Dict[str, Any]] = field(default_factory=list)
    frame_index: int = 0
    cycle_step_offset: int = 0
    cycle_task_offset: int = 0
    base_metrics: Dict[str, Any] = field(default_factory=dict)
    runtime_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    tick_ms: int = DEFAULT_TASK_TICK_MS
    cumulative_conflicts: int = 0
    alert_count: int = 0
    stall_steps: Dict[int, int] = field(default_factory=dict)
    last_positions: Dict[int, Tuple[int, int]] = field(default_factory=dict)
    last_alert_step: Dict[str, int] = field(default_factory=dict)
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    events: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=2048))
    next_seq: int = 1
    stop_requested: bool = False
    runner_thread: Optional[threading.Thread] = None
    prep_thread: Optional[threading.Thread] = None
    lock: threading.RLock = field(default_factory=threading.RLock)
    cond: threading.Condition = field(init=False)

    def __post_init__(self):
        self.cond = threading.Condition(self.lock)

    @property
    def total_frames(self) -> int:
        return len(self.frames)


class TaskRuntime:
    def __init__(self, db_path: Path):
        self.db = TaskDB(db_path)
        self.tasks: Dict[str, LiveTask] = {}
        self.tasks_lock = threading.RLock()
        self.replay_dir = self.db.db_path.parent / "task_replays"
        self.replay_dir.mkdir(parents=True, exist_ok=True)
        self._restore_live_tasks()

    def get_auth_state(self) -> Dict[str, Any]:
        return self.db.get_auth_state()

    def get_auth_options(self) -> Dict[str, Any]:
        return self.db.get_auth_options()

    def login(self, role: str, username: str, password: str) -> Optional[Dict[str, Any]]:
        return self.db.login(role=role, username=username, password=password)

    def logout(self) -> Dict[str, Any]:
        return self.db.logout()

    def get_identity(self) -> Dict[str, Any]:
        return self.db.get_identity()

    def switch_identity(self, user_id: str) -> Optional[Dict[str, Any]]:
        user_id = str(user_id or "").strip()
        if not user_id:
            return None
        return self.db.switch_identity(user_id)

    def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        current = self.db.get_current_user()
        if current and current.get("role") == "requester":
            return self._create_task_request(payload, current)
        return self._create_dispatch_task(payload)

    def _create_dispatch_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        template = str(payload.get("template") or "warehouse").lower()
        if template not in ALLOWED_TEMPLATES:
            template = "warehouse"

        source = str(payload.get("source") or "sample").lower()
        if source not in ALLOWED_SOURCES:
            source = "sample"

        mission_name = str(payload.get("mission_name") or f"{template}_mission")
        tick_ms = clamp_int(payload.get("tick_ms"), DEFAULT_TASK_TICK_MS, 120, 2000)

        params = normalize_task_payload(payload, template=template)
        task_id = uuid.uuid4().hex[:12]
        live = LiveTask(
            task_id=task_id,
            mission_name=mission_name,
            template=template,
            source=source,
            params=params,
            tick_ms=tick_ms,
        )

        with self.tasks_lock:
            self.tasks[task_id] = live

        self.db.insert_task(
            task_id=task_id,
            mission_name=mission_name,
            template=template,
            source=source,
            status=live.status,
            params=params,
            created_at=live.created_at,
            updated_at=live.updated_at,
            tick_ms=tick_ms,
        )

        self._emit_event(live, "task_created", {"task": self._task_brief(live)})
        live.prep_thread = threading.Thread(target=self._prepare_task, args=(task_id,), daemon=True)
        live.prep_thread.start()
        return {
            "task": self._task_brief(live),
            "last_event_seq": live.next_seq - 1,
        }

    def _create_task_request(self, payload: Dict[str, Any], current_user: Dict[str, Any]) -> Dict[str, Any]:
        task_category = normalize_task_category(payload.get("task_category"))
        category_config = TASK_CATEGORY_CONFIGS[task_category]
        mission_name = str(payload.get("mission_name") or category_config["default_mission_name"]).strip() or category_config["default_mission_name"]
        requested_location = str(payload.get("requested_location") or payload.get("location") or "").strip() or "待管理员确认地点"
        requested_ts = None
        try:
            requested_ts = float(payload.get("scheduled_start_at") or 0) or None
        except (TypeError, ValueError):
            requested_ts = None
        requested_label = str(payload.get("scheduled_start_label") or "").strip()
        if requested_ts and not requested_label:
            requested_label = time.strftime("%Y-%m-%d %H:%M", time.localtime(requested_ts))

        params = normalize_task_payload(
            {
                "task_origin": "request",
                "review_status": "pending",
                "task_category": task_category,
                "task_category_label": category_config["label"],
                "continuous_patrol": task_category == "patrol",
                "requested_location": requested_location,
                "requester_user_id": str(current_user.get("user_id") or ""),
                "requester_username": str(current_user.get("username") or ""),
                "requester_display_name": str(current_user.get("display_name") or ""),
                "scheduled_start_at": requested_ts,
                "scheduled_start_label": requested_label,
                "map_name": requested_location or TEMPLATE_CONFIGS[category_config["template"]]["map_name"],
            },
            template=category_config["template"],
        )
        task_id = uuid.uuid4().hex[:12]
        created_at = now_ts()
        task_payload = {
            "task_id": task_id,
            "mission_name": mission_name,
            "template": category_config["template"],
            "source": "sample",
            "status": "PENDING_REVIEW",
            "tick_ms": clamp_int(payload.get("tick_ms"), DEFAULT_TASK_TICK_MS, 120, 2000),
            "params": params,
            "metrics": {},
            "error": None,
            "total_frames": 0,
            "current_frame_index": 0,
            "created_at": created_at,
            "started_at": None,
            "ended_at": None,
            "updated_at": created_at,
        }
        self.db.insert_task(
            task_id=task_id,
            mission_name=mission_name,
            template=category_config["template"],
            source="sample",
            status="PENDING_REVIEW",
            params=params,
            created_at=created_at,
            updated_at=created_at,
            tick_ms=task_payload["tick_ms"],
        )
        return {"task": task_payload, "request_submitted": True}

    def list_tasks(self, limit: int = 30) -> Dict[str, Any]:
        limit = max(1, min(int(limit), 200))
        current = self.db.get_current_user()
        tasks = self.db.list_tasks(limit=limit)
        visible = [task for task in tasks if self._can_view_task(task, current)]
        return {"tasks": visible}

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        current = self.db.get_current_user()
        live = self._get_live_task(task_id)
        if live is None:
            stored = self.db.get_task(task_id)
            if stored is None:
                return None
            if not self._can_view_task(stored, current):
                return {"error": "无权访问该任务", "status": 403}
            return {"task": stored, "snapshot": None, "alerts": self.db.get_alerts(task_id, limit=20)}

        with live.lock:
            task = self._task_brief(live)
            if not self._can_view_task(task, current):
                return {"error": "无权访问该任务", "status": 403}
            return {
                "task": task,
                "snapshot": self._build_snapshot(live, include_environment=True),
                "alerts": list(reversed(live.alerts[-20:])),
            }

    def get_alerts(self, task_id: str, limit: int = 20) -> Optional[Dict[str, Any]]:
        current = self.db.get_current_user()
        live = self._get_live_task(task_id)
        if live is None:
            stored = self.db.get_task(task_id)
            if stored is None:
                return None
            if not self._can_view_task(stored, current):
                return {"error": "无权访问该任务", "status": 403}
            return {"task_id": task_id, "alerts": self.db.get_alerts(task_id, limit=limit)}
        with live.lock:
            task = self._task_brief(live)
            if not self._can_view_task(task, current):
                return {"error": "无权访问该任务", "status": 403}
            alerts = list(reversed(live.alerts[-limit:]))
        return {"task_id": task_id, "alerts": alerts}

    def get_feedback(self, task_id: str, limit: int = 20) -> Optional[Dict[str, Any]]:
        stored = self.db.get_task(task_id)
        if stored is None and self._get_live_task(task_id) is None:
            return None
        current = self.db.get_current_user()
        reference = stored
        if reference is None:
            live = self._get_live_task(task_id)
            reference = self._task_brief(live) if live is not None else None
        if reference is not None and not self._can_view_task(reference, current):
            return {"error": "无权访问该任务", "status": 403}
        return {"task_id": task_id, "feedback": self.db.get_feedback(task_id, limit=limit)}

    def submit_feedback(self, task_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        task = self.db.get_task(task_id)
        live = self._get_live_task(task_id)
        if task is None and live is None:
            return None

        current = self.db.get_current_user()
        if current is None:
            return {"error": "未检测到当前登录账号"}
        task_payload = task or self._task_brief(live)
        if not self._can_view_task(task_payload, current):
            return {"error": "当前账号不能向该任务提交反馈"}

        category = str(payload.get("category") or "issue").strip().lower()
        if category not in {"issue", "risk", "note", "delay_request", "anomaly"}:
            category = "issue"

        message = str(payload.get("message") or "").strip()
        if not message:
            return {"error": "反馈内容不能为空"}

        params = task_payload.get("params") or {}
        assignee_user_id = str(params.get("assignee_user_id") or "")
        if current.get("role") == "executor" and assignee_user_id and assignee_user_id != current.get("user_id"):
            return {"error": "当前飞手不能提交未分配给自己的任务反馈"}

        feedback = {
            "task_id": task_id,
            "user_id": str(current.get("user_id") or ""),
            "username": str(current.get("username") or ""),
            "display_name": str(current.get("display_name") or ""),
            "role": str(current.get("role") or ""),
            "category": category,
            "message": message,
            "created_at": now_ts(),
        }
        self.db.insert_feedback(task_id, feedback)

        if live is not None:
            self._emit_event(live, "feedback_added", {"task_id": task_id, "feedback": feedback, "task": self._task_brief(live)})

        return {"task_id": task_id, "feedback": feedback}

    def get_replay(self, task_id: str) -> Optional[Dict[str, Any]]:
        current = self.db.get_current_user()
        live = self._get_live_task(task_id)
        if live is None:
            stored = self.db.get_task(task_id)
            if stored is None:
                return None
            if not self._can_view_task(stored, current):
                return {"error": "无权访问该任务", "status": 403}
            persisted = self._load_persisted_replay(task_id)
            if persisted is not None:
                persisted["task"] = stored
                return persisted
            rebuilt = self._rebuild_historical_replay(stored)
            if rebuilt is not None:
                return rebuilt
            return {
                "task_id": task_id,
                "available": False,
                "reason": "未找到该任务的历史回放文件，且按任务参数重建回放失败。",
                "task": stored,
            }
        with live.lock:
            task = self._task_brief(live)
            if not self._can_view_task(task, current):
                return {"error": "无权访问该任务", "status": 403}
            payload = self._build_replay_response(
                task_id=task_id,
                task=task,
                environment=live.environment,
                frames=live.frames,
                metrics=live.base_metrics,
                meta={"warnings": list(live.warnings or [])},
            )
        self._persist_replay_payload(payload)
        return payload

    def control_task(self, task_id: str, action: str, payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        action = str(action or "").lower()
        payload = dict(payload or {})
        if action in {"approve", "reject"}:
            return self._review_task_request(task_id, action, payload)
        current = self.db.get_current_user()
        if current is None:
            return {"error": "未检测到当前登录账号"}
        live = self._get_live_task(task_id)
        if live is None:
            return None

        with live.lock:
            task = self._task_brief(live)
            if not self._can_control_task(task, current, action):
                return {"error": "当前账号无权操作该任务"}
            if action == "start":
                self._handle_start_locked(live)
            elif action == "pause":
                if live.status == "RUNNING":
                    live.status = "PAUSED"
                    if live.runtime_metrics:
                        live.runtime_metrics["status"] = "PAUSED"
                    live.updated_at = now_ts()
                    self._emit_event(live, "task_status", {"status": "PAUSED", "task": self._task_brief(live)})
                    self._persist_runtime_state(live)
            elif action == "resume":
                if live.status == "PAUSED":
                    live.status = "RUNNING"
                    if live.runtime_metrics:
                        live.runtime_metrics["status"] = "RUNNING"
                    live.updated_at = now_ts()
                    self._emit_event(live, "task_status", {"status": "RUNNING", "task": self._task_brief(live)})
                    self._persist_runtime_state(live)
                    if not (live.runner_thread and live.runner_thread.is_alive()):
                        live.runner_thread = threading.Thread(target=self._run_task_loop, args=(task_id,), daemon=True)
                        live.runner_thread.start()
                    live.cond.notify_all()
            elif action == "stop":
                if live.status not in FINAL_STATUSES:
                    live.status = "STOPPED"
                    if live.runtime_metrics:
                        live.runtime_metrics["status"] = "STOPPED"
                    live.stop_requested = True
                    live.ended_at = now_ts()
                    live.updated_at = live.ended_at
                    self._emit_event(live, "task_stopped", {"task": self._task_brief(live), "snapshot": self._build_snapshot(live)})
                    self._persist_runtime_state(live)
                    live.cond.notify_all()
            elif action == "set_speed":
                tick_ms = clamp_int(payload.get("tick_ms"), live.tick_ms, 120, 2400)
                live.tick_ms = tick_ms
                live.params["tick_ms"] = tick_ms
                live.updated_at = now_ts()
                self._persist_runtime_state(live)
                self._emit_event(
                    live,
                    "task_speed_changed",
                    {"task": self._task_brief(live), "tick_ms": tick_ms},
                )
            else:
                return {"error": f"Unsupported action: {action}"}

            return {"task": self._task_brief(live)}

    def _review_task_request(self, task_id: str, action: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        stored = self.db.get_task(task_id)
        if stored is None:
            return None
        current = self.db.get_current_user()
        if not current or current.get("role") != "admin":
            return {"error": "仅管理员可审核任务申请"}
        if stored.get("status") != "PENDING_REVIEW":
            return {"error": "当前任务申请不处于待审核状态"}

        params = dict(stored.get("params") or {})
        review_note = str(payload.get("review_note") or "").strip()
        if review_note:
            params["review_note"] = review_note
        params["reviewed_by_user_id"] = str(current.get("user_id") or "")
        params["reviewed_by_display_name"] = str(current.get("display_name") or "")
        params["reviewed_at"] = now_ts()

        if action == "reject":
            params["review_status"] = "rejected"
            updated = self.db.update_task_definition(
                task_id=task_id,
                mission_name=stored["mission_name"],
                template=stored["template"],
                source=stored["source"],
                status="REJECTED",
                params=params,
                tick_ms=int(stored.get("tick_ms") or DEFAULT_TASK_TICK_MS),
                updated_at=now_ts(),
            )
            return {"task": updated, "review_action": "rejected"}

        assignee_user_id = str(payload.get("assignee_user_id") or "").strip()
        assignee_display_name = str(payload.get("assignee_display_name") or "").strip()
        if not assignee_user_id:
            return {"error": "审核通过前请先指定飞手"}
        params["assignee_user_id"] = assignee_user_id
        params["assignee_display_name"] = assignee_display_name or assignee_user_id
        params["review_status"] = "approved"

        merged = normalize_task_payload(
            {
                **params,
                "map_name": payload.get("map_name") or params.get("map_name"),
                "source": payload.get("source") or stored.get("source") or "sample",
                "num_agents": payload.get("num_agents") or params.get("num_agents"),
                "max_frames": payload.get("max_frames") or params.get("max_frames"),
                "tick_ms": payload.get("tick_ms") or stored.get("tick_ms") or DEFAULT_TASK_TICK_MS,
                "scheduled_start_at": payload.get("scheduled_start_at") if payload.get("scheduled_start_at") is not None else params.get("scheduled_start_at"),
                "scheduled_start_label": payload.get("scheduled_start_label") or params.get("scheduled_start_label"),
            },
            template=str(stored.get("template") or "warehouse"),
        )
        source = str(payload.get("source") or stored.get("source") or "sample").lower()
        if source not in ALLOWED_SOURCES:
            source = "sample"
        tick_ms = clamp_int(payload.get("tick_ms") or stored.get("tick_ms"), DEFAULT_TASK_TICK_MS, 120, 2000)
        updated = self.db.update_task_definition(
            task_id=task_id,
            mission_name=stored["mission_name"],
            template=stored["template"],
            source=source,
            status="PREPARING",
            params=merged,
            tick_ms=tick_ms,
            updated_at=now_ts(),
        )
        live = LiveTask(
            task_id=task_id,
            mission_name=str(updated["mission_name"]),
            template=str(updated["template"]),
            source=str(updated["source"]),
            params=dict(updated["params"] or {}),
            status="PREPARING",
            created_at=float(updated["created_at"]),
            updated_at=float(updated["updated_at"]),
            tick_ms=int(updated["tick_ms"]),
        )
        with self.tasks_lock:
            self.tasks[task_id] = live
        self._emit_event(live, "task_approved", {"task": self._task_brief(live)})
        live.prep_thread = threading.Thread(target=self._prepare_task, args=(task_id,), daemon=True)
        live.prep_thread.start()
        return {"task": self._task_brief(live), "review_action": "approved"}

    def wait_events(self, task_id: str, after_seq: int, timeout: float = 15.0) -> Optional[List[Dict[str, Any]]]:
        live = self._get_live_task(task_id)
        if live is None:
            return None

        deadline = now_ts() + max(0.5, min(timeout, 60.0))
        with live.lock:
            while True:
                pending = [event for event in live.events if event["seq"] > after_seq]
                if pending:
                    return pending
                remaining = deadline - now_ts()
                if remaining <= 0:
                    return []
                live.cond.wait(timeout=remaining)

    def _prepare_task(self, task_id: str):
        live = self._get_live_task(task_id)
        if live is None:
            return

        try:
            playback = self._load_playback(live)
        except Exception as exc:
            with live.lock:
                live.status = "FAILED"
                live.error = str(exc)
                live.ended_at = now_ts()
                live.updated_at = live.ended_at
                self._persist_runtime_state(live)
                self._emit_event(
                    live,
                    "task_failed",
                    {
                        "task": self._task_brief(live),
                        "error": str(exc),
                    },
                )
            return

        with live.lock:
            live.environment = playback["environment"]
            live.frames = playback["frames"]
            live.base_metrics = playback.get("metrics") or {}
            live.warnings = list(playback.get("meta", {}).get("warnings") or [])
            live.frame_index = 0
            live.status = "READY"
            live.updated_at = now_ts()
            if live.frames:
                first_frame = live.frames[0]
                live.runtime_metrics = self._calculate_runtime_metrics(live, first_frame)
            else:
                live.runtime_metrics = self._blank_runtime_metrics(live)

            self._persist_runtime_state(live)
            self._emit_event(
                live,
                "task_ready",
                {
                    "task": self._task_brief(live),
                    "snapshot": self._build_snapshot(live, include_environment=True),
                },
            )

            if live.source == "model" and live.warnings:
                for warning in live.warnings:
                    self._emit_alert(live, "warning", "MODEL_RUNTIME_WARNING", warning, frame_step=0)

            replay_payload = self._build_replay_response(
                task_id=live.task_id,
                task=self._task_brief(live),
                environment=live.environment,
                frames=live.frames,
                metrics=live.base_metrics,
                meta=playback.get("meta") or {},
            )

        self._persist_replay_payload(replay_payload)

    def _load_playback(self, live: LiveTask) -> Dict[str, Any]:
        return self._build_playback(source=live.source, template=live.template, params=live.params)

    def _build_playback(self, source: str, template: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if source == "model":
            try:
                from web_demo.inference import build_rollout

                return build_rollout(params)
            except Exception as exc:
                fallback = build_sample_rollout(template, params)
                fallback.setdefault("meta", {}).setdefault("warnings", [])
                fallback["meta"]["warnings"].append(f"Model playback failed, fallback to sample: {exc}")
                return fallback
        return build_sample_rollout(template, params)

    def _run_task_loop(self, task_id: str):
        live = self._get_live_task(task_id)
        if live is None:
            return

        while True:
            cycle_reset = False
            with live.lock:
                if live.status in FINAL_STATUSES or live.stop_requested:
                    return
                if live.status != "RUNNING":
                    live.cond.wait(timeout=0.25)
                    continue
                if not live.frames:
                    live.status = "FAILED"
                    live.error = "No playback frames available"
                    live.ended_at = now_ts()
                    live.updated_at = live.ended_at
                    self._persist_runtime_state(live)
                    self._emit_event(live, "task_failed", {"task": self._task_brief(live), "error": live.error})
                    return

                last_index = len(live.frames) - 1
                if live.frame_index >= last_index:
                    if bool(live.params.get("continuous_patrol")) and live.frames:
                        live.cycle_step_offset += max(1, int(live.frames[-1].get("step", last_index)) + 1)
                        live.cycle_task_offset += max(0, int(live.frames[-1].get("tasks_completed", 0)))
                        live.frame_index = 0
                        frame = live.frames[live.frame_index]
                        live.runtime_metrics = self._calculate_runtime_metrics(live, frame)
                        self._detect_alerts(live, frame)
                        live.updated_at = now_ts()
                        self._persist_runtime_state(live)
                        self._emit_event(
                            live,
                            "frame_update",
                            {
                                "task": self._task_brief(live),
                                "snapshot": self._build_snapshot(live),
                            },
                        )
                        cycle_reset = True
                    else:
                        live.status = "COMPLETED"
                        if live.runtime_metrics:
                            live.runtime_metrics["status"] = "COMPLETED"
                        live.ended_at = now_ts()
                        live.updated_at = live.ended_at
                        self._persist_runtime_state(live)
                        self._emit_event(
                            live,
                            "task_completed",
                            {
                                "task": self._task_brief(live),
                                "snapshot": self._build_snapshot(live),
                            },
                        )
                        return

            if cycle_reset:
                time.sleep(live.tick_ms / 1000.0)
                continue
            time.sleep(live.tick_ms / 1000.0)

            with live.lock:
                if live.status != "RUNNING":
                    continue
                live.frame_index += 1
                frame = live.frames[live.frame_index]
                live.runtime_metrics = self._calculate_runtime_metrics(live, frame)
                self._detect_alerts(live, frame)
                live.updated_at = now_ts()
                self._persist_runtime_state(live)
                self._emit_event(
                    live,
                    "frame_update",
                    {
                        "task": self._task_brief(live),
                        "snapshot": self._build_snapshot(live),
                    },
                )

    def _handle_start_locked(self, live: LiveTask):
        if live.status == "PREPARING":
            self._emit_event(
                live,
                "task_status",
                {"status": "PREPARING", "message": "Task is still preparing.", "task": self._task_brief(live)},
            )
            return

        if live.status in FINAL_STATUSES and live.frames:
            live.frame_index = 0
            live.cycle_step_offset = 0
            live.cycle_task_offset = 0
            live.cumulative_conflicts = 0
            live.alert_count = 0
            live.alerts = []
            live.stall_steps = {}
            live.last_positions = {}
            live.last_alert_step = {}
            live.runtime_metrics = self._calculate_runtime_metrics(live, live.frames[0])

        if live.status in {"READY", "PAUSED"} or live.status in FINAL_STATUSES:
            live.started_at = live.started_at or now_ts()
            live.stop_requested = False
            live.status = "RUNNING"
            if live.runtime_metrics:
                live.runtime_metrics["status"] = "RUNNING"
            live.updated_at = now_ts()
            self._persist_runtime_state(live)
            self._emit_event(live, "task_status", {"status": "RUNNING", "task": self._task_brief(live)})
            if not (live.runner_thread and live.runner_thread.is_alive()):
                live.runner_thread = threading.Thread(target=self._run_task_loop, args=(live.task_id,), daemon=True)
                live.runner_thread.start()
            live.cond.notify_all()

    def _calculate_runtime_metrics(self, live: LiveTask, frame: Dict[str, Any]) -> Dict[str, Any]:
        step = int(frame.get("step", live.frame_index)) + int(live.cycle_step_offset)
        tasks_completed = int(frame.get("tasks_completed", 0)) + int(live.cycle_task_offset)
        frame_conflicts = int(frame.get("vertex_conflicts", 0))
        live.cumulative_conflicts += frame_conflicts

        online = len(frame.get("agents", []))
        throughput = round(tasks_completed / max(1, step), 4)
        avg_latency = round(step / max(1, tasks_completed), 2)

        return {
            "online": online,
            "tasks_completed": tasks_completed,
            "throughput": throughput,
            "avg_latency": avg_latency,
            "frame_conflicts": frame_conflicts,
            "cumulative_conflicts": int(live.cumulative_conflicts),
            "alerts": int(live.alert_count),
            "step": step,
            "status": live.status,
        }

    def _blank_runtime_metrics(self, live: LiveTask) -> Dict[str, Any]:
        return {
            "online": 0,
            "tasks_completed": 0,
            "throughput": 0.0,
            "avg_latency": 0.0,
            "frame_conflicts": 0,
            "cumulative_conflicts": 0,
            "alerts": int(live.alert_count),
            "step": 0,
            "status": live.status,
        }

    def _detect_alerts(self, live: LiveTask, frame: Dict[str, Any]):
        step = int(frame.get("step", live.frame_index))
        conflicts = int(frame.get("vertex_conflicts", 0))
        if conflicts > 0:
            self._emit_alert(
                live,
                "warning",
                "VERTEX_CONFLICT",
                f"Step {step}: detected {conflicts} vertex conflict(s).",
                frame_step=step,
            )

        for agent in frame.get("agents", []):
            aid = int(agent["id"])
            pos = (int(agent["x"]), int(agent["y"]))
            prev = live.last_positions.get(aid)
            if prev == pos:
                live.stall_steps[aid] = live.stall_steps.get(aid, 0) + 1
            else:
                live.stall_steps[aid] = 0
            live.last_positions[aid] = pos

            if live.stall_steps[aid] == 6:
                code = f"STALL_AGENT_{aid}"
                self._emit_alert(
                    live,
                    "info",
                    code,
                    f"Agent {aid + 1} has not moved for 6 steps near ({pos[0]}, {pos[1]}).",
                    frame_step=step,
                )

        if live.total_frames and step >= live.total_frames - 1:
            if frame.get("tasks_completed", 0) <= 0:
                self._emit_alert(
                    live,
                    "warning",
                    "LOW_THROUGHPUT_TIMEOUT",
                    "Reached final frame with zero completed tasks.",
                    frame_step=step,
                )

    def _emit_alert(self, live: LiveTask, level: str, code: str, message: str, frame_step: int):
        last_step = live.last_alert_step.get(code, -99999)
        if frame_step - last_step < 5:
            return
        live.last_alert_step[code] = frame_step

        alert = {
            "ts": now_ts(),
            "level": level,
            "code": code,
            "message": message,
            "frame_step": int(frame_step),
        }
        live.alert_count += 1
        live.alerts.append(alert)
        if len(live.alerts) > 120:
            live.alerts = live.alerts[-120:]

        self.db.insert_alert(live.task_id, alert)
        self._emit_event(live, "alert", {"task_id": live.task_id, "alert": alert, "task": self._task_brief(live)})

    def _build_snapshot(self, live: LiveTask, include_environment: bool = False) -> Dict[str, Any]:
        frame = live.frames[live.frame_index] if live.frames and live.frame_index < len(live.frames) else None
        payload = {
            "task": self._task_brief(live),
            "frame": frame,
            "metrics": live.runtime_metrics or self._blank_runtime_metrics(live),
            "alerts": list(reversed(live.alerts[-8:])),
        }
        if include_environment:
            payload["environment"] = live.environment
        return payload

    def _task_brief(self, live: LiveTask) -> Dict[str, Any]:
        return {
            "task_id": live.task_id,
            "mission_name": live.mission_name,
            "template": live.template,
            "source": live.source,
            "status": live.status,
            "tick_ms": live.tick_ms,
            "params": dict(live.params),
            "metrics": dict(live.runtime_metrics or {}),
            "created_at": live.created_at,
            "started_at": live.started_at,
            "ended_at": live.ended_at,
            "updated_at": live.updated_at,
            "total_frames": live.total_frames,
            "current_frame_index": int(live.frame_index),
            "error": live.error,
            "warnings": live.warnings,
        }

    def _emit_event(self, live: LiveTask, event_type: str, payload: Dict[str, Any]):
        with live.lock:
            event = {
                "seq": live.next_seq,
                "type": event_type,
                "ts": now_ts(),
                "payload": payload,
            }
            live.next_seq += 1
            live.events.append(event)
            live.cond.notify_all()
        self.db.insert_event(live.task_id, event)

    def _persist_runtime_state(self, live: LiveTask):
        self.db.update_task_runtime(
            task_id=live.task_id,
            status=live.status,
            updated_at=live.updated_at,
            started_at=live.started_at,
            ended_at=live.ended_at,
            current_frame_index=live.frame_index,
            total_frames=live.total_frames,
            metrics=live.runtime_metrics,
            error=live.error,
        )

    def _get_live_task(self, task_id: str) -> Optional[LiveTask]:
        with self.tasks_lock:
            return self.tasks.get(task_id)

    def _can_view_task(self, task: Optional[Dict[str, Any]], current: Optional[Dict[str, Any]]) -> bool:
        if task is None or current is None:
            return False
        role = normalize_role(current.get("role"))
        if role == "admin":
            return True
        params = task.get("params") or {}
        user_id = str(current.get("user_id") or "")
        if role == "requester":
            return str(params.get("requester_user_id") or "") == user_id
        if role == "executor":
            return str(params.get("assignee_user_id") or "") == user_id
        return False

    def _can_control_task(self, task: Optional[Dict[str, Any]], current: Optional[Dict[str, Any]], action: str) -> bool:
        if task is None or current is None:
            return False
        role = normalize_role(current.get("role"))
        if role == "admin":
            return True
        if role != "executor":
            return False
        if action not in {"start", "pause", "resume", "stop", "set_speed"}:
            return False
        params = task.get("params") or {}
        return str(params.get("assignee_user_id") or "") == str(current.get("user_id") or "")

    def _restore_live_tasks(self):
        for stored in self.db.list_restorable_tasks(limit=300):
            task_id = str(stored.get("task_id") or "").strip()
            if not task_id:
                continue
            try:
                playback = self._load_persisted_replay(task_id)
                if playback and playback.get("available"):
                    environment = playback.get("environment")
                    frames = list(playback.get("frames") or [])
                    metrics = dict(playback.get("metrics") or {})
                    meta = dict(playback.get("meta") or {})
                else:
                    rebuilt = self._build_playback(
                        source=str(stored.get("source") or "sample"),
                        template=str(stored.get("template") or "warehouse"),
                        params=dict(stored.get("params") or {}),
                    )
                    environment = rebuilt.get("environment")
                    frames = list(rebuilt.get("frames") or [])
                    metrics = dict(rebuilt.get("metrics") or {})
                    meta = dict(rebuilt.get("meta") or {})
                    self._persist_replay_payload(
                        self._build_replay_response(
                            task_id=task_id,
                            task=stored,
                            environment=environment,
                            frames=frames,
                            metrics=metrics,
                            meta=meta,
                        )
                    )
            except Exception:
                continue

            live_status = str(stored.get("status") or "READY").upper()
            if live_status == "PREPARING":
                live_status = "READY"
            elif live_status == "RUNNING":
                live_status = "PAUSED"

            live = LiveTask(
                task_id=task_id,
                mission_name=str(stored.get("mission_name") or "restored_task"),
                template=str(stored.get("template") or "warehouse"),
                source=str(stored.get("source") or "sample"),
                params=dict(stored.get("params") or {}),
                status=live_status,
                created_at=float(stored.get("created_at") or now_ts()),
                updated_at=float(stored.get("updated_at") or now_ts()),
                started_at=float(stored["started_at"]) if stored.get("started_at") is not None else None,
                ended_at=float(stored["ended_at"]) if stored.get("ended_at") is not None else None,
                error=stored.get("error"),
                tick_ms=int(stored.get("tick_ms") or DEFAULT_TASK_TICK_MS),
            )
            live.environment = environment
            live.frames = frames
            live.base_metrics = metrics
            live.warnings = list(meta.get("warnings") or [])

            if live.frames:
                max_index = max(0, len(live.frames) - 1)
                stored_index = int(stored.get("current_frame_index") or 0)
                live.frame_index = max(0, min(stored_index, max_index))
                live.runtime_metrics = dict(stored.get("metrics") or {}) or self._calculate_runtime_metrics(
                    live,
                    live.frames[live.frame_index],
                )
            else:
                live.frame_index = 0
                live.runtime_metrics = dict(stored.get("metrics") or {}) or self._blank_runtime_metrics(live)

            alerts = list(reversed(self.db.get_alerts(task_id, limit=120)))
            live.alerts = alerts
            live.alert_count = len(alerts)

            with self.tasks_lock:
                self.tasks[task_id] = live

            if live_status != str(stored.get("status") or "").upper():
                live.updated_at = now_ts()
                self._persist_runtime_state(live)

    def _replay_path(self, task_id: str) -> Path:
        return self.replay_dir / f"{task_id}.json"

    def _build_replay_response(
        self,
        task_id: str,
        task: Dict[str, Any],
        environment: Optional[Dict[str, Any]],
        frames: Optional[List[Dict[str, Any]]],
        metrics: Optional[Dict[str, Any]],
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized_frames = list(frames or [])
        return {
            "task_id": task_id,
            "available": bool(environment and normalized_frames),
            "task": task,
            "environment": environment,
            "frames": normalized_frames,
            "metrics": dict(metrics or {}),
            "meta": dict(meta or {}),
            "reason": "" if environment and normalized_frames else "历史回放帧为空",
        }

    def _persist_replay_payload(self, payload: Dict[str, Any]):
        task_id = str(payload.get("task_id") or "").strip()
        if not task_id:
            return
        path = self._replay_path(task_id)
        artifact = {
            "task_id": task_id,
            "environment": payload.get("environment"),
            "frames": payload.get("frames") or [],
            "metrics": payload.get("metrics") or {},
            "meta": payload.get("meta") or {},
            "saved_at": now_ts(),
        }
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(path)

    def _load_persisted_replay(self, task_id: str) -> Optional[Dict[str, Any]]:
        path = self._replay_path(task_id)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return self._build_replay_response(
            task_id=task_id,
            task={},
            environment=payload.get("environment"),
            frames=payload.get("frames"),
            metrics=payload.get("metrics"),
            meta=payload.get("meta"),
        )

    def _rebuild_historical_replay(self, stored: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        task_id = str(stored.get("task_id") or "").strip()
        if not task_id:
            return None
        try:
            playback = self._build_playback(
                source=str(stored.get("source") or "sample"),
                template=str(stored.get("template") or "warehouse"),
                params=dict(stored.get("params") or {}),
            )
        except Exception as exc:
            return {
                "task_id": task_id,
                "available": False,
                "reason": f"历史任务回放重建失败：{exc}",
                "task": stored,
            }

        payload = self._build_replay_response(
            task_id=task_id,
            task=stored,
            environment=playback.get("environment"),
            frames=playback.get("frames"),
            metrics=playback.get("metrics"),
            meta=playback.get("meta"),
        )
        self._persist_replay_payload(payload)
        return payload


class TaskDB:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    mission_name TEXT NOT NULL,
                    template TEXT NOT NULL,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    metrics_json TEXT,
                    error TEXT,
                    tick_ms INTEGER NOT NULL,
                    total_frames INTEGER NOT NULL DEFAULT 0,
                    current_frame_index INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    ended_at REAL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS task_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    ts REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_task_events_task_seq ON task_events(task_id, seq);
                CREATE TABLE IF NOT EXISTS task_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    ts REAL NOT NULL,
                    level TEXT NOT NULL,
                    code TEXT NOT NULL,
                    message TEXT NOT NULL,
                    frame_step INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_task_alerts_task_ts ON task_alerts(task_id, ts DESC);
                CREATE TABLE IF NOT EXISTS user_accounts (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    department TEXT NOT NULL,
                    title TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    last_login_at REAL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_credentials (
                    user_id TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS task_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    user_id TEXT,
                    username TEXT,
                    display_name TEXT,
                    role TEXT,
                    category TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_task_feedback_task_created ON task_feedback(task_id, created_at DESC);
                """
            )
            self._seed_default_users(conn)

    def _seed_default_users(self, conn: sqlite3.Connection):
        now = now_ts()
        default_ids = set()
        for account in DEFAULT_USER_ACCOUNTS:
            user_id = str(account["user_id"])
            username = normalize_username(account["username"])
            default_ids.add(user_id)
            conn.execute(
                """
                INSERT INTO user_accounts(
                    user_id, username, display_name, role, department, title, status, last_login_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'active', NULL, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    display_name = excluded.display_name,
                    role = excluded.role,
                    department = excluded.department,
                    title = excluded.title,
                    status = 'active',
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    username,
                    account["display_name"],
                    account["role"],
                    account["department"],
                    account.get("title") or "",
                    now,
                    now,
                ),
            )
            conn.execute(
                """
                INSERT INTO auth_credentials(user_id, password_hash, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    password_hash = excluded.password_hash,
                    updated_at = excluded.updated_at
                """,
                (user_id, hash_password(str(account.get("password") or "")), now),
            )

        # Legacy demo account cleanup: keep only default active accounts.
        if default_ids:
            placeholders = ",".join("?" for _ in default_ids)
            conn.execute(
                f"UPDATE user_accounts SET status = 'inactive', updated_at = ? WHERE user_id NOT IN ({placeholders})",
                (now, *sorted(default_ids)),
            )

        self._ensure_app_state(conn, "auth_logged_in", "0", now)

        active_row = conn.execute("SELECT value FROM app_state WHERE key = 'active_user_id'").fetchone()
        if active_row is None:
            candidate = DEFAULT_ACTIVE_USER_ID
            candidate_row = conn.execute("SELECT user_id FROM user_accounts WHERE user_id = ?", (candidate,)).fetchone()
            if candidate_row is None:
                fallback_row = conn.execute("SELECT user_id, role FROM user_accounts ORDER BY created_at ASC").fetchall()
                if fallback_row:
                    ranked = sorted(
                        fallback_row,
                        key=lambda row: (
                            ROLE_PRIORITY.get(normalize_role(row["role"]), 99),
                            str(row["user_id"]),
                        ),
                    )
                    candidate = str(ranked[0]["user_id"])
            conn.execute(
                """
                INSERT OR REPLACE INTO app_state(key, value, updated_at)
                VALUES ('active_user_id', ?, ?)
                """,
                (candidate, now),
            )
        conn.commit()

    def _ensure_app_state(self, conn: sqlite3.Connection, key: str, value: str, ts: float):
        existing = conn.execute("SELECT key FROM app_state WHERE key = ?", (key,)).fetchone()
        if existing is None:
            conn.execute(
                "INSERT OR REPLACE INTO app_state(key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, ts),
            )

    def get_auth_options(self) -> Dict[str, Any]:
        with self._connect() as conn:
            users = self._load_users(conn)
        accounts = []
        for user in users:
            accounts.append(
                {
                    "user_id": user["user_id"],
                    "username": user["username"],
                    "display_name": user["display_name"],
                    "role": user["role"],
                    "department": user["department"],
                    "title": user["title"],
                }
            )
        return {"accounts": accounts}

    def get_auth_state(self) -> Dict[str, Any]:
        with self._connect() as conn:
            users = self._load_users(conn)
            active_user_id = self._load_active_user_id(conn)
            logged_in = self._load_auth_logged_in(conn)
        current = self._pick_current_user(users, active_user_id) if logged_in else None
        return {"logged_in": bool(logged_in), "current_user": current}

    def login(self, role: str, username: str, password: str) -> Optional[Dict[str, Any]]:
        role = normalize_role(role)
        username = normalize_username(username)
        password_hash = hash_password(password)
        now = now_ts()

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT u.user_id, u.role, c.password_hash
                FROM user_accounts u
                LEFT JOIN auth_credentials c ON c.user_id = u.user_id
                WHERE u.status = 'active' AND lower(u.username) = ?
                LIMIT 1
                """,
                (username,),
            ).fetchone()
            if row is None:
                return None

            actual_role = normalize_role(row["role"])
            stored_hash = str(row["password_hash"] or "")
            if actual_role != role or not stored_hash or not hmac.compare_digest(stored_hash, password_hash):
                return None

            user_id = str(row["user_id"])
            conn.execute(
                "UPDATE user_accounts SET last_login_at = ?, updated_at = ? WHERE user_id = ?",
                (now, now, user_id),
            )
            conn.execute(
                "INSERT OR REPLACE INTO app_state(key, value, updated_at) VALUES ('active_user_id', ?, ?)",
                (user_id, now),
            )
            conn.execute(
                "INSERT OR REPLACE INTO app_state(key, value, updated_at) VALUES ('auth_logged_in', '1', ?)",
                (now,),
            )
            conn.commit()

            users = self._load_users(conn)
            current = self._pick_current_user(users, user_id)
            return {"logged_in": True, "current_user": current}

    def logout(self) -> Dict[str, Any]:
        now = now_ts()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_state(key, value, updated_at) VALUES ('auth_logged_in', '0', ?)",
                (now,),
            )
            conn.commit()
        return {"logged_in": False, "current_user": None}

    def get_identity(self) -> Dict[str, Any]:
        with self._connect() as conn:
            users = self._load_users(conn)
            active_user_id = self._load_active_user_id(conn)
        current = self._pick_current_user(users, active_user_id)
        return {"current_user": current, "users": users}

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        state = self.get_auth_state()
        return state.get("current_user")

    def switch_identity(self, user_id: str) -> Optional[Dict[str, Any]]:
        now = now_ts()
        with self._connect() as conn:
            row = conn.execute("SELECT user_id FROM user_accounts WHERE user_id = ?", (user_id,)).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE user_accounts SET last_login_at = ?, updated_at = ? WHERE user_id = ?",
                (now, now, user_id),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO app_state(key, value, updated_at)
                VALUES ('active_user_id', ?, ?)
                """,
                (user_id, now),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO app_state(key, value, updated_at)
                VALUES ('auth_logged_in', '1', ?)
                """,
                (now,),
            )
            conn.commit()
            users = self._load_users(conn)
        current = self._pick_current_user(users, user_id)
        return {"current_user": current, "users": users}

    def _load_users(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT user_id, username, display_name, role, department, title, status, last_login_at, created_at, updated_at
            FROM user_accounts
            WHERE status = 'active'
            ORDER BY updated_at DESC, created_at ASC
            """
        ).fetchall()
        users = [self._parse_user_row(row) for row in rows]
        return sorted(users, key=lambda user: (ROLE_PRIORITY.get(user["role"], 99), -float(user["updated_at"])))

    def _load_active_user_id(self, conn: sqlite3.Connection) -> Optional[str]:
        row = conn.execute("SELECT value FROM app_state WHERE key = 'active_user_id'").fetchone()
        if row is None:
            return None
        return str(row["value"])

    def _load_auth_logged_in(self, conn: sqlite3.Connection) -> bool:
        row = conn.execute("SELECT value FROM app_state WHERE key = 'auth_logged_in'").fetchone()
        if row is None:
            return False
        return str(row["value"]) == "1"

    def _pick_current_user(self, users: List[Dict[str, Any]], active_user_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not users:
            return None
        if active_user_id:
            for user in users:
                if user["user_id"] == active_user_id:
                    return user
        return users[0]

    def insert_task(
        self,
        task_id: str,
        mission_name: str,
        template: str,
        source: str,
        status: str,
        params: Dict[str, Any],
        created_at: float,
        updated_at: float,
        tick_ms: int,
    ):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks(task_id, mission_name, template, source, status, params_json, created_at, updated_at, tick_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    mission_name,
                    template,
                    source,
                    status,
                    json.dumps(params, ensure_ascii=False),
                    created_at,
                    updated_at,
                    tick_ms,
                ),
            )
            conn.commit()

    def update_task_definition(
        self,
        task_id: str,
        mission_name: str,
        template: str,
        source: str,
        status: str,
        params: Dict[str, Any],
        tick_ms: int,
        updated_at: float,
    ) -> Dict[str, Any]:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET mission_name = ?,
                    template = ?,
                    source = ?,
                    status = ?,
                    params_json = ?,
                    tick_ms = ?,
                    updated_at = ?,
                    metrics_json = COALESCE(metrics_json, '{}'),
                    error = NULL
                WHERE task_id = ?
                """,
                (
                    mission_name,
                    template,
                    source,
                    status,
                    json.dumps(params, ensure_ascii=False),
                    tick_ms,
                    updated_at,
                    task_id,
                ),
            )
            conn.commit()
        updated = self.get_task(task_id)
        if updated is None:
            raise KeyError(task_id)
        return updated

    def update_task_runtime(
        self,
        task_id: str,
        status: str,
        updated_at: float,
        started_at: Optional[float],
        ended_at: Optional[float],
        current_frame_index: int,
        total_frames: int,
        metrics: Dict[str, Any],
        error: Optional[str],
    ):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?,
                    updated_at = ?,
                    started_at = ?,
                    ended_at = ?,
                    current_frame_index = ?,
                    total_frames = ?,
                    metrics_json = ?,
                    error = ?
                WHERE task_id = ?
                """,
                (
                    status,
                    updated_at,
                    started_at,
                    ended_at,
                    current_frame_index,
                    total_frames,
                    json.dumps(metrics or {}, ensure_ascii=False),
                    error,
                    task_id,
                ),
            )
            conn.commit()

    def insert_event(self, task_id: str, event: Dict[str, Any]):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO task_events(task_id, seq, ts, event_type, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    int(event["seq"]),
                    float(event["ts"]),
                    str(event["type"]),
                    json.dumps(event.get("payload") or {}, ensure_ascii=False),
                ),
            )
            conn.commit()

    def insert_alert(self, task_id: str, alert: Dict[str, Any]):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO task_alerts(task_id, ts, level, code, message, frame_step)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    float(alert.get("ts", now_ts())),
                    str(alert.get("level", "info")),
                    str(alert.get("code", "UNKNOWN")),
                    str(alert.get("message", "")),
                    int(alert.get("frame_step", 0)),
                ),
            )
            conn.commit()

    def insert_feedback(self, task_id: str, feedback: Dict[str, Any]):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO task_feedback(task_id, user_id, username, display_name, role, category, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    str(feedback.get("user_id") or ""),
                    str(feedback.get("username") or ""),
                    str(feedback.get("display_name") or ""),
                    str(feedback.get("role") or ""),
                    str(feedback.get("category") or "issue"),
                    str(feedback.get("message") or ""),
                    float(feedback.get("created_at") or now_ts()),
                ),
            )
            conn.commit()

    def list_tasks(self, limit: int = 30) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM tasks
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._parse_task_row(row) for row in rows]

    def list_restorable_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM tasks
                WHERE status IN ('PREPARING', 'READY', 'RUNNING', 'PAUSED')
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._parse_task_row(row) for row in rows]

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        return self._parse_task_row(row)

    def get_alerts(self, task_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT ts, level, code, message, frame_step
                FROM task_alerts
                WHERE task_id = ?
                ORDER BY ts DESC
                LIMIT ?
                """,
                (task_id, limit),
            ).fetchall()
        return [
            {
                "ts": float(row["ts"]),
                "level": str(row["level"]),
                "code": str(row["code"]),
                "message": str(row["message"]),
                "frame_step": int(row["frame_step"]),
            }
            for row in rows
        ]

    def get_feedback(self, task_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT user_id, username, display_name, role, category, message, created_at
                FROM task_feedback
                WHERE task_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (task_id, limit),
            ).fetchall()
        return [
            {
                "user_id": str(row["user_id"] or ""),
                "username": str(row["username"] or ""),
                "display_name": str(row["display_name"] or ""),
                "role": str(row["role"] or ""),
                "category": str(row["category"] or "issue"),
                "message": str(row["message"] or ""),
                "created_at": float(row["created_at"]),
            }
            for row in rows
        ]

    def _parse_task_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "task_id": str(row["task_id"]),
            "mission_name": str(row["mission_name"]),
            "template": str(row["template"]),
            "source": str(row["source"]),
            "status": str(row["status"]),
            "tick_ms": int(row["tick_ms"]),
            "params": json.loads(row["params_json"] or "{}"),
            "metrics": json.loads(row["metrics_json"] or "{}"),
            "error": row["error"],
            "total_frames": int(row["total_frames"]),
            "current_frame_index": int(row["current_frame_index"]),
            "created_at": float(row["created_at"]),
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "updated_at": float(row["updated_at"]),
        }

    def _parse_user_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        normalized_role = normalize_role(row["role"])
        return {
            "user_id": str(row["user_id"]),
            "username": str(row["username"]),
            "display_name": str(row["display_name"]),
            "role": normalized_role,
            "department": str(row["department"]),
            "title": str(row["title"] or ""),
            "status": str(row["status"]),
            "last_login_at": float(row["last_login_at"]) if row["last_login_at"] is not None else None,
            "created_at": float(row["created_at"]),
            "updated_at": float(row["updated_at"]),
        }


def normalize_task_payload(payload: Dict[str, Any], template: str) -> Dict[str, Any]:
    defaults = {
        "cfg_dir": "results/train_dir/0001/exp",
        "checkpoint_path": "results/train_dir/0001/exp/checkpoint_p0/best/best_model_obj_+0000000.000000_step_000921600_1772213120.pth",
        "device": "cpu",
        "render": False,
        "save_svg": "results/mac_eval/web-task.svg",
        "max_frames": 64,
        "fps": 0,
        "seed": 7,
        "map_name": TEMPLATE_CONFIGS[template]["map_name"],
        "num_agents": 4,
        "max_episode_steps": 64,
        "policy_index": 0,
    }
    merged = dict(defaults)
    merged.update(payload or {})
    merged["render"] = bool(merged.get("render", False))
    merged["num_agents"] = clamp_int(merged.get("num_agents"), 4, 1, 128)
    merged["max_frames"] = clamp_int(merged.get("max_frames"), 64, 4, 1024)
    merged["max_episode_steps"] = clamp_int(merged.get("max_episode_steps"), 64, 8, 2048)
    merged["device"] = "gpu" if str(merged.get("device", "cpu")).lower() == "gpu" else "cpu"
    merged["continuous_patrol"] = bool(merged.get("continuous_patrol", False))
    merged["tick_ms"] = clamp_int(merged.get("tick_ms"), DEFAULT_TASK_TICK_MS, 120, 2400)
    try:
        merged["scheduled_start_at"] = float(merged["scheduled_start_at"]) if merged.get("scheduled_start_at") else None
    except (TypeError, ValueError):
        merged["scheduled_start_at"] = None
    merged["scheduled_start_label"] = str(merged.get("scheduled_start_label") or "")
    return merged


def build_sample_rollout(template: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if bool(payload.get("continuous_patrol")) and template == "campus":
        return build_continuous_patrol_rollout(template, payload)

    config = TEMPLATE_CONFIGS.get(template, TEMPLATE_CONFIGS["warehouse"])
    height, width = 12, 12
    obstacles = build_template_obstacles(template, height, width)
    environment = {"width": width, "height": height, "obstacles": obstacles}

    requested_agents = clamp_int(payload.get("num_agents"), 4, 1, 64)
    starts = expand_starts(config["starts"], requested_agents, height, width)
    plans = []
    for idx, (sx, sy, tx, ty) in enumerate(starts):
        path = find_path_a_star(obstacles, (sx, sy), (tx, ty))
        if not path:
            path = [(sx, sy)]
        plans.append(
            {
                "id": idx,
                "start_x": sx,
                "start_y": sy,
                "target_x": tx,
                "target_y": ty,
                "path": path,
                "reachable": len(path) > 1 or (sx == tx and sy == ty),
            }
        )

    max_frames = clamp_int(payload.get("max_frames"), 64, 4, 1024)
    natural_max = max((len(plan["path"]) - 1 for plan in plans), default=0)
    max_step = min(natural_max, max_frames)

    frames = []
    tasks_completed = 0
    for step in range(0, max_step + 1):
        agents = []
        completed_this_step = 0
        for plan in plans:
            cursor = min(step, len(plan["path"]) - 1)
            x, y = plan["path"][cursor]
            done = plan["reachable"] and cursor == len(plan["path"]) - 1
            if done and step == cursor:
                completed_this_step += 1
            agents.append(
                {
                    "id": int(plan["id"]),
                    "x": int(x),
                    "y": int(y),
                    "target_x": int(plan["target_x"]),
                    "target_y": int(plan["target_y"]),
                    "reward": float(1.0 if done else 0.0),
                    "done": bool(done),
                }
            )
        tasks_completed += completed_this_step
        frames.append(
            {
                "step": int(step),
                "vertex_conflicts": int(count_vertex_conflicts(agents)),
                "completed_this_step": int(completed_this_step),
                "tasks_completed": int(tasks_completed),
                "agents": agents,
            }
        )

    total_steps = max(1, len(frames) - 1)
    total_conflicts = sum(frame["vertex_conflicts"] for frame in frames)
    metrics = {
        "mean_reward": round(1.0 if tasks_completed else 0.0, 4),
        "tasks_completed": int(tasks_completed),
        "throughput": round(tasks_completed / total_steps, 4),
        "total_steps": int(total_steps),
        "vertex_conflicts": int(total_conflicts),
    }

    return {
        "meta": {
            "actual_device": "sample",
            "checkpoint_path": "sample/demo",
            "cfg_dir": "sample",
            "frames": len(frames),
            "map_name": str(config["map_name"]),
            "num_agents": len(starts),
            "save_svg": None,
            "warnings": [f"backend sample mode: {template}"],
        },
        "environment": environment,
        "frames": frames,
        "metrics": metrics,
    }


def build_continuous_patrol_rollout(template: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    config = TEMPLATE_CONFIGS.get(template, TEMPLATE_CONFIGS["campus"])
    height, width = 12, 12
    obstacles = build_template_obstacles(template, height, width)
    environment = {"width": width, "height": height, "obstacles": obstacles}

    route = [(1, 1), (1, 10), (6, 10), (10, 10), (10, 3), (6, 1)]
    requested_agents = clamp_int(payload.get("num_agents"), 4, 1, 16)
    plans = []

    for idx in range(requested_agents):
        offset = idx % len(route)
        rotated = route[offset:] + route[:offset]
        points = rotated + [rotated[0]]
        full_path: List[Tuple[int, int]] = []
        targets: List[Tuple[int, int]] = []
        completed_marks: List[int] = []
        cumulative = 0
        for segment_index in range(len(points) - 1):
            start = points[segment_index]
            target = points[segment_index + 1]
            segment = find_path_a_star(obstacles, start, target) or [start]
            for point_index, point in enumerate(segment):
                if full_path and point_index == 0:
                    continue
                full_path.append(point)
                targets.append(target)
                reached = int(point == target)
                cumulative += reached
                completed_marks.append(cumulative)
        plans.append(
            {
                "id": idx,
                "path": full_path or [points[0]],
                "targets": targets or [points[1]],
                "completed_marks": completed_marks or [0],
            }
        )

    max_step = max((len(plan["path"]) - 1 for plan in plans), default=0)
    frames = []
    for step in range(0, max_step + 1):
        agents = []
        tasks_completed = 0
        completed_this_step = 0
        for plan in plans:
            cursor = min(step, len(plan["path"]) - 1)
            x, y = plan["path"][cursor]
            target_x, target_y = plan["targets"][cursor]
            cumulative = int(plan["completed_marks"][cursor])
            previous = int(plan["completed_marks"][cursor - 1]) if cursor > 0 else 0
            reached = max(0, cumulative - previous)
            completed_this_step += reached
            tasks_completed += cumulative
            agents.append(
                {
                    "id": int(plan["id"]),
                    "x": int(x),
                    "y": int(y),
                    "target_x": int(target_x),
                    "target_y": int(target_y),
                    "reward": float(0.3 if reached else 0.02),
                    "done": False,
                }
            )
        frames.append(
            {
                "step": int(step),
                "vertex_conflicts": int(count_vertex_conflicts(agents)),
                "completed_this_step": int(completed_this_step),
                "tasks_completed": int(tasks_completed),
                "agents": agents,
            }
        )

    total_steps = max(1, len(frames) - 1)
    total_conflicts = sum(frame["vertex_conflicts"] for frame in frames)
    metrics = {
        "mean_reward": 0.28,
        "tasks_completed": int(frames[-1]["tasks_completed"] if frames else 0),
        "throughput": round((frames[-1]["tasks_completed"] if frames else 0) / total_steps, 4),
        "total_steps": int(total_steps),
        "vertex_conflicts": int(total_conflicts),
    }

    return {
        "meta": {
            "actual_device": "sample",
            "checkpoint_path": "sample/continuous-campus-patrol",
            "cfg_dir": "sample",
            "frames": len(frames),
            "map_name": str(payload.get("map_name") or config["map_name"]),
            "num_agents": requested_agents,
            "save_svg": None,
            "warnings": ["backend sample mode: continuous campus patrol"],
        },
        "environment": environment,
        "frames": frames,
        "metrics": metrics,
    }


def expand_starts(base_starts: List[Tuple[int, int, int, int]], num_agents: int, height: int, width: int) -> List[Tuple[int, int, int, int]]:
    starts = []
    offset = 0
    while len(starts) < num_agents:
        sx, sy, tx, ty = base_starts[len(starts) % len(base_starts)]
        shift = offset // len(base_starts)
        nx = max(1, min(height - 2, sx + (shift % 3) - 1))
        ny = max(1, min(width - 2, sy + ((shift + 1) % 3) - 1))
        gx = max(1, min(height - 2, tx - (shift % 2)))
        gy = max(1, min(width - 2, ty - ((shift + 1) % 2)))
        starts.append((nx, ny, gx, gy))
        offset += 1
    return starts


def build_template_obstacles(template: str, height: int, width: int) -> List[List[int]]:
    if template == "campus":
        return build_campus_obstacles(height, width)
    if template == "emergency":
        return build_emergency_obstacles(height, width)
    return build_warehouse_obstacles(height, width)


def build_warehouse_obstacles(height: int, width: int) -> List[List[int]]:
    obstacles = [[0 for _ in range(width)] for _ in range(height)]
    for col in range(2, width - 2):
        if col not in (5, 8):
            obstacles[3][col] = 1
        if col not in (3, 9):
            obstacles[6][col] = 1
        if col not in (4, 7):
            obstacles[9][col] = 1
    for row in range(1, height - 1):
        if row not in (4, 8):
            obstacles[row][5] = 1
        if row not in (2, 7):
            obstacles[row][8] = 1
    return obstacles


def build_campus_obstacles(height: int, width: int) -> List[List[int]]:
    obstacles = [[0 for _ in range(width)] for _ in range(height)]
    for row in range(2, height - 2):
        for col in range(2, width - 2):
            if 4 <= row <= 7 and 4 <= col <= 7:
                obstacles[row][col] = 1
    for row in range(1, height - 1):
        if row != 5:
            obstacles[row][2] = 1
            obstacles[row][9] = 1
    for col in range(1, width - 1):
        if col != 6:
            obstacles[2][col] = 1
            obstacles[9][col] = 1
    for col in range(width):
        obstacles[5][col] = 0
    for row in range(height):
        obstacles[row][6] = 0
    return obstacles


def build_emergency_obstacles(height: int, width: int) -> List[List[int]]:
    obstacles = [[0 for _ in range(width)] for _ in range(height)]
    mid_w = width // 2
    mid_h = height // 2
    for row in range(2, height - 2):
        obstacles[row][mid_w] = 1
    for col in range(2, width - 2):
        obstacles[mid_h][col] = 1
    for i in range(2, height - 2):
        if i not in (4, 7):
            obstacles[i][i] = 1
            mirror_col = width - 1 - i
            obstacles[i][mirror_col] = 1

    obstacles[4][mid_w] = 0
    obstacles[7][mid_w] = 0
    obstacles[mid_h][4] = 0
    obstacles[mid_h][7] = 0
    return obstacles


def find_path_a_star(obstacles: List[List[int]], start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
    sx, sy = start
    gx, gy = goal
    if not is_walkable(obstacles, sx, sy) or not is_walkable(obstacles, gx, gy):
        return None
    if (sx, sy) == (gx, gy):
        return [(sx, sy)]

    open_nodes = [{"x": sx, "y": sy, "g": 0, "f": manhattan(sx, sy, gx, gy)}]
    parents: Dict[str, Optional[str]] = {}
    g_score: Dict[str, int] = {to_key(sx, sy): 0}
    closed = set()

    while open_nodes:
        open_nodes.sort(key=lambda node: (node["f"], node["g"]))
        current = open_nodes.pop(0)
        current_key = to_key(current["x"], current["y"])
        if current_key in closed:
            continue
        if (current["x"], current["y"]) == (gx, gy):
            return rebuild_path(parents, current_key)
        closed.add(current_key)

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = current["x"] + dx, current["y"] + dy
            if not is_walkable(obstacles, nx, ny):
                continue
            n_key = to_key(nx, ny)
            if n_key in closed:
                continue
            tentative_g = current["g"] + 1
            if tentative_g >= g_score.get(n_key, 10**9):
                continue
            g_score[n_key] = tentative_g
            parents[n_key] = current_key
            open_nodes.append(
                {
                    "x": nx,
                    "y": ny,
                    "g": tentative_g,
                    "f": tentative_g + manhattan(nx, ny, gx, gy),
                }
            )

    return None


def rebuild_path(parents: Dict[str, str], end_key: str) -> List[Tuple[int, int]]:
    chain = []
    cursor = end_key
    while cursor:
        x, y = from_key(cursor)
        chain.append((x, y))
        cursor = parents.get(cursor)  # type: ignore[assignment]
    chain.reverse()
    return chain


def count_vertex_conflicts(agents: List[Dict[str, Any]]) -> int:
    occupied: Dict[str, int] = {}
    for agent in agents:
        key = to_key(int(agent["x"]), int(agent["y"]))
        occupied[key] = occupied.get(key, 0) + 1
    conflicts = 0
    for count in occupied.values():
        if count > 1:
            conflicts += count - 1
    return conflicts


def is_walkable(obstacles: List[List[int]], x: int, y: int) -> bool:
    if x < 0 or y < 0:
        return False
    if x >= len(obstacles) or y >= len(obstacles[0]):
        return False
    return obstacles[x][y] == 0


def manhattan(x1: int, y1: int, x2: int, y2: int) -> int:
    return abs(x1 - x2) + abs(y1 - y2)


def to_key(x: int, y: int) -> str:
    return f"{x},{y}"


def from_key(key: str) -> Tuple[int, int]:
    x, y = key.split(",")
    return int(x), int(y)
