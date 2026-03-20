import asyncio
from contextlib import asynccontextmanager
from html import escape
import json
from pathlib import Path
import shutil
import tempfile

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from control_panel.lifecycle import current_stage_indicator, plain_status_label, run_stage_summary, stage_progress_percent, transition_status
from control_panel.models import RunArtifact, RunLogEntry, RunResultSummary, RunView
from control_panel.observability import build_run_metrics, build_system_metrics
from control_panel.rendering import render_template
from control_panel.schemas import AuthRequest, GenerateRequest, SecretRequest
from control_panel.theme import THEME_COOKIE, theme_from_request, theme_html_attrs
from deployment.deploy import deploy_online
from engine.control_panel_jobs import artifact_summary
from engine.pipeline import app_root_for_idea
from engine.provider_health import check_openai_generation_access
from memory.control_panel_store import (
    append_run_log,
    authenticate_user,
    create_run,
    create_session,
    delete_secret,
    delete_session,
    get_database_backend,
    get_run,
    get_run_by_id,
    get_usage_summary,
    get_user_by_session,
    init_db,
    list_recent_workers,
    list_run_artifacts,
    list_run_logs,
    list_runs,
    list_secrets,
    register_user,
    replace_run_artifacts,
    store_secret,
    update_run,
)


SESSION_COOKIE = "sg_session"

PROMPT_TEMPLATES = [
    {"label": "CRM", "prompt": "Build a CRM for managing leads, deals, tasks, and sales pipeline reviews."},
    {"label": "Booking", "prompt": "Build a booking platform for personal trainers with schedules, clients, and session tracking."},
    {"label": "Support", "prompt": "Build a support desk for tracking tickets, escalations, SLAs, and customer updates."},
    {"label": "Marketplace", "prompt": "Build a marketplace for fitness coaches to sell programs and manage buyer inquiries."},
]



@asynccontextmanager
async def app_lifespan(_app):
    init_db()
    yield


app = FastAPI(title="SaaS Generator Control Panel", lifespan=app_lifespan)
# Mount the lightweight browser client separately from the server-rendered templates.
app.mount("/static", StaticFiles(directory="control_panel/static"), name="static")


def _json_error(message, status_code=400):
    return JSONResponse({"error": message}, status_code=status_code)


def _current_user(request: Request):
    return get_user_by_session(request.cookies.get(SESSION_COOKIE))


def _friendly_error_message(message):
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


def _worker_status():
    workers = list_recent_workers(limit=5)
    return {
        "ok": bool(workers),
        "status": "ready" if workers else "missing",
        "workers": workers,
        "message": "Worker heartbeat detected." if workers else "No active worker heartbeat has been recorded yet.",
    }


def _readiness_status():
    provider = check_openai_generation_access()
    worker = _worker_status()
    ready = bool(provider.get("ok")) and bool(worker.get("ok"))
    return {
        "ok": ready,
        "database_backend": get_database_backend(),
        "worker_mode": "external_service",
        "provider_status": provider,
        "worker_status": worker,
    }


def _build_prompt(payload: GenerateRequest):
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


def _run_payload(user_id, run_id):
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
        "friendly_error": _friendly_error_message(run.get("error")),
        "stages": run_stage_summary(run),
        "current_stage": current_stage_indicator(run),
        "logs": logs,
        "artifacts": artifacts,
    }
    view = RunView(**run_data)
    return view.model_dump()


def _run_summary_payload(run):
    result = RunResultSummary(**(run.get("result") or {})) if run.get("result") else None
    run_data = {
        **run,
        "result": result,
        "friendly_error": _friendly_error_message(run.get("error")),
        "stages": run_stage_summary(run),
        "current_stage": current_stage_indicator(run),
    }
    view = RunView(**run_data)
    return view.model_dump(exclude={"logs", "artifacts"})


def _setup_checklist(user):
    usage = get_usage_summary(user["id"]) or {}
    provider = check_openai_generation_access()
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


def _render_auth_page(theme="light"):
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
    latest_error = _friendly_error_message(run.get("error") or result.get("latest_error") or "None")
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


def _render_dashboard(user, theme="light"):
    html_attrs, body_attrs = theme_html_attrs(theme)
    runs = list_runs(user["id"], limit=20)
    usage = get_usage_summary(user["id"]) or {}
    secrets = list_secrets(user["id"])
    provider_status = check_openai_generation_access()
    checklist = _setup_checklist(user)
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


