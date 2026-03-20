from control_panel.lifecycle import (
    RunStatus,
    current_stage_indicator,
    plain_status_label,
    stage_progress_percent,
    transition_status,
)
from control_panel.models import RunStage


def test_transition_status_allows_valid_transitions():
    assert transition_status("queued", "running") == RunStatus.RUNNING
    assert transition_status("running", "completed") == RunStatus.COMPLETED
    assert transition_status("completed", "deploying") == RunStatus.DEPLOYING
    assert transition_status("deploying", "failed") == RunStatus.FAILED


def test_transition_status_rejects_invalid_transitions():
    try:
        transition_status("queued", "completed")
    except ValueError as exc:
        assert "Invalid run status transition" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected invalid transition to raise.")


def test_plain_status_label_and_stage_progress_defaults():
    assert plain_status_label("running") == "Building now"
    assert plain_status_label("unknown") == "In progress"
    assert stage_progress_percent(RunStage(key="deploying", label="Deploying", state="current")) == 90
    assert stage_progress_percent({"key": "missing"}) == 8


def test_current_stage_indicator_uses_completed_terminal_state(monkeypatch):
    monkeypatch.setattr(
        "control_panel.lifecycle.run_stage_summary",
        lambda run: [RunStage(key="completed", label="Completed", state="done")],
    )
    stage = current_stage_indicator({"status": "completed"})
    assert stage.key == "completed"
    assert stage.state == "done"
