import json
from html import escape
from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

from control_panel.lifecycle import current_stage_indicator, plain_status_label, run_stage_summary, stage_progress_percent
from control_panel.models import RunArtifact, RunLogEntry, RunResultSummary, RunView
from control_panel.observability import build_run_metrics, build_system_metrics
from control_panel.rendering import render_template
from control_panel.theme import theme_html_attrs
from memory.control_panel_store import (
    get_database_backend,
    get_run,
    get_usage_summary,
    get_user_by_session,
    list_recent_workers,
    list_run_artifacts,
    list_run_logs,
    list_runs,
    list_secrets,
)


SESSION_COOKIE = "sg_session"

PROMPT_TEMPLATES = [
    {"label": "CRM", "prompt": "Build a CRM for managing leads, deals, tasks, and sales pipeline reviews."},
    {"label": "Booking", "prompt": "Build a booking platform for personal trainers with schedules, clients, and session tracking."},
    {"label": "Support", "prompt": "Build a support desk for tracking tickets, escalations, SLAs, and customer updates."},
    {"label": "Marketplace", "prompt": "Build a marketplace for fitness coaches to sell programs and manage buyer inquiries."},
]


def json_error(message, status_code=400):
    return JSONResponse({"error": message}, status_code=status_code)


def current_user(request: Request):
    return get_user_by_session(request.cookies.get(SESSION_COOKIE))


def friendly_error_message(message):
    text = str(message or "").strip()
    if not text:
        return "No error reported."
    lowered = text.lower()
    if "insufficient_quota" in lowered or "exceeded your current quota" in lowered:
        return "OpenAI account quota is exhausted. Update billing or switch to a funded API key."
    if "openai_api_key" in lowered and "not configured" in lowered:
        return "OpenAI API key is missing. Add a valid key before starting a run."
    if "cannot deploy a run that did not pass verification" in lowered:
        return "Deployment is blocked because verification did not pass."
    if "docker" in lowered and "not found" in lowered:
        return "Docker is not installed or not available to the generator."
    if "npm" in lowered and "not found" in lowered:
        return "Node/npm is not installed or not available to the generator."
    if "frontend build" in lowered:
        return "The generated frontend did not build successfully."
    if "backend runtime" in lowered:
        return "The generated backend did not start successfully."
    return text


def worker_status():
    workers = list_recent_workers(limit=5)
    return {
        "ok": bool(workers),
        "status": "ready" if workers else "missing",
        "workers": workers,
        "message": "Worker heartbeat detected." if workers else "No active worker heartbeat has been recorded yet.",
    }


def readiness_status():
    import web_app

    provider = web_app.check_openai_generation_access()
    worker = worker_status()
    ready = bool(provider.get("ok")) and bool(worker.get("ok"))
    return {
        "ok": ready,
        "database_backend": get_database_backend(),
        "worker_mode": "external_service",
        "provider_status": provider,
        "worker_status": worker,
    }


def build_prompt(payload):
    prompt = payload.prompt.strip()
    if payload.mode != "advanced":
        return prompt
    details = []
    if payload.app_name.strip():
        details.append(f"App name: {payload.app_name.strip()}")
    if payload.target_users.strip():
        details.append(f"Target users: {payload.target_users.strip()}")
    if payload.core_entities.strip():
        details.append(f"Core entities: {payload.core_entities.strip()}")
    if payload.core_workflows.strip():
        details.append(f"Core workflows: {payload.core_workflows.strip()}")
    if not details:
        return prompt
    return prompt + "\n\nAdvanced build brief:\n- " + "\n- ".join(details)


def run_payload(user_id, run_id):
    run = get_run(user_id, run_id)
    if not run:
        return None
    # Normalize DB rows into typed view models before they leave the API layer.
    logs = [RunLogEntry(**entry) for entry in (list_run_logs(user_id, run_id, limit=200) or [])]
    artifacts = [RunArtifact(**entry) for entry in (list_run_artifacts(user_id, run_id) or [])]
    result = RunResultSummary(**(run.get("result") or {})) if run.get("result") else None
    run_data = {
        **run,
        "result": result,
        "friendly_error": friendly_error_message(run.get("error")),
        "stages": run_stage_summary(run),
        "current_stage": current_stage_indicator(run),
        "logs": logs,
        "artifacts": artifacts,
    }
    return RunView(**run_data).model_dump()


def run_summary_payload(run):
    result = RunResultSummary(**(run.get("result") or {})) if run.get("result") else None
    run_data = {
        **run,
        "result": result,
        "friendly_error": friendly_error_message(run.get("error")),
        "stages": run_stage_summary(run),
        "current_stage": current_stage_indicator(run),
    }
    return RunView(**run_data).model_dump(exclude={"logs", "artifacts"})


