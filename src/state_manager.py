import json
import os
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "workflow_state.json")


def _load_state() -> Dict[str, Any]:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_state(state: Dict[str, Any]):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def create_workflow(workflow_id: str, workflow_name: str = "generate_interview_report") -> Dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state = _load_state()
    state[workflow_id] = {
        "workflow_name": workflow_name,
        "step": 0,
        "step_name": "",
        "status": "pending",
        "data": {},
        "error": None,
        "retry_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    _save_state(state)
    return state[workflow_id]


def update_workflow_status(
    workflow_id: str,
    step: int,
    step_name: str,
    status: str,
    data: Optional[Dict[str, Any]] = None,
    error: Optional[Dict[str, Any]] = None,
    retry_count: int = 0,
):
    state = _load_state()
    if workflow_id not in state:
        raise ValueError(f"Workflow {workflow_id} not found")

    workflow = state[workflow_id]
    workflow["step"] = step
    workflow["step_name"] = step_name
    workflow["status"] = status
    workflow["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if data is not None:
        workflow["data"].update(data)

    if error is not None:
        workflow["error"] = error

    if retry_count > 0:
        workflow["retry_count"] = retry_count

    _save_state(state)


def get_workflow(workflow_id: str) -> Optional[Dict[str, Any]]:
    state = _load_state()
    return state.get(workflow_id)


def get_workflow_step_data(workflow_id: str, step: int) -> Optional[Dict[str, Any]]:
    workflow = get_workflow(workflow_id)
    if workflow and workflow["step"] >= step:
        return workflow["data"]
    return None


def is_workflow_stale(workflow_id: str, timeout_minutes: int = 30) -> bool:
    workflow = get_workflow(workflow_id)
    if not workflow or workflow["status"] != "running":
        return False

    updated_at = datetime.fromisoformat(workflow["updated_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return (now - updated_at).total_seconds() > timeout_minutes * 60


def cleanup_completed_workflow(workflow_id: str, retention_hours: int = 24):
    workflow = get_workflow(workflow_id)
    if not workflow or workflow["status"] != "completed":
        return

    updated_at = datetime.fromisoformat(workflow["updated_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    if (now - updated_at).total_seconds() > retention_hours * 3600:
        state = _load_state()
        del state[workflow_id]
        _save_state(state)
