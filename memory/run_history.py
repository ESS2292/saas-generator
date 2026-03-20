import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4


RUN_HISTORY_FILE = Path("memory/run_history.json")
_RUN_LOCK = Lock()


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _load_runs_unlocked():
    if not RUN_HISTORY_FILE.exists():
        return []
    try:
        return json.loads(RUN_HISTORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save_runs_unlocked(runs):
    RUN_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    RUN_HISTORY_FILE.write_text(json.dumps(runs, indent=2) + "\n", encoding="utf-8")


def list_runs():
    with _RUN_LOCK:
        return _load_runs_unlocked()


def get_run(run_id):
    with _RUN_LOCK:
        for run in _load_runs_unlocked():
            if run.get("id") == run_id:
                return run
    return None


def create_run(prompt, app_root, run_verification=True, auto_deploy=False):
    with _RUN_LOCK:
        runs = _load_runs_unlocked()
        run = {
            "id": uuid4().hex,
            "prompt": prompt,
            "app_root": app_root,
            "run_verification": run_verification,
            "auto_deploy": auto_deploy,
            "status": "queued",
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
            "result": None,
            "error": "",
        }
        runs.insert(0, run)
        _save_runs_unlocked(runs)
        return run


def update_run(run_id, **updates):
    with _RUN_LOCK:
        runs = _load_runs_unlocked()
        for index, run in enumerate(runs):
            if run.get("id") == run_id:
                updated = {**run, **updates, "updated_at": _utc_now()}
                runs[index] = updated
                _save_runs_unlocked(runs)
                return updated
    return None
