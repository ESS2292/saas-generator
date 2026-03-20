from control_panel.models import RunArtifact, RunLogEntry, RunResultSummary, RunStage, RunView


def test_run_view_model_dump_preserves_nested_control_panel_models():
    view = RunView(
        id="run-1",
        user_id=7,
        prompt="Build CRM",
        app_root="generated_apps/crm",
        run_verification=True,
        auto_deploy=False,
        status="completed",
        created_at="2026-03-20T00:00:00Z",
        updated_at="2026-03-20T00:01:00Z",
        result=RunResultSummary(
            success=True,
            app_name="CRM Control",
            closest_family="crm_platform",
            support_tier="supported",
            tests_passed=True,
            saved_files_count=4,
        ),
        friendly_error="No error reported.",
        stages=[RunStage(key="completed", label="Completed", state="done")],
        current_stage=RunStage(key="completed", label="Completed", state="done"),
        logs=[RunLogEntry(level="info", message="Pipeline finished.", created_at="2026-03-20T00:01:00Z")],
        artifacts=[RunArtifact(artifact_type="manifest", label="Manifest", path="generated_apps/crm/manifest.json")],
    )

    payload = view.model_dump()

    assert payload["result"]["app_name"] == "CRM Control"
    assert payload["stages"][0]["key"] == "completed"
    assert payload["current_stage"]["state"] == "done"
    assert payload["logs"][0]["message"] == "Pipeline finished."
    assert payload["artifacts"][0]["artifact_type"] == "manifest"
