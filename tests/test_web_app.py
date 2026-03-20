from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import update

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


def test_web_app_index_requires_auth(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    client = TestClient(web_app.app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Control Panel Access" in response.text
    assert "Register" in response.text


def test_web_app_registers_and_sets_session_cookie(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    client = TestClient(web_app.app)

    response = _register_and_login(client)

    assert response.cookies.get(web_app.SESSION_COOKIE)
    assert response.json()["user"]["email"] == "owner@example.com"


def test_web_app_returns_authenticated_dashboard(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": True, "status": "ready", "message": "Ready"},
    )
    client = TestClient(web_app.app)
    _register_and_login(client)

    response = client.get("/")

    assert response.status_code == 200
    assert "Authenticated Control Panel" in response.text
    assert "Your Runs" in response.text
    assert "Stored Secrets" in response.text
    assert "OpenAI Access" in response.text
    assert "Advanced mode" in response.text


def test_web_app_returns_usage_summary(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": True, "status": "ready", "message": "Ready"},
    )
    client = TestClient(web_app.app)
    register_response = _register_and_login(client)

    me_response = client.get("/api/me")
    usage_response = client.get("/api/billing/usage")

    assert me_response.status_code == 200
    assert usage_response.status_code == 200
    assert me_response.json()["user"]["id"] == register_response.json()["user"]["id"]
    assert usage_response.json()["monthly_run_limit"] == 5
    assert usage_response.json()["monthly_run_usage"] == 0
    assert usage_response.json()["remaining_runs"] == 5
    assert usage_response.json()["database_url"].startswith("sqlite:///")


def test_web_app_stores_lists_and_deletes_secrets(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": True, "status": "ready", "message": "Ready"},
    )
    client = TestClient(web_app.app)
    register_response = _register_and_login(client)
    user_id = register_response.json()["user"]["id"]

    store_response = client.post(
        "/api/secrets",
        json={"name": "RENDER_API_KEY", "value": "secret-value"},
    )
    list_response = client.get("/api/secrets")

    assert store_response.status_code == 200
    assert list_response.status_code == 200
    assert list_response.json()["secrets"][0]["name"] == "RENDER_API_KEY"
    assert control_panel_store.get_secret_value(user_id, "RENDER_API_KEY") == "secret-value"

    delete_response = client.delete("/api/secrets/RENDER_API_KEY")
    assert delete_response.status_code == 200
    assert client.get("/api/secrets").json()["secrets"] == []


def test_web_app_scopes_runs_to_current_user(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    monkeypatch.setattr(web_app, "app_root_for_idea", lambda prompt: f"generated_apps/{prompt.split()[1].lower()}")
    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": True, "status": "ready", "message": "Ready"},
    )

    owner = TestClient(web_app.app)
    _register_and_login(owner, email="owner@example.com", password="secret123", name="Owner")
    owner.post("/api/runs", json={"prompt": "Build CRM", "run_verification": True, "auto_deploy": False})

    second = TestClient(web_app.app)
    _register_and_login(second, email="second@example.com", password="secret456", name="Second")
    second.post("/api/runs", json={"prompt": "Build Support", "run_verification": True, "auto_deploy": False})

    owner_runs = owner.get("/api/runs").json()["runs"]
    second_runs = second.get("/api/runs").json()["runs"]

    assert len(owner_runs) == 1
    assert len(second_runs) == 1
    assert owner_runs[0]["prompt"] == "Build CRM"
    assert second_runs[0]["prompt"] == "Build Support"


def test_web_app_enforces_monthly_run_quota(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    monkeypatch.setattr(web_app, "app_root_for_idea", lambda prompt: f"generated_apps/{prompt.lower().replace(' ', '-')}")
    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": True, "status": "ready", "message": "Ready"},
    )
    client = TestClient(web_app.app)
    register_response = _register_and_login(client)
    user_id = register_response.json()["user"]["id"]

    control_panel_store.set_user_plan(user_id, "free", 1)
    with control_panel_store._engine().begin() as connection:
        connection.execute(
            update(control_panel_store.users)
            .where(control_panel_store.users.c.id == user_id)
            .values(monthly_run_usage=1)
        )

    response = client.post("/api/runs", json={"prompt": "Build Inventory", "run_verification": True, "auto_deploy": False})

    assert response.status_code == 403
    assert "Monthly run limit reached" in response.json()["error"]


def test_web_app_processes_job_and_exposes_logs_and_artifacts(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    app_root = tmp_path / "generated_apps" / "crm"
    monkeypatch.setattr(web_app, "app_root_for_idea", lambda prompt: str(app_root))
    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": True, "status": "ready", "message": "Ready"},
    )

    def fake_generate_saas_app(prompt, app_root, run_verification, auto_deploy):
        root = Path(app_root)
        (root / "deploy").mkdir(parents=True, exist_ok=True)
        (root / "backend").mkdir(parents=True, exist_ok=True)
        (root / "frontend" / "src").mkdir(parents=True, exist_ok=True)
        (root / "manifest.json").write_text('{"app_name":"CRM Control","app_type":"crm_platform"}')
        (root / "backend" / "main.py").write_text("app = object()")
        (root / "frontend" / "src" / "App.jsx").write_text("export default function App() { return null; }")
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

    create_response = client.post("/api/runs", json={"prompt": "Build CRM", "run_verification": True, "auto_deploy": False})
    assert create_response.status_code == 202
    run_id = create_response.json()["id"]

    job = control_panel_store.claim_next_job("test-worker")
    assert job["run_id"] == run_id
    control_panel_jobs.process_job(job, "test-worker")

    run_response = client.get(f"/api/runs/{run_id}")
    logs_response = client.get(f"/api/runs/{run_id}/logs")
    artifacts_response = client.get(f"/api/runs/{run_id}/artifacts")

    assert run_response.status_code == 200
    assert run_response.json()["status"] == "completed"
    assert run_response.json()["result"]["app_name"] == "CRM Control"
    assert any("Worker claimed queued run." in entry["message"] for entry in logs_response.json()["logs"])
    assert any(entry["artifact_type"] == "manifest" for entry in artifacts_response.json()["artifacts"])


def test_web_app_deploys_completed_owned_run(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": True, "status": "ready", "message": "Ready"},
    )
    deployed = {}

    def fake_deploy_online(app_folder="generated_app"):
        deployed["app_folder"] = app_folder

    monkeypatch.setattr(web_app, "deploy_online", fake_deploy_online)
    client = TestClient(web_app.app)
    register_response = _register_and_login(client)
    user_id = register_response.json()["user"]["id"]
    run = control_panel_store.create_run(user_id, "Build Marketplace", "generated_apps/market")
    control_panel_store.update_run(
        run["id"],
        status="completed",
        result={
            "app_name": "Creator Market",
            "closest_family": "marketplace",
            "tests_passed": True,
            "deployed": False,
        },
    )

    response = client.post(f"/api/runs/{run['id']}/deploy")

    assert response.status_code == 200
    assert deployed["app_folder"] == "generated_apps/market"
    updated = control_panel_store.get_run(user_id, run["id"])
    assert updated["result"]["deployed"] is True


def test_web_app_logout_clears_session(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": True, "status": "ready", "message": "Ready"},
    )
    client = TestClient(web_app.app)
    _register_and_login(client)

    logout_response = client.post("/api/auth/logout")
    me_response = client.get("/api/me")

    assert logout_response.status_code == 200
    assert me_response.status_code == 401


def test_web_app_health_reports_external_worker_and_database_backend(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": False, "status": "insufficient_quota", "message": "Quota exceeded"},
    )
    client = TestClient(web_app.app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["worker_mode"] == "external_service"
    assert response.json()["database_backend"] == "sqlite"
    assert response.json()["provider_status"]["status"] == "insufficient_quota"


def test_web_app_exposes_provider_status_to_authenticated_user(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": False, "status": "insufficient_quota", "message": "Quota exceeded"},
    )
    client = TestClient(web_app.app)
    _register_and_login(client)

    response = client.get("/api/provider-status")

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_quota"


def test_web_app_blocks_run_creation_when_provider_is_not_ready(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": False, "status": "insufficient_quota", "message": "Quota exceeded"},
    )
    client = TestClient(web_app.app)
    _register_and_login(client)

    response = client.post("/api/runs", json={"prompt": "Build CRM", "run_verification": True, "auto_deploy": False})

    assert response.status_code == 503
    assert "OpenAI provider is not ready" in response.json()["error"]


def test_web_app_renders_settings_page(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": True, "status": "ready", "message": "Ready"},
    )
    client = TestClient(web_app.app)
    _register_and_login(client)

    response = client.get("/settings")

    assert response.status_code == 200
    assert "Settings" in response.text
    assert "Provider Status" in response.text


def test_web_app_renders_run_detail_page(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": True, "status": "ready", "message": "Ready"},
    )
    client = TestClient(web_app.app)
    register_response = _register_and_login(client)
    user_id = register_response.json()["user"]["id"]
    run = control_panel_store.create_run(user_id, "Build CRM", "generated_apps/crm")
    control_panel_store.update_run(
        run["id"],
        status="completed",
        result={"app_name": "CRM Control", "tests_passed": True, "closest_family": "crm_platform", "support_tier": "supported"},
        error="",
    )
    control_panel_store.append_run_log(run["id"], "info", "Run finished.")

    response = client.get(f"/runs/{run['id']}")

    assert response.status_code == 200
    assert "CRM Control" in response.text
    assert "Stage Timeline" in response.text
    assert "Download App" in response.text


def test_web_app_downloads_run_bundle(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": True, "status": "ready", "message": "Ready"},
    )
    app_root = tmp_path / "generated_apps" / "crm"
    (app_root / "backend").mkdir(parents=True, exist_ok=True)
    (app_root / "backend" / "main.py").write_text("app = object()")
    client = TestClient(web_app.app)
    register_response = _register_and_login(client)
    user_id = register_response.json()["user"]["id"]
    run = control_panel_store.create_run(user_id, "Build CRM", str(app_root))

    response = client.get(f"/api/runs/{run['id']}/download")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_web_app_builds_advanced_prompt_before_queueing(tmp_path, monkeypatch):
    _isolate_control_panel_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        web_app,
        "check_openai_generation_access",
        lambda: {"ok": True, "status": "ready", "message": "Ready"},
    )
    monkeypatch.setattr(web_app, "app_root_for_idea", lambda prompt: f"generated_apps/{prompt.lower().replace(' ', '-')}")
    client = TestClient(web_app.app)
    register_response = _register_and_login(client)
    user_id = register_response.json()["user"]["id"]

    response = client.post(
        "/api/runs",
        json={
            "prompt": "Build training app",
            "mode": "advanced",
            "app_name": "CoachOS",
            "target_users": "coaches and clients",
            "core_entities": "programs, sessions",
            "core_workflows": "weekly plan delivery",
            "run_verification": True,
            "auto_deploy": False,
        },
    )

    assert response.status_code == 202
    stored_run = control_panel_store.list_runs(user_id, limit=1)[0]
    assert "Advanced build brief" in stored_run["prompt"]
    assert "CoachOS" in stored_run["prompt"]
