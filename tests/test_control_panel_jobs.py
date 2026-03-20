from datetime import datetime, timedelta, timezone
from pathlib import Path

from engine import control_panel_jobs
from memory import control_panel_store


def _isolate_control_panel_db(tmp_path, monkeypatch):
    monkeypatch.setattr(control_panel_store, "DB_PATH", tmp_path / "control_panel.db")
    control_panel_store.init_db()


def _create_user():
    return control_panel_store.register_user("worker@example.com", "secret123", "Worker User")


def test_process_job_requeues_before_final_failure(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    user = _create_user()
    run = control_panel_store.create_run(user["id"], "Build CRM", str(tmp_path / "generated_apps" / "crm"))
    job = control_panel_store.claim_next_job("retry-worker")

    monkeypatch.setattr(
        control_panel_jobs,
        "generate_saas_app",
        lambda *args, **kwargs: {
            "success": False,
            "latest_error": "Synthetic pipeline failure.",
            "app_root": kwargs.get("app_root") or args[1],
        },
    )

    control_panel_jobs.process_job(job, "retry-worker")
    first_retry = control_panel_store.get_run(user["id"], run["id"])
    first_job = control_panel_store.get_job_for_run(run["id"])
    assert first_retry["status"] == "queued"
    assert first_job["status"] == "queued"

    second_job = control_panel_store.claim_next_job("retry-worker")
    control_panel_jobs.process_job(second_job, "retry-worker")
    second_retry = control_panel_store.get_run(user["id"], run["id"])
    assert second_retry["status"] == "queued"

    third_job = control_panel_store.claim_next_job("retry-worker")
    control_panel_jobs.process_job(third_job, "retry-worker")
    final_run = control_panel_store.get_run(user["id"], run["id"])
    final_job = control_panel_store.get_job_for_run(run["id"])
    logs = control_panel_store.list_run_logs(user["id"], run["id"])

    assert final_run["status"] == "failed"
    assert final_job["status"] == "failed"
    assert any("Retrying run" in entry["message"] for entry in logs)
    assert any(entry["message"] == "Synthetic pipeline failure." for entry in logs)


def test_recover_stale_jobs_requeues_running_job(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    user = _create_user()
    run = control_panel_store.create_run(user["id"], "Build Support", str(tmp_path / "generated_apps" / "support"))
    claimed = control_panel_store.claim_next_job("stale-worker")
    assert claimed["status"] == "running"

    stale_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    with control_panel_store._engine().begin() as connection:
        connection.execute(
            control_panel_store.update(control_panel_store.jobs)
            .where(control_panel_store.jobs.c.run_id == run["id"])
            .values(updated_at=stale_time)
        )
        connection.execute(
            control_panel_store.insert(control_panel_store.worker_heartbeats).values(
                worker_id="stale-worker",
                status="alive",
                last_seen_at=stale_time,
                backend="sqlite",
            )
        )

    recovered = control_panel_store.recover_stale_jobs(worker_timeout_seconds=30, lease_timeout_seconds=30)
    job = control_panel_store.get_job_for_run(run["id"])

    assert run["id"] in recovered
    assert job["status"] == "queued"
    assert job["worker_id"] is None
