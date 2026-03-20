from pathlib import Path
from threading import Event
import uuid

from control_panel.lifecycle import transition_status
from control_panel.models import RunArtifact, RunResultSummary
from engine.pipeline import generate_saas_app
from memory.control_panel_store import (
    append_run_log,
    claim_next_job,
    get_run_by_id,
    list_run_logs,
    recover_stale_jobs,
    record_worker_heartbeat,
    replace_run_artifacts,
    update_job,
    update_run,
)


WORKER_POLL_SECONDS = 1.0
MAX_JOB_ATTEMPTS = 3
WORKER_HEARTBEAT_TIMEOUT_SECONDS = 90
JOB_LEASE_TIMEOUT_SECONDS = 180


def build_worker_id(prefix="control-panel-worker"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def result_summary(result):
    # Persist a compact, dashboard-friendly summary instead of the entire pipeline result.
    if not result:
        return {}
    intake = result.get("intake_context") or {}
    spec = result.get("spec_brief") or {}
    manifest = result.get("manifest") or {}
    return RunResultSummary(
        success=bool(result.get("success")),
        app_root=result.get("app_root"),
        tests_passed=bool(result.get("tests_passed")),
        deployed=bool(result.get("deployed")),
        latest_error=result.get("latest_error", ""),
        saved_files_count=result.get("saved_files_count", 0),
        app_name=manifest.get("app_name", "Generated App"),
        closest_family=intake.get("closest_family", ""),
        support_tier=intake.get("support_tier", ""),
        primary_users=spec.get("primary_users", []),
        core_entities=spec.get("core_entities", []),
        core_workflows=spec.get("core_workflows", []),
    ).model_dump()


def artifact_summary(app_root):
    # These are the main user-facing outputs we want to expose in the control panel.
    root = Path(app_root)
    candidates = [
        ("manifest", "Manifest", root / "manifest.json"),
        ("deploy", "Deploy Folder", root / "deploy"),
        ("backend", "Backend App", root / "backend" / "main.py"),
        ("frontend", "Frontend App", root / "frontend" / "src" / "App.jsx"),
    ]
    return [
        RunArtifact(artifact_type=artifact_type, label=label, path=str(path)).model_dump()
        for artifact_type, label, path in candidates
        if path.exists()
    ]


def count_run_attempts(run_id):
    logs = list_run_logs(get_run_by_id(run_id)["user_id"], run_id, limit=500) or []
    return sum(1 for entry in logs if entry["message"] == "Worker claimed queued run.")


def _requeue_or_fail(run, worker_id, message):
    run_id = run["id"]
    attempts = count_run_attempts(run_id)
    if attempts < MAX_JOB_ATTEMPTS:
        append_run_log(run_id, "warning", f"{message} Retrying run ({attempts}/{MAX_JOB_ATTEMPTS - 1} retries used).")
        update_run(run_id, status="queued", error=message)
        update_job(run_id, status="queued", worker_id=None)
        return "queued"
    append_run_log(run_id, "error", message)
    failed_status = transition_status("running", "failed")
    update_run(run_id, status=failed_status, error=message, result={})
    update_job(run_id, status=failed_status, worker_id=worker_id)
    return failed_status


def process_job(job, worker_id):
    # A claimed job is converted into a tracked run lifecycle:
    # queued -> running -> completed/failed
    run = get_run_by_id(job["run_id"])
    if run is None:
        return
    run_id = run["id"]
    append_run_log(run_id, "info", "Worker claimed queued run.")
    running_status = transition_status(run["status"], "running")
    update_run(run_id, status=running_status, error="")
    update_job(run_id, running_status, worker_id=worker_id)
    append_run_log(run_id, "info", "Starting generator pipeline.")
    try:
        result = generate_saas_app(
            run["prompt"],
            app_root=run["app_root"],
            run_verification=run["run_verification"],
            auto_deploy=run["auto_deploy"],
        )
        summary = result_summary(result)
        replace_run_artifacts(run_id, artifact_summary(run["app_root"]))
        if result.get("success"):
            status = transition_status(running_status, "completed")
            append_run_log(run_id, "info", f"Pipeline finished with status={status}.")
            update_run(run_id, status=status, result=summary, error=result.get("latest_error", ""))
            update_job(run_id, status=status, worker_id=worker_id)
            return
        retry_state = _requeue_or_fail(run, worker_id, result.get("latest_error", "Generator pipeline returned an unsuccessful result."))
        append_run_log(run_id, "info", f"Pipeline finished with status={retry_state}.")
    except Exception as exc:  # pragma: no cover
        retry_state = _requeue_or_fail(run, worker_id, str(exc))
        append_run_log(run_id, "info", f"Pipeline finished with status={retry_state}.")


def worker_loop(stop_event, worker_id):
    # Keep polling the shared jobs table until the process is stopped.
    while not stop_event.is_set():
        record_worker_heartbeat(worker_id)
        recovered = recover_stale_jobs(
            worker_timeout_seconds=WORKER_HEARTBEAT_TIMEOUT_SECONDS,
            lease_timeout_seconds=JOB_LEASE_TIMEOUT_SECONDS,
        )
        for run_id in recovered:
            append_run_log(run_id, "warning", "Recovered stale job and returned it to the queue.")
        job = claim_next_job(worker_id)
        if job:
            process_job(job, worker_id)
            continue
        stop_event.wait(WORKER_POLL_SECONDS)


def run_worker_forever():
    stop_event = Event()
    worker_loop(stop_event, build_worker_id())
