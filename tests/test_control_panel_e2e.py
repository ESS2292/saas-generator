from pathlib import Path

from fastapi.testclient import TestClient

import web_app
from engine import control_panel_jobs
from memory import control_panel_store


def _isolate_control_panel_db(tmp_path, monkeypatch):
    monkeypatch.setattr(control_panel_store, "DB_PATH", tmp_path / "control_panel.db")
    control_panel_store.init_db()


def _register_and_login(client, email="owner@example.com", password="secret123", name="Owner"):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "name": name},
    )
    assert response.status_code == 200
    return response


def test_control_panel_e2e_run_flow(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    app_root = tmp_path / "generated_apps" / "crm-control"

    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": True, "status": "ready", "message": "Ready"},
    )
    monkeypatch.setattr(web_app, "app_root_for_idea", lambda prompt: str(app_root))

    def fake_generate_saas_app(prompt, app_root, run_verification, auto_deploy):
        root = Path(app_root)
        (root / "deploy").mkdir(parents=True, exist_ok=True)
        (root / "backend").mkdir(parents=True, exist_ok=True)
        (root / "frontend" / "src").mkdir(parents=True, exist_ok=True)
        (root / "manifest.json").write_text(
            '{"app_name":"CRM Control","app_type":"crm_platform"}'
        )
        (root / "backend" / "main.py").write_text("app = object()\n")
        (root / "frontend" / "src" / "App.jsx").write_text(
            "export default function App() { return null; }\n"
        )
        (root / "deploy" / "README.md").write_text("deploy steps\n")
        return {
            "success": True,
            "app_root": app_root,
            "tests_passed": True,
            "deployed": False,
            "latest_error": "",
            "saved_files_count": 4,
            "manifest": {"app_name": "CRM Control"},
            "intake_context": {"closest_family": "crm_platform", "support_tier": "supported"},
            "spec_brief": {
                "primary_users": ["sales manager"],
                "core_entities": ["lead", "deal"],
                "core_workflows": ["advance deal"],
            },
        }

    monkeypatch.setattr(control_panel_jobs, "generate_saas_app", fake_generate_saas_app)

    client = TestClient(web_app.app)
    _register_and_login(client)

    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert "Build my app" in dashboard.text

    create_response = client.post(
        "/api/runs",
        json={
            "prompt": "Build a CRM for leads and pipeline reviews",
            "run_verification": True,
            "auto_deploy": False,
            "mode": "advanced",
            "app_name": "CRM Control",
            "target_users": "Sales managers",
            "core_entities": "Leads, deals",
            "core_workflows": "Advance deals, assign follow-ups",
        },
    )
    assert create_response.status_code == 202
    run_id = create_response.json()["id"]

    queued_payload = client.get(f"/api/runs/{run_id}").json()
    assert queued_payload["status"] == "queued"
    assert queued_payload["current_stage"]["state"] in {"pending", "current"}

    claimed_job = control_panel_store.claim_next_job("e2e-worker")
    assert claimed_job["run_id"] == run_id
    control_panel_jobs.process_job(claimed_job, "e2e-worker")

    run_response = client.get(f"/api/runs/{run_id}")
    artifacts_response = client.get(f"/api/runs/{run_id}/artifacts")
    logs_response = client.get(f"/api/runs/{run_id}/logs")
    detail_response = client.get(f"/runs/{run_id}")

    assert run_response.status_code == 200
    assert run_response.json()["status"] == "completed"
    assert run_response.json()["result"]["app_name"] == "CRM Control"
    assert run_response.json()["result"]["tests_passed"] is True
    assert detail_response.status_code == 200
    assert "CRM Control" in detail_response.text
    assert "Your app is ready" in detail_response.text
    assert any(item["artifact_type"] == "manifest" for item in artifacts_response.json()["artifacts"])
    assert any(item["artifact_type"] == "backend" for item in artifacts_response.json()["artifacts"])
    assert any("Worker claimed queued run." in entry["message"] for entry in logs_response.json()["logs"])

    with client.stream("GET", f"/api/runs/{run_id}/stream?once=true") as stream_response:
        streamed_event = ""
        for line in stream_response.iter_lines():
            if line.startswith("data: "):
                streamed_event = line
                break

    assert stream_response.status_code == 200
    assert '"status": "completed"' in streamed_event

    download_response = client.get(f"/api/runs/{run_id}/download")
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/zip"
    assert download_response.content[:2] == b"PK"
