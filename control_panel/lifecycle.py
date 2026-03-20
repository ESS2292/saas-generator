from enum import StrEnum

from control_panel.models import RunStage
from memory.control_panel_store import list_run_logs


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"


STATUS_LABELS = {
    RunStatus.QUEUED: "Getting ready",
    RunStatus.RUNNING: "Building now",
    RunStatus.DEPLOYING: "Publishing online",
    RunStatus.COMPLETED: "Finished",
    RunStatus.FAILED: "Needs attention",
}

STAGE_SEQUENCE = [
    ("queued", "Queued"),
    ("planning", "Planning"),
    ("generating", "Generating"),
    ("validating", "Validating"),
    ("repairing", "Repairing"),
    ("deploying", "Deploying"),
    ("completed", "Completed"),
]

STAGE_PROGRESS = {
    "queued": 8,
    "planning": 22,
    "generating": 40,
    "validating": 62,
    "repairing": 76,
    "deploying": 90,
    "completed": 100,
}

ALLOWED_TRANSITIONS = {
    RunStatus.QUEUED: {RunStatus.RUNNING, RunStatus.FAILED},
    RunStatus.RUNNING: {RunStatus.DEPLOYING, RunStatus.COMPLETED, RunStatus.FAILED},
    RunStatus.DEPLOYING: {RunStatus.COMPLETED, RunStatus.FAILED},
    RunStatus.COMPLETED: {RunStatus.DEPLOYING},
    RunStatus.FAILED: set(),
}


def plain_status_label(status) -> str:
    normalized = str(status or "").lower()
    return STATUS_LABELS.get(RunStatus(normalized), "In progress") if normalized in RunStatus._value2member_map_ else "In progress"


def run_stage_summary(run) -> list[RunStage]:
    logs = list_run_logs(run["user_id"], run["id"], limit=100) or []
    messages = " ".join(entry["message"].lower() for entry in logs)
    current = "queued"
    if "starting generator pipeline" in messages:
        current = "planning"
    if run["status"] == RunStatus.RUNNING:
        current = "generating"
    if "verification" in messages:
        current = "validating"
    if "repair" in messages:
        current = "repairing"
    if run["status"] == RunStatus.DEPLOYING:
        current = "deploying"
    if run["status"] == RunStatus.COMPLETED:
        current = "completed"
    if run["status"] == RunStatus.FAILED and current == "queued":
        current = "generating"

    found = False
    rows: list[RunStage] = []
    for key, label in STAGE_SEQUENCE:
        if not found:
            state = "done" if key != current else "current"
        else:
            state = "pending"
        if key == current:
            found = True
        if run["status"] == RunStatus.FAILED and key == current:
            state = "failed"
        rows.append(RunStage(key=key, label=label, state=state))
    return rows


def current_stage_indicator(run) -> RunStage:
    stages = run_stage_summary(run)
    active = next((stage for stage in stages if stage.state in {"current", "failed"}), None)
    if active:
        return active
    if run.get("status") == RunStatus.COMPLETED:
        return RunStage(key="completed", label="Completed", state="done")
    return RunStage(key="queued", label="Queued", state="pending")


def stage_progress_percent(stage: RunStage | dict) -> int:
    if isinstance(stage, RunStage):
        return STAGE_PROGRESS.get(stage.key, 8)
    return STAGE_PROGRESS.get(stage.get("key"), 8)


def transition_status(current_status, next_status) -> str:
    current = RunStatus(str(current_status))
    target = RunStatus(str(next_status))
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"Invalid run status transition: {current.value} -> {target.value}")
    return target.value