def setup_checklist(user):
    usage = get_usage_summary(user["id"]) or {}
    import web_app

    provider = web_app.check_openai_generation_access()
    secrets = list_secrets(user["id"])
    return [
        {
            "label": "AI connection",
            "ok": provider.get("ok", False),
            "message": provider.get("message", "Unknown provider state."),
        },
        {
            "label": "Run quota",
            "ok": usage.get("remaining_runs", 0) > 0,
            "message": f"{usage.get('remaining_runs', 0)} runs remaining this month.",
        },
        {
            "label": "Connected accounts",
            "ok": len(secrets) > 0,
            "message": "No connected accounts yet. You can add them later in settings.",
        },
    ]


def render_auth_page(theme="light"):
    html_attrs, body_attrs = theme_html_attrs(theme)
    return render_template(
        "auth.html",
        title="SaaS Generator Login",
        html_attrs=html_attrs,
        body_attrs=body_attrs,
        theme_toggle_label="Light mode" if theme == "dark" else "Dark mode",
    )


def _render_run_card(run):
    result = run.get("result") or {}
    latest_error = friendly_error_message(run.get("error") or result.get("latest_error") or "None")
    status_label = plain_status_label(run.get("status"))
    current_stage = current_stage_indicator(run)
    stage_percent = stage_progress_percent(current_stage)
    stage_label = current_stage.label if current_stage.state != "failed" else "Failed"
    stage_markup = f"<div class='stage-track-wrap'><span class='stage-pill stage-{escape(current_stage.state)}'>{escape(stage_label)}</span><div class='stage-track'><span class='stage-fill stage-{escape(current_stage.state)}' style='width:{stage_percent}%;'></span></div></div>"
    deploy_button = ""
    if run.get("status") == "completed" and result.get("tests_passed") and not result.get("deployed"):
        deploy_button = f'<button class="secondary-button" data-deploy-run="{escape(run["id"])}">Deploy App</button>'
    return f"""
      <article class="run-card" data-run-id="{escape(run['id'])}">
        <div class="run-header">
          <div><p class="eyebrow">App Request</p><h3>{escape(result.get('app_name', 'New App'))}</h3></div>
          <span class="status-pill status-{escape(run['status'])}">{escape(status_label)}</span>
        </div>
        <p class="prompt-copy">{escape(run['prompt'])}</p>
        <div class="stage-row"><strong>Current step:</strong> {stage_markup}</div>
        <div class="metric-grid">
          <div class="metric"><span>App type</span><strong>{escape(result.get('closest_family', 'in progress').replace('_', ' '))}</strong></div>
          <div class="metric"><span>Status</span><strong>{escape(status_label)}</strong></div>
          <div class="metric"><span>Ready to download</span><strong>{'Yes' if result.get('saved_files_count') else 'Not yet'}</strong></div>
          <div class="metric"><span>Quality check</span><strong>{'Passed' if result.get('tests_passed') else 'In progress'}</strong></div>
        </div>
        <div class="detail-grid">
          <div class="panel">
            <h4>Main parts</h4>
            <p><strong>For:</strong> {escape(', '.join(result.get('primary_users', [])) or 'Still deciding')}</p>
            <p><strong>Includes:</strong> {escape(', '.join(result.get('core_entities', [])) or 'Still deciding')}</p>
            <p><strong>Key actions:</strong> {escape(', '.join(result.get('core_workflows', [])) or 'Still deciding')}</p>
          </div>
          <div class="panel">
            <h4>Progress</h4>
            <p><strong>Quality check:</strong> {'Passed' if result.get('tests_passed') else 'Not finished yet'}</p>
            <p><strong>Published online:</strong> {'Yes' if result.get('deployed') else 'No'}</p>
            <p><strong>Need attention:</strong> {escape(latest_error)}</p>
          </div>
        </div>
        <div class="button-row"><a class="ghost-link" href="/runs/{escape(run['id'])}">Open details</a>{deploy_button}</div>
      </article>
    """


def render_dashboard(user, theme="light"):
    html_attrs, body_attrs = theme_html_attrs(theme)
    runs = list_runs(user["id"], limit=20)
    usage = get_usage_summary(user["id"]) or {}
    secrets = list_secrets(user["id"])
    import web_app

    provider_status = web_app.check_openai_generation_access()
    checklist = setup_checklist(user)
    first_run = len(runs) == 0
    history_markup = "".join(_render_run_card(run) for run in runs) or "<p class='empty-state'>Your apps will appear here after your first build.</p>"
    secret_markup = "".join(
        f"<div class='secret-row'><strong>{escape(secret['name'])}</strong><span>{escape(secret['updated_at'])}</span><button class='ghost-button' data-delete-secret='{escape(secret['name'])}'>Delete</button></div>"
        for secret in secrets
    ) or "<p class='empty-state'>No saved account keys yet.</p>"
    checklist_markup = "".join(
        f"<div class='check-row'><strong>{escape(item['label'])}</strong><span class='check-state {'ok' if item['ok'] else 'warn'}'>{'Ready' if item['ok'] else 'Needs attention'}</span><p>{escape(item['message'])}</p></div>"
        for item in checklist
    )
    onboarding_markup = ""
    if first_run:
        onboarding_markup = f"""
<section class="ops"><div class="panel"><p class="eyebrow">Before You Start</p><h3>Quick check</h3><div class="checklist">{checklist_markup}</div><p class="hint">Choose a template below, or open more options if you want more control.</p></div></section>
"""
    return render_template(
        "dashboard.html",
        title="SaaS Generator Control Panel",
        html_attrs=html_attrs,
        body_attrs=body_attrs,
        user=user,
        usage=usage,
        provider_status=provider_status,
        prompt_templates=PROMPT_TEMPLATES,
        secret_markup=secret_markup,
        history_markup=history_markup,
        onboarding_markup=onboarding_markup,
        theme_toggle_label="Light mode" if theme == "dark" else "Dark mode",
    )


