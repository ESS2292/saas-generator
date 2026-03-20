from datetime import datetime, timezone

from control_panel.lifecycle import current_stage_indicator
from memory.control_panel_store import get_job_for_run, list_jobs_by_status, list_recent_workers, list_run_logs


STAGE_MESSAGE_MARKERS = (
    ("queued", "Run queued."),
    ("running", "Worker claimed queued run."),
    ("planning", "Starting generator pipeline."),
    ("deploying", "Manual deploy requested from control panel."),
)


def _parse_timestamp(value):
    if not value:
        return None
    return datetime.fromisoformat(value)


def _seconds_between(start, end):
    if not start or not end:
        return None
    return max((end - start).total_seconds(), 0.0)


def _first_stage_timestamps(logs):
    # Reconstruct stage timing from durable run logs so observability works
    # even if the worker process that created the logs is gone.
    timestamps = {}
    for entry in logs:
        message = entry["message"]
        for stage, marker in STAGE_MESSAGE_MARKERS:
            if stage not in timestamps and marker in message:
                timestamps[stage] = entry["created_at"]
        if "Pipeline finished with status=completed." in message and "completed" not in timestamps:
            timestamps["completed"] = entry["created_at"]
        if "Pipeline finished with status=failed." in message and "failed" not in timestamps:
            timestamps["failed"] = entry["created_at"]
    return timestamps


def build_run_metrics(run):
    logs = list_run_logs(run["user_id"], run["id"], limit=500) or []
    current_stage = current_stage_indicator(run)
    first_stage_timestamps = _first_stage_timestamps(logs)
    created_at = _parse_timestamp(run.get("created_at"))
    updated_at = _parse_timestamp(run.get("updated_at"))
    stage_metrics = {}

    # Keep the stage order explicit so duration math remains predictable.
    ordered_stages = ["queued", "running", "planning", "deploying", "completed", "failed"]
    for index, stage in enumerate(ordered_stages):
        started_at = first_stage_timestamps.get(stage)
        if not started_at:
            continue
        next_started = None
        for next_stage in ordered_stages[index + 1 :]:
            if first_stage_timestamps.get(next_stage):
                next_started = first_stage_timestamps[next_stage]
                break
        stage_metrics[stage] = {
            "started_at": started_at,
            "duration_seconds": _seconds_between(_parse_timestamp(started_at), _parse_timestamp(next_started) if next_started else updated_at),
        }

    return {
        "run_id": run["id"],
        "status": run["status"],
        "current_stage": current_stage.model_dump(),
        "attempt_count": sum(1 for entry in logs if entry["message"] == "Worker claimed queued run."),
        "log_count": len(logs),
        "total_duration_seconds": _seconds_between(created_at, updated_at),
        "job": get_job_for_run(run["id"]),
        "stages": stage_metrics,
    }


def build_system_metrics():
    # This powers the control panel's operator view: queue pressure plus worker freshness.
    queued = list_jobs_by_status("queued")
    running = list_jobs_by_status("running")
    failed = list_jobs_by_status("failed")
    completed = list_jobs_by_status("completed")
    workers = list_recent_workers(limit=10)
    now = datetime.now(timezone.utc)

    worker_summaries = []
    for worker in workers:
        last_seen = _parse_timestamp(worker.get("last_seen_at"))
        worker_summaries.append(
            {
                **worker,
                "heartbeat_age_seconds": _seconds_between(last_seen, now),
            }
        )

    return {
        "job_counts": {
            "queued": len(queued),
            "running": len(running),
            "failed": len(failed),
            "completed": len(completed),
        },
        "workers": worker_summaries,
    }
