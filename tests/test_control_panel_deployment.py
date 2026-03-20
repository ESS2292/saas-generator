from pathlib import Path


def test_control_panel_deployment_artifacts_exist():
    expected_paths = [
        Path("Dockerfile.control-panel"),
        Path("deployment/control-panel-docker-compose.yml"),
        Path("deployment/control-panel-render.yaml"),
        Path("deployment/control-panel-railway.json"),
        Path("deployment/CONTROL_PANEL.md"),
    ]

    for path in expected_paths:
        assert path.exists(), f"Missing deployment artifact: {path}"


def test_control_panel_deployment_artifacts_have_expected_markers():
    assert '"web_app:app"' in Path("Dockerfile.control-panel").read_text()
    compose_text = Path("deployment/control-panel-docker-compose.yml").read_text()
    render_text = Path("deployment/control-panel-render.yaml").read_text()
    railway_text = Path("deployment/control-panel-railway.json").read_text()

    assert "control-panel-worker" in compose_text
    assert "postgres:16" in compose_text
    assert "CONTROL_PANEL_DATABASE_URL" in compose_text
    assert "startCommand: uvicorn web_app:app" in Path("deployment/control-panel-render.yaml").read_text()
    assert "type: worker" in render_text
    assert "saas-generator-control-panel-db" in render_text
    assert '"startCommand": "uvicorn web_app:app --host 0.0.0.0 --port $PORT"' in railway_text
    assert "CONTROL_PANEL_DATABASE_URL" in railway_text