def render_settings_page(user, theme="light"):
    html_attrs, body_attrs = theme_html_attrs(theme)
    usage = get_usage_summary(user["id"]) or {}
    import web_app

    provider = web_app.check_openai_generation_access()
    secrets = list_secrets(user["id"])
    secret_markup = "".join(
        f"<li><strong>{escape(secret['name'])}</strong> · updated {escape(secret['updated_at'])}</li>"
        for secret in secrets
    ) or "<li>No stored secrets yet.</li>"
    return render_template(
        "settings.html",
        title="Settings",
        html_attrs=html_attrs,
        body_attrs=body_attrs,
        usage=usage,
        provider=provider,
        secret_markup=secret_markup,
        theme_toggle_label="Light mode" if theme == "dark" else "Dark mode",
    )


def render_run_detail_page(user, run, theme="light"):
    html_attrs, body_attrs = theme_html_attrs(theme)
    payload = run_payload(user["id"], run["id"]) or {}
    result = payload.get("result") or {}
    logs = payload.get("logs") or []
    artifacts = payload.get("artifacts") or []
    current_stage = payload.get("current_stage") or current_stage_indicator(run)
    stage_label = current_stage["label"] if current_stage["state"] != "failed" else "Failed"
    stage_percent = stage_progress_percent(current_stage)
    stage_markup = f"<div class='stage-track-wrap'><span class='stage-pill stage-{escape(current_stage['state'])}'>{escape(stage_label)}</span><div class='stage-track'><span class='stage-fill stage-{escape(current_stage['state'])}' style='width:{stage_percent}%;'></span></div></div>"
    log_text = "\n".join(
        f"[{entry['created_at']}] {entry['level'].upper()}: {entry['message']}" for entry in logs
    ) or "No logs yet."
    artifact_markup = "".join(
        f"<li><strong>{escape(item['label'])}</strong><br />{escape(item['path'])}</li>" for item in artifacts
    ) or "<li>No artifacts yet.</li>"
    if run["status"] == "completed" and result.get("tests_passed"):
        outcome_title = "Your app is ready"
        outcome_text = "The build finished and the quality check passed. You can download it now."
        outcome_class = "outcome-ready"
    elif run["status"] == "failed":
        outcome_title = "This build needs attention"
        outcome_text = friendly_error_message(run.get("error") or result.get("latest_error") or "Something went wrong during the build.")
        outcome_class = "outcome-failed"
    else:
        outcome_title = "Your app is being built"
        outcome_text = "Stay on this page to watch the progress update live."
        outcome_class = "outcome-progress"
    return render_template(
        "run_detail.html",
        title="Run Details",
        html_attrs=html_attrs,
        body_attrs=body_attrs,
        run_id=run["id"],
        app_name=result.get("app_name", "App details"),
        family_label=result.get("closest_family", "pending").replace("_", " "),
        support_tier=result.get("support_tier", "pending"),
        verification_label="Passed" if result.get("tests_passed") else "Not passed",
        deployed_label="Yes" if result.get("deployed") else "No",
        status_label=plain_status_label(run["status"]),
        run_prompt=run["prompt"],
        friendly_error=friendly_error_message(run.get("error") or result.get("latest_error") or "None"),
        stage_markup=stage_markup,
        artifact_markup=artifact_markup,
        log_text=log_text,
        outcome_title=outcome_title,
        outcome_text=outcome_text,
        outcome_class=outcome_class,
        theme_toggle_label="Light mode" if theme == "dark" else "Dark mode",
    )


__all__ = [
    "SESSION_COOKIE",
    "PROMPT_TEMPLATES",
    "build_prompt",
    "build_run_metrics",
    "build_system_metrics",
    "current_user",
    "friendly_error_message",
    "json_error",
    "readiness_status",
    "render_auth_page",
    "render_dashboard",
    "render_run_detail_page",
    "render_settings_page",
    "run_payload",
    "run_summary_payload",
]
