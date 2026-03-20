import pytest
from fastapi.testclient import TestClient

from engine.project_builder import build_project_from_manifest
from engine.runtime_verifier import _generated_backend_context, verify_generated_backend_runtime
from tests.golden_prompts import GOLDEN_PROMPTS


@pytest.mark.parametrize("case", GOLDEN_PROMPTS, ids=[case["name"] for case in GOLDEN_PROMPTS])
def test_generated_backend_runtime_for_golden_prompt(case, tmp_path):
    app_root = tmp_path / case["name"]
    manifest, _saved_files = build_project_from_manifest(case["manifest_output"], app_root=str(app_root))

    runtime = verify_generated_backend_runtime(
        str(app_root),
        expected_family_route=case["expected"]["route_path"] if case["expected"]["route_path"].startswith("/api/") else f"/api{case['expected']['route_path']}",
    )

    assert runtime["config"]["appType"] == manifest["app_type"]
    assert runtime["config"]["primaryEntity"] == manifest["primary_entity"]
    assert runtime["entities"]["primaryTable"] == runtime["config"]["primaryTable"]
    assert runtime["session"]["user"]["role"] in manifest["auth"]["roles"]
    assert isinstance(runtime["summary"]["totalItems"], int)


def test_crm_business_engine_advances_deal_stage(tmp_path):
    case = next(case for case in GOLDEN_PROMPTS if case["name"] == "crm")
    app_root = tmp_path / "crm"
    build_project_from_manifest(case["manifest_output"], app_root=str(app_root))

    with _generated_backend_context(str(app_root)):
        from main import app

        with TestClient(app) as client:
            response = client.post("/api/crm/deals/1/advance?user_email=avery@example.com")
            assert response.status_code == 200
            assert response.json()["deal"]["status"] == "proposal"


def test_support_business_engine_escalates_ticket(tmp_path):
    case = next(case for case in GOLDEN_PROMPTS if case["name"] == "support")
    app_root = tmp_path / "support"
    build_project_from_manifest(case["manifest_output"], app_root=str(app_root))

    with _generated_backend_context(str(app_root)):
        from main import app

        with TestClient(app) as client:
            response = client.post("/api/support/tickets/1/escalate?user_email=avery@example.com")
            assert response.status_code == 200
            assert response.json()["ticket"]["status"] == "escalated"
            assert response.json()["ticket"]["priority"] == "high"


def test_project_management_business_engine_advances_project(tmp_path):
    case = next(case for case in GOLDEN_PROMPTS if case["name"] == "project_management")
    app_root = tmp_path / "project_management"
    build_project_from_manifest(case["manifest_output"], app_root=str(app_root))

    with _generated_backend_context(str(app_root)):
        from main import app

        with TestClient(app) as client:
            response = client.post("/api/project-management/projects/1/advance?user_email=avery@example.com")
            assert response.status_code == 200
            assert response.json()["project"]["status"] == "complete"
            assert response.json()["project"]["progress"] == 100


def test_recruiting_business_engine_advances_candidate(tmp_path):
    case = next(case for case in GOLDEN_PROMPTS if case["name"] == "recruiting")
    app_root = tmp_path / "recruiting"
    build_project_from_manifest(case["manifest_output"], app_root=str(app_root))

    with _generated_backend_context(str(app_root)):
        from main import app

        with TestClient(app) as client:
            response = client.post("/api/recruiting/candidates/1/advance?user_email=avery@example.com")
            assert response.status_code == 200
            assert response.json()["candidate"]["status"] == "interview"


def test_inventory_business_engine_creates_reorder_request(tmp_path):
    case = next(case for case in GOLDEN_PROMPTS if case["name"] == "inventory")
    app_root = tmp_path / "inventory"
    build_project_from_manifest(case["manifest_output"], app_root=str(app_root))

    with _generated_backend_context(str(app_root)):
        from main import app

        with TestClient(app) as client:
            response = client.post("/api/inventory/items/1/reorder?user_email=avery@example.com")
            assert response.status_code == 200
            assert response.json()["item"]["status"] == "reorder_pending"


def test_finance_business_engine_approves_invoice(tmp_path):
    case = next(case for case in GOLDEN_PROMPTS if case["name"] == "finance")
    app_root = tmp_path / "finance"
    build_project_from_manifest(case["manifest_output"], app_root=str(app_root))

    with _generated_backend_context(str(app_root)):
        from main import app

        with TestClient(app) as client:
            response = client.post("/api/finance/invoices/1/approve?user_email=avery@example.com")
            assert response.status_code == 200
            assert response.json()["invoice"]["status"] == "approved"


def test_generated_provider_adapters_report_missing_credentials(tmp_path):
    case = next(case for case in GOLDEN_PROMPTS if case["name"] == "saas_analytics")
    app_root = tmp_path / "providers"
    build_project_from_manifest(case["manifest_output"], app_root=str(app_root))

    with _generated_backend_context(str(app_root)):
        from providers import build_checkout_session, build_storage_upload, send_email_message

        checkout = build_checkout_session("stripe", 99, "usd", "Generated checkout")
        email = send_email_message("sendgrid", "demo@example.com", "Hello", "World")
        upload = build_storage_upload("s3", "demo.json", "application/json")

        assert checkout["mode"] == "config_required"
        assert "PAYMENTS_SECRET_KEY" in checkout["required_env"]
        assert email["mode"] == "config_required"
        assert "EMAIL_API_KEY" in email["required_env"]
        assert upload["mode"] == "config_required"
        assert "AWS_ACCESS_KEY_ID" in upload["required_env"]