def _render_settings_page(user, theme="light"):
    html_attrs, body_attrs = theme_html_attrs(theme)
    usage = get_usage_summary(user["id"]) or {}
    provider = check_openai_generation_access()
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


def _render_run_detail_page(user, run, theme="light"):
    html_attrs, body_attrs = theme_html_attrs(theme)
    payload = _run_payload(user["id"], run["id"]) or {}
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
        outcome_text = _friendly_error_message(run.get("error") or result.get("latest_error") or "Something went wrong during the build.")
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
        friendly_error=_friendly_error_message(run.get("error") or result.get("latest_error") or "None"),
        stage_markup=stage_markup,
        artifact_markup=artifact_markup,
        log_text=log_text,
        outcome_title=outcome_title,
        outcome_text=outcome_text,
        outcome_class=outcome_class,
        theme_toggle_label="Light mode" if theme == "dark" else "Dark mode",
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = _current_user(request)
    theme = theme_from_request(request)
    if not user:
        return _render_auth_page(theme)
    return _render_dashboard(user, theme)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user = _current_user(request)
    theme = theme_from_request(request)
    if not user:
        return _render_auth_page(theme)
    return _render_settings_page(user, theme)


@app.get("/runs/{run_id}", response_class=HTMLResponse)
async def run_detail_page(run_id: str, request: Request):
    user = _current_user(request)
    theme = theme_from_request(request)
    if not user:
        return _render_auth_page(theme)
    run = get_run(user["id"], run_id)
    if not run:
        return HTMLResponse("Run not found.", status_code=404)
    return _render_run_detail_page(user, run, theme)


@app.get("/theme/toggle")
async def toggle_theme(request: Request, next: str = "/"):
    current = theme_from_request(request)
    new_theme = "light" if current == "dark" else "dark"
    response = RedirectResponse(url=next, status_code=303)
    response.set_cookie(THEME_COOKIE, new_theme, httponly=False, samesite="lax")
    return response


@app.get("/api/health")
async def health():
    return _readiness_status()


@app.get("/api/readiness")
async def readiness():
    payload = _readiness_status()
    status_code = 200 if payload["ok"] else 503
    return JSONResponse(payload, status_code=status_code)


