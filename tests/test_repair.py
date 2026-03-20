from engine.repair import (
    artifact_group_for_failure,
    canonicalize_manifest_output,
    repair_project_for_failure,
    repair_project_from_output,
    rewrite_project_scaffold,
)
from engine.validator import validate_project_scaffold


MANIFEST_OUTPUT = """
{
  "app_name": "Repair Desk",
  "slug": "repair-desk",
  "app_type": "internal_tool",
  "tagline": "Handle ops work",
  "summary": "Operational repair workspace",
  "primary_entity": "Ticket",
  "theme": {
    "primary_color": "#0f766e",
    "accent_color": "#f59e0b",
    "surface_color": "#ecfeff"
  },
  "dashboard": {
    "headline": "Repair dashboard",
    "subheadline": "Fix issues by queue",
    "sections": [{"title": "Queue", "description": "Review pending work"}]
  },
  "pages": [{"name": "Overview", "purpose": "See queue state"}],
  "workflows": [{"name": "Route ticket", "steps": ["Create", "Assign", "Resolve"]}],
  "auth": {
    "enabled": true,
    "roles": ["owner", "manager", "viewer"],
    "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
  },
  "capabilities": {"search": true, "notifications": true, "automation": true},
  "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
  "data_model": [{"name": "Ticket", "fields": [{"name": "status", "type": "string"}]}],
  "api_routes": [{"path": "/tickets", "method": "GET", "summary": "List tickets"}],
  "sample_records": [{"status": "open"}]
}
"""


def test_canonicalize_manifest_output_backfills_richer_dsl_fields():
    manifest, manifest_text = canonicalize_manifest_output(MANIFEST_OUTPUT)

    assert manifest["permissions"][0]["resource"] == "Ticket"
    assert manifest["layout"]["navigation_style"] == "tabs"
    assert "internal_tool_module" in manifest["family_modules"]
    assert '"permissions"' in manifest_text
    assert '"layout"' in manifest_text


def test_rewrite_project_scaffold_repairs_missing_generated_files(tmp_path):
    manifest, _manifest_text = canonicalize_manifest_output(MANIFEST_OUTPUT)
    rewrite_project_scaffold(manifest, app_root=str(tmp_path))

    broken_file = tmp_path / "backend" / "app_config.py"
    broken_file.unlink()

    rewrite_project_scaffold(manifest, app_root=str(tmp_path))

    assert broken_file.exists()
    assert validate_project_scaffold(str(tmp_path)) is True


def test_repair_project_from_output_returns_canonical_manifest_text(tmp_path):
    repaired = repair_project_from_output(MANIFEST_OUTPUT, app_root=str(tmp_path))

    assert repaired["manifest"]["app_type"] == "internal_tool"
    assert repaired["manifest_text"].startswith("{\n")
    assert "backend/app_core.py" in repaired["saved_files"]
    assert validate_project_scaffold(str(tmp_path)) is True


def test_artifact_group_for_failure_maps_failure_stages():
    assert artifact_group_for_failure("backend_runtime") == "backend"
    assert artifact_group_for_failure("frontend_build") == "frontend"
    assert artifact_group_for_failure("deployment") == "deploy"
    assert artifact_group_for_failure("unknown", error_text="Vite build failed in frontend") == "frontend"


def test_repair_project_for_failure_repairs_only_targeted_frontend_files(tmp_path):
    repaired = repair_project_from_output(MANIFEST_OUTPUT, app_root=str(tmp_path))
    frontend_broken = tmp_path / "frontend" / "src" / "App.jsx"
    backend_marker = tmp_path / "backend" / "app_core.py"

    frontend_broken.unlink()
    backend_before = backend_marker.read_text(encoding="utf-8")

    targeted = repair_project_for_failure(
        repaired["manifest_text"],
        app_root=str(tmp_path),
        failure_stage="frontend_build",
        error_text="vite build failed",
    )

    assert targeted["artifact_group"] == "frontend"
    assert frontend_broken.exists()
    assert "frontend/src/App.jsx" in targeted["saved_files"]
    assert "backend/app_core.py" not in targeted["saved_files"]
    assert backend_marker.read_text(encoding="utf-8") == backend_before
    assert validate_project_scaffold(str(tmp_path)) is True