@app.get("/api/me")
async def me(request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    return {"user": user, "usage": get_usage_summary(user["id"])}


@app.post("/api/auth/register")
async def register(payload: AuthRequest):
    try:
        user = register_user(payload.email, payload.password, payload.name or payload.email)
    except ValueError as exc:
        return _json_error(str(exc))
    token = create_session(user["id"])
    response = JSONResponse({"ok": True, "user": user})
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax")
    return response


@app.post("/api/auth/login")
async def login(payload: AuthRequest):
    user = authenticate_user(payload.email, payload.password)
    if not user:
        return _json_error("Invalid email or password.", status_code=401)
    token = create_session(user["id"])
    response = JSONResponse({"ok": True, "user": user})
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax")
    return response


@app.post("/api/auth/logout")
async def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        delete_session(token)
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/api/usage")
async def usage(request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    return get_usage_summary(user["id"])


@app.get("/api/billing/usage")
async def billing_usage(request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    return get_usage_summary(user["id"])


@app.get("/api/provider-status")
async def provider_status(request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    return check_openai_generation_access()


@app.get("/api/observability/summary")
async def observability_summary(request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    return build_system_metrics()


@app.get("/api/observability/runs/{run_id}")
async def observability_run_metrics(run_id: str, request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    run = get_run(user["id"], run_id)
    if not run:
        return _json_error("Run not found.", status_code=404)
    return build_run_metrics(run)


@app.get("/api/secrets")
async def secrets_list(request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    return {"secrets": list_secrets(user["id"])}


@app.post("/api/secrets")
async def secrets_save(payload: SecretRequest, request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    if not payload.name.strip() or not payload.value:
        return _json_error("Secret name and value are required.")
    store_secret(user["id"], payload.name.strip(), payload.value)
    return {"ok": True}


@app.delete("/api/secrets/{name}")
async def secrets_delete(name: str, request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    delete_secret(user["id"], name)
    return {"ok": True}


@app.get("/api/runs")
async def get_runs(request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    runs = list_runs(user["id"], limit=20)
    return {
        "runs": [_run_summary_payload(run) for run in runs]
    }


@app.get("/api/runs/{run_id}")
async def get_run_status(run_id: str, request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    run = get_run(user["id"], run_id)
    if not run:
        return _json_error("Run not found.", status_code=404)
    return _run_summary_payload(run)


@app.get("/api/runs/{run_id}/stream")
async def stream_run_status(run_id: str, request: Request, once: bool = False):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    if not get_run(user["id"], run_id):
        return _json_error("Run not found.", status_code=404)

    async def event_stream():
        last_payload = None
        while True:
            payload = _run_payload(user["id"], run_id)
            if payload is None:
                yield "event: error\ndata: {}\n\n"
                break
            serialized = json.dumps(payload)
            if serialized != last_payload:
                yield f"data: {serialized}\n\n"
                last_payload = serialized
                if once:
                    break
            if payload["status"] in {"completed", "failed"}:
                break
            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/runs/{run_id}/logs")
async def get_run_logs_api(run_id: str, request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    logs = list_run_logs(user["id"], run_id)
    if logs is None:
        return _json_error("Run not found.", status_code=404)
    return {"logs": logs}


@app.get("/api/runs/{run_id}/artifacts")
async def get_run_artifacts_api(run_id: str, request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    artifacts = list_run_artifacts(user["id"], run_id)
    if artifacts is None:
        return _json_error("Run not found.", status_code=404)
    return {"artifacts": artifacts}


@app.get("/api/runs/{run_id}/download")
async def download_run_bundle(run_id: str, request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    run = get_run(user["id"], run_id)
    if not run:
        return _json_error("Run not found.", status_code=404)
    app_root = Path(run["app_root"])
    if not app_root.exists():
        return _json_error("Generated app files are not available for download.", status_code=404)
    bundle_dir = Path(tempfile.mkdtemp(prefix="control-panel-bundle-"))
    archive_base = bundle_dir / run_id
    archive_path = shutil.make_archive(str(archive_base), "zip", root_dir=app_root)
    return FileResponse(archive_path, media_type="application/zip", filename=f"{run_id}.zip")


@app.post("/api/runs")
async def create_run_api(payload: GenerateRequest, request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    if not payload.prompt.strip():
        return _json_error("Prompt is required.")
    provider = check_openai_generation_access()
    if not provider.get("ok"):
        return _json_error(
            f"OpenAI provider is not ready: {_friendly_error_message(provider.get('message', 'Unknown provider error.'))}",
            status_code=503,
        )
    final_prompt = _build_prompt(payload)
    app_root = app_root_for_idea(payload.prompt)
    try:
        run = create_run(
            user["id"],
            final_prompt,
            app_root=app_root,
            run_verification=payload.run_verification,
            auto_deploy=payload.auto_deploy,
        )
    except ValueError as exc:
        return _json_error(str(exc), status_code=403)
    append_run_log(run["id"], "info", "Run queued.")
    if payload.mode == "advanced":
        append_run_log(run["id"], "info", "Advanced brief attached to run prompt.")
    return JSONResponse(run, status_code=202)


@app.post("/api/runs/{run_id}/deploy")
async def deploy_run_api(run_id: str, request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    run = get_run(user["id"], run_id)
    if not run:
        return _json_error("Run not found.", status_code=404)
    if run.get("status") != "completed":
        return _json_error("Run has not completed successfully yet.")
    result = run.get("result") or {}
    if not result.get("tests_passed"):
        return _json_error("Cannot deploy a run that did not pass verification.")
    if result.get("deployed"):
        return {"ok": True, "message": "Run already deployed."}
    deploying_status = transition_status(run["status"], "deploying")
    update_run(run_id, status=deploying_status, error="")
    append_run_log(run_id, "info", "Manual deploy requested from control panel.")
    try:
        deploy_online(app_folder=run["app_root"])
        latest = get_run_by_id(run_id) or run
        latest_result = {**(latest.get("result") or {}), "deployed": True}
        replace_run_artifacts(run_id, artifact_summary(run["app_root"]))
        updated = update_run(run_id, status=transition_status(deploying_status, "completed"), result=latest_result, error="")
        append_run_log(run_id, "info", "Deploy completed successfully.")
        return {"ok": True, "run": updated}
    except Exception as exc:  # pragma: no cover
        append_run_log(run_id, "error", str(exc))
        update_run(run_id, status=transition_status(deploying_status, "failed"), error=str(exc))
        return _json_error(_friendly_error_message(str(exc)), status_code=500)
