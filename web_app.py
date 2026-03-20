import asyncio
from contextlib import asynccontextmanager
from html import escape
import json
from pathlib import Path
import shutil
import tempfile

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel

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
    get_job_for_run,
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
THEME_COOKIE = "sg_theme"

PROMPT_TEMPLATES = [
    {"label": "CRM", "prompt": "Build a CRM for managing leads, deals, tasks, and sales pipeline reviews."},
    {"label": "Booking", "prompt": "Build a booking platform for personal trainers with schedules, clients, and session tracking."},
    {"label": "Support", "prompt": "Build a support desk for tracking tickets, escalations, SLAs, and customer updates."},
    {"label": "Marketplace", "prompt": "Build a marketplace for fitness coaches to sell programs and manage buyer inquiries."},
]


class GenerateRequest(BaseModel):
    prompt: str
    run_verification: bool = True
    auto_deploy: bool = False
    mode: str = "starter"
    app_name: str = ""
    target_users: str = ""
    core_entities: str = ""
    core_workflows: str = ""


class AuthRequest(BaseModel):
    email: str
    password: str
    name: str | None = None


class SecretRequest(BaseModel):
    name: str
    value: str


@asynccontextmanager
async def app_lifespan(_app):
    init_db()
    yield


app = FastAPI(title="SaaS Generator Control Panel", lifespan=app_lifespan)


def _json_error(message, status_code=400):
    return JSONResponse({"error": message}, status_code=status_code)


def _current_user(request: Request):
    return get_user_by_session(request.cookies.get(SESSION_COOKIE))


def _theme_from_request(request: Request):
    return "dark" if request.cookies.get(THEME_COOKIE) == "dark" else "light"


def _theme_html_attrs(theme: str):
    if theme == "dark":
        return ' data-theme="dark" class="force-dark"', ' data-theme="dark" class="force-dark"'
    return ' data-theme="light"', ' data-theme="light"'


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


def _plain_status_label(status):
    labels = {
        "queued": "Getting ready",
        "running": "Building now",
        "deploying": "Publishing online",
        "completed": "Finished",
        "failed": "Needs attention",
    }
    return labels.get(str(status or "").lower(), "In progress")


def _run_stage_summary(run):
    logs = list_run_logs(run["user_id"], run["id"], limit=100) or []
    messages = " ".join(entry["message"].lower() for entry in logs)
    stages = [
        ("queued", "Queued"),
        ("planning", "Planning"),
        ("generating", "Generating"),
        ("validating", "Validating"),
        ("repairing", "Repairing"),
        ("deploying", "Deploying"),
        ("completed", "Completed"),
    ]
    current = "queued"
    if "starting generator pipeline" in messages:
        current = "planning"
    if run["status"] == "running":
        current = "generating"
    if "verification" in messages:
        current = "validating"
    if "repair" in messages:
        current = "repairing"
    if run["status"] == "deploying":
        current = "deploying"
    if run["status"] == "completed":
        current = "completed"
    if run["status"] == "failed" and current == "queued":
        current = "generating"

    found = False
    rows = []
    for key, label in stages:
        if not found:
            state = "done" if key != current else "current"
        else:
            state = "pending"
        if key == current:
            found = True
        if run["status"] == "failed" and key == current:
            state = "failed"
        rows.append({"key": key, "label": label, "state": state})
    return rows


def _current_stage_indicator(run):
    stages = _run_stage_summary(run)
    active = next((stage for stage in stages if stage["state"] in {"current", "failed"}), None)
    if active:
        return active
    if run.get("status") == "completed":
        return {"key": "completed", "label": "Completed", "state": "done"}
    return {"key": "queued", "label": "Queued", "state": "pending"}


def _stage_progress_percent(stage):
    order = {
        "queued": 8,
        "planning": 22,
        "generating": 40,
        "validating": 62,
        "repairing": 76,
        "deploying": 90,
        "completed": 100,
    }
    return order.get(stage.get("key"), 8)


def _run_payload(user_id, run_id):
    run = get_run(user_id, run_id)
    if not run:
        return None
    logs = list_run_logs(user_id, run_id, limit=200) or []
    artifacts = list_run_artifacts(user_id, run_id) or []
    return {
        **run,
        "friendly_error": _friendly_error_message(run.get("error")),
        "stages": _run_stage_summary(run),
        "current_stage": _current_stage_indicator(run),
        "logs": logs,
        "artifacts": artifacts,
    }


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
    html_attrs, body_attrs = _theme_html_attrs(theme)
    template = """<!doctype html>
<html lang="en"__HTML_ATTRS__><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>SaaS Generator Login</title>
<style>
:root { --ink:#111827; --muted:#5b6472; --line:rgba(15,23,42,0.08); --accent:#0f766e; --accent-deep:#115e59; --gold:#c89227; --card:rgba(255,255,255,0.76); --card-strong:rgba(255,255,255,0.92); --surface:#f4f7f6; --shadow:0 22px 60px rgba(15,23,42,0.10); color-scheme:light dark; }
* { box-sizing:border-box; }
body { margin:0; color:var(--ink); font-family:'Manrope','Avenir Next','Segoe UI',sans-serif; background:radial-gradient(circle at 8% 8%, rgba(15,118,110,0.12), transparent 24%), radial-gradient(circle at 92% 12%, rgba(200,146,39,0.10), transparent 18%), linear-gradient(180deg, #f8fbfa 0%, var(--surface) 44%, #eef2f1 100%); }
.shell { max-width:1080px; margin:0 auto; padding:34px 18px 64px; display:grid; gap:18px; }
.card { position:relative; overflow:hidden; background:var(--card); border:1px solid var(--line); border-radius:28px; padding:28px; box-shadow:var(--shadow); backdrop-filter:blur(18px); animation:riseIn .55s ease; }
.card::after { content:""; position:absolute; inset:auto -50px -70px auto; width:180px; height:180px; background:radial-gradient(circle, rgba(15,118,110,0.08), transparent 70%); pointer-events:none; }
.eyebrow { margin:0 0 10px; color:var(--accent); text-transform:uppercase; letter-spacing:0.16em; font-size:0.76rem; }
h1,h2,p { margin:0; position:relative; z-index:1; }
h1 { font-size:clamp(2.8rem,5vw,4.9rem); line-height:0.93; max-width:10ch; }
h2 { font-size:1.6rem; }
.lead { margin-top:12px; max-width:62ch; line-height:1.7; font-size:1.02rem; color:var(--muted); }
.hero-pills { display:flex; flex-wrap:wrap; gap:10px; margin-top:14px; position:relative; z-index:1; }
.hero-pill { display:inline-flex; align-items:center; gap:8px; border-radius:999px; padding:10px 14px; border:1px solid var(--line); background:var(--card-strong); font-size:0.9rem; box-shadow:inset 0 1px 0 rgba(255,255,255,0.55); }
.mini-icon { display:inline-flex; align-items:center; justify-content:center; width:20px; height:20px; border-radius:999px; background:rgba(15,118,110,0.10); color:var(--accent-deep); font-size:0.72rem; font-weight:700; }
.icon-chip { display:inline-flex; align-items:center; justify-content:center; width:34px; height:34px; margin-right:10px; border-radius:999px; background:rgba(15,118,110,0.10); border:1px solid var(--line); font-size:0.84rem; font-weight:700; color:var(--accent-deep); vertical-align:middle; }
.grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:18px; }
form { display:grid; gap:14px; position:relative; z-index:1; }
input { width:100%; border-radius:16px; border:1px solid var(--line); padding:14px; font:inherit; color:var(--ink); background:rgba(255,255,255,0.7); box-shadow:inset 0 1px 0 rgba(255,255,255,0.6); }
button { border:0; border-radius:999px; padding:13px 20px; font:inherit; font-weight:700; color:white; background:linear-gradient(135deg,var(--accent),var(--accent-deep)); cursor:pointer; box-shadow:0 14px 28px rgba(15,118,110,0.22); transition:transform .16s ease, box-shadow .16s ease, opacity .16s ease; }
button:hover { transform:translateY(-1px); box-shadow:0 18px 34px rgba(15,118,110,0.26); }
.error { display:none; border-radius:16px; padding:14px 16px; color:#b91c1c; background:#fee2e2; border:1px solid #fecaca; }
.hint { color:var(--muted); font-size:0.94rem; line-height:1.6; }
.stack-note { color:var(--muted); line-height:1.6; }
@keyframes riseIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
@media (prefers-color-scheme: dark) {
  :root { --ink:#edf2f7; --muted:#9aa6b2; --line:rgba(148,163,184,0.16); --accent:#2dd4bf; --accent-deep:#14b8a6; --gold:#f6c35b; --card:rgba(15,23,42,0.78); --card-strong:rgba(15,23,42,0.92); --surface:#08111f; --shadow:0 26px 70px rgba(2,6,23,0.45); }
  body { background:radial-gradient(circle at 12% 10%, rgba(45,212,191,0.12), transparent 26%), radial-gradient(circle at 88% 12%, rgba(246,195,91,0.08), transparent 18%), linear-gradient(180deg, #07111e 0%, #0b1424 52%, #111827 100%); }
  .card, .hero-pill, input { background:var(--card); }
  .hero-pill { box-shadow:none; }
  .mini-icon, .icon-chip { background:rgba(45,212,191,0.12); }
}
html[data-theme="dark"], [data-theme="dark"] { --ink:#edf2f7; --muted:#9aa6b2; --line:rgba(148,163,184,0.16); --accent:#2dd4bf; --accent-deep:#14b8a6; --gold:#f6c35b; --card:rgba(15,23,42,0.78); --card-strong:rgba(15,23,42,0.92); --surface:#08111f; --shadow:0 26px 70px rgba(2,6,23,0.45); }
body[data-theme="dark"] { background:radial-gradient(circle at 12% 10%, rgba(45,212,191,0.12), transparent 26%), radial-gradient(circle at 88% 12%, rgba(246,195,91,0.08), transparent 18%), linear-gradient(180deg, #07111e 0%, #0b1424 52%, #111827 100%); }
body[data-theme="dark"] .card, body[data-theme="dark"] .hero-pill, body[data-theme="dark"] input { background:var(--card); }
body[data-theme="dark"] .hero-pill { box-shadow:none; }
body[data-theme="dark"] .mini-icon, body[data-theme="dark"] .icon-chip { background:rgba(45,212,191,0.12); }
@media (max-width:640px) {
  .shell { padding:22px 14px 42px; gap:14px; }
  .card { padding:22px; border-radius:24px; }
  h1 { font-size:2.45rem; line-height:0.95; }
  h2 { font-size:1.4rem; }
  .hero-pills { gap:8px; }
  .hero-pill { width:100%; justify-content:flex-start; }
  .grid { grid-template-columns:1fr; }
}
.top-actions { display:flex; justify-content:flex-end; }
.theme-toggle { border:1px solid var(--line); border-radius:999px; padding:10px 14px; font:inherit; font-weight:700; color:var(--ink); background:var(--card-strong); box-shadow:none; }
.theme-toggle:hover { box-shadow:none; }
</style></head><body__BODY_ATTRS__>
<main class="shell">
<div class="top-actions"><a id="themeToggle" class="theme-toggle" href="/theme/toggle?next=/">__TOGGLE_LABEL__</a></div>
<section class="card"><p class="eyebrow">Get Started</p><h1>Describe your app idea.</h1><p class="lead">Turn an idea into a starter app, follow the progress, and download the result.</p><div class="hero-pills"><span class="hero-pill"><span class="mini-icon">1</span>Simple prompt</span><span class="hero-pill"><span class="mini-icon">2</span>Live progress</span><span class="hero-pill"><span class="mini-icon">3</span>Download your app</span></div></section>
<div id="errorBox" class="error"></div>
<section class="grid">
<section class="card"><p class="eyebrow">Login</p><h2><span class="icon-chip">→</span>Open your dashboard</h2><p class="stack-note">See your app ideas, progress, and downloads in one place.</p><form id="loginForm"><input id="loginEmail" type="email" placeholder="you@example.com" /><input id="loginPassword" type="password" placeholder="Password" /><button type="submit">Login</button></form></section>
<section class="card"><p class="eyebrow">Register</p><h2><span class="icon-chip">+</span>Create your account</h2><p class="stack-note">Save your app ideas and results under one account.</p><form id="registerForm"><input id="registerName" type="text" placeholder="Your name" /><input id="registerEmail" type="email" placeholder="you@example.com" /><input id="registerPassword" type="password" placeholder="Password" /><button type="submit">Register</button></form><p class="hint">Start with a simple prompt, or add a few extra details if you want more control.</p></section>
</section></main>
<script>
const errorBox = document.getElementById('errorBox');
function showError(message){ errorBox.style.display = message ? 'block' : 'none'; errorBox.textContent = message || ''; }
async function submitAuth(path, payload){ const response = await fetch(path,{ method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)}); const data = await response.json(); if(!response.ok){ showError(data.error || 'Authentication failed.'); return; } window.location.reload(); }
document.getElementById('loginForm').addEventListener('submit',(event)=>{ event.preventDefault(); submitAuth('/api/auth/login',{ email:document.getElementById('loginEmail').value, password:document.getElementById('loginPassword').value }); });
document.getElementById('registerForm').addEventListener('submit',(event)=>{ event.preventDefault(); submitAuth('/api/auth/register',{ name:document.getElementById('registerName').value, email:document.getElementById('registerEmail').value, password:document.getElementById('registerPassword').value }); });
</script></body></html>"""
    return (
        template.replace("__HTML_ATTRS__", html_attrs)
        .replace("__BODY_ATTRS__", body_attrs)
        .replace("__TOGGLE_LABEL__", "Light mode" if theme == "dark" else "Dark mode")
    )


def _render_run_card(run):
    result = run.get("result") or {}
    latest_error = _friendly_error_message(run.get("error") or result.get("latest_error") or "None")
    job = get_job_for_run(run["id"]) or {}
    status_label = _plain_status_label(run.get("status"))
    current_stage = _current_stage_indicator(run)
    stage_percent = _stage_progress_percent(current_stage)
    stage_markup = f"<div class='stage-track-wrap'><span class='stage-pill stage-{escape(current_stage['state'])}'>{escape(current_stage['label'] if current_stage['state'] != 'failed' else 'Failed')}</span><div class='stage-track'><span class='stage-fill stage-{escape(current_stage['state'])}' style='width:{stage_percent}%;'></span></div></div>"
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
    html_attrs, body_attrs = _theme_html_attrs(theme)
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
    template_markup = "".join(
        f"<button type='button' class='ghost-button template-button' data-template='{escape(template['prompt'])}' onclick=\"document.getElementById('prompt').value=this.dataset.template;document.getElementById('prompt').focus();\">{escape(template['label'])}</button>"
        for template in PROMPT_TEMPLATES
    )
    checklist_markup = "".join(
        f"<div class='check-row'><strong>{escape(item['label'])}</strong><span class='check-state {'ok' if item['ok'] else 'warn'}'>{'Ready' if item['ok'] else 'Needs attention'}</span><p>{escape(item['message'])}</p></div>"
        for item in checklist
    )
    onboarding_markup = ""
    if first_run:
        onboarding_markup = f"""
<section class="ops"><div class="panel"><p class="eyebrow">Before You Start</p><h3>Quick check</h3><div class="checklist">{checklist_markup}</div><p class="hint">Choose a template below, or open more options if you want more control.</p></div></section>
"""
    dashboard_script = """
<script>
const runList = document.getElementById('runList'); const errorBox = document.getElementById('errorBox'); const secretList = document.getElementById('secretList');
function showError(message) { errorBox.style.display = message ? 'block' : 'none'; errorBox.textContent = message || ''; }
function escapeHtml(value) { return String(value ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'", '&#39;'); }
function plainStatusLabel(status) {
  const labels = { queued:'Getting ready', running:'Building now', deploying:'Publishing online', completed:'Finished', failed:'Needs attention' };
  return labels[String(status || '').toLowerCase()] || 'In progress';
}
function statusIcon(status) {
  const icons = { queued:'○', running:'◔', deploying:'↗', completed:'✓', failed:'!' };
  return icons[String(status || '').toLowerCase()] || '•';
}
function currentStage(run) {
  const stages = run.stages || [];
  const active = stages.find((stage) => stage.state === 'current' || stage.state === 'failed');
  if (active) return active;
  if (String(run.status || '').toLowerCase() === 'completed') return { label: 'Completed', state: 'done' };
  return { label: 'Queued', state: 'pending' };
}
function stageProgress(stage) {
  const order = { queued:8, planning:22, generating:40, validating:62, repairing:76, deploying:90, completed:100 };
  return order[String(stage.key || '').toLowerCase()] || 8;
}
function renderRun(run) {
  const result = run.result || {}; const latestError = run.friendly_error || result.latest_error || 'None';
  const stage = currentStage(run);
  const stageLabel = stage.state === 'failed' ? 'Failed' : stage.label;
  const stageMarkup = `<div class="stage-track-wrap"><span class="stage-pill stage-${escapeHtml(stage.state)}">${escapeHtml(stageLabel)}</span><div class="stage-track"><span class="stage-fill stage-${escapeHtml(stage.state)}" style="width:${escapeHtml(stageProgress(stage))}%"></span></div></div>`;
  const deployButton = run.status === 'completed' && result.tests_passed && !result.deployed ? `<button class="secondary-button" data-deploy-run="${escapeHtml(run.id)}">Deploy App</button>` : '';
  return `<article class="run-card" data-run-id="${escapeHtml(run.id)}"><div class="run-header"><div><p class="eyebrow">App Request</p><h3>${escapeHtml(result.app_name || 'New App')}</h3></div><span class="status-pill status-${escapeHtml(run.status)}"><span class="status-icon">${escapeHtml(statusIcon(run.status))}</span>${escapeHtml(plainStatusLabel(run.status))}</span></div><p class="prompt-copy">${escapeHtml(run.prompt)}</p><div class="stage-row"><strong>Current step:</strong> ${stageMarkup}</div><div class="metric-grid"><div class="metric"><span>App type</span><strong>${escapeHtml(String(result.closest_family || 'in progress').replaceAll('_',' '))}</strong></div><div class="metric"><span>Status</span><strong>${escapeHtml(plainStatusLabel(run.status))}</strong></div><div class="metric"><span>Ready to download</span><strong>${result.saved_files_count ? 'Yes' : 'Not yet'}</strong></div><div class="metric"><span>Quality check</span><strong>${result.tests_passed ? 'Passed' : 'In progress'}</strong></div></div><div class="detail-grid"><div class="panel"><h4>Main parts</h4><p><strong>For:</strong> ${escapeHtml((result.primary_users || []).join(', ') || 'Still deciding')}</p><p><strong>Includes:</strong> ${escapeHtml((result.core_entities || []).join(', ') || 'Still deciding')}</p><p><strong>Key actions:</strong> ${escapeHtml((result.core_workflows || []).join(', ') || 'Still deciding')}</p></div><div class="panel"><h4>Progress</h4><p><strong>Quality check:</strong> ${result.tests_passed ? 'Passed' : 'Not finished yet'}</p><p><strong>Published online:</strong> ${result.deployed ? 'Yes' : 'No'}</p><p><strong>Need attention:</strong> ${escapeHtml(latestError)}</p></div></div><div class="button-row"><a class="ghost-link" href="/runs/${escapeHtml(run.id)}">Open details</a>${deployButton}</div></article>`;
}
function renderSecrets(secrets) { secretList.innerHTML = secrets.length ? secrets.map((secret) => `<div class="secret-row"><strong>${escapeHtml(secret.name)}</strong><span>${escapeHtml(secret.updated_at)}</span><button class="ghost-button" data-delete-secret="${escapeHtml(secret.name)}">Delete</button></div>`).join('') : "<p class='empty-state'>No saved account keys yet.</p>"; }
async function loadRuns() { const response = await fetch('/api/runs'); if (response.status === 401) { window.location.reload(); return; } const payload = await response.json(); runList.innerHTML = payload.runs.length ? payload.runs.map(renderRun).join('') : "<p class='empty-state'>Your apps will show up here after you start your first build.</p>"; }
async function loadSecrets() { const response = await fetch('/api/secrets'); const payload = await response.json(); if (!response.ok) { showError(payload.error || 'Unable to load secrets.'); return; } renderSecrets(payload.secrets); }
async function startRun(event) { event.preventDefault(); showError(''); const prompt = document.getElementById('prompt').value.trim(); if (!prompt) { showError('Prompt is required.'); return; } const advancedMode = document.getElementById('advancedMode').checked; const response = await fetch('/api/runs', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ prompt, run_verification:document.getElementById('runVerification').checked, auto_deploy:document.getElementById('autoDeploy').checked, mode: advancedMode ? 'advanced' : 'starter', app_name: document.getElementById('appName').value, target_users: document.getElementById('targetUsers').value, core_entities: document.getElementById('coreEntities').value, core_workflows: document.getElementById('coreWorkflows').value }) }); const payload = await response.json(); if (!response.ok) { showError(payload.error || 'Unable to queue run.'); return; } window.location.href = `/runs/${payload.id}`; }
async function deployRun(runId) { showError(''); const response = await fetch(`/api/runs/${runId}/deploy`, { method:'POST' }); const payload = await response.json(); if (!response.ok) { showError(payload.error || 'Unable to deploy app.'); return; } await loadRuns(); }
async function saveSecret(event) { event.preventDefault(); showError(''); const response = await fetch('/api/secrets', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ name:document.getElementById('secretName').value.trim(), value:document.getElementById('secretValue').value }) }); const payload = await response.json(); if (!response.ok) { showError(payload.error || 'Unable to store secret.'); return; } document.getElementById('secretName').value=''; document.getElementById('secretValue').value=''; await loadSecrets(); }
async function deleteSecretByName(name) { const response = await fetch(`/api/secrets/${encodeURIComponent(name)}`, { method:'DELETE' }); const payload = await response.json(); if (!response.ok) { showError(payload.error || 'Unable to delete secret.'); return; } await loadSecrets(); }
document.getElementById('generatorForm').addEventListener('submit', startRun);
document.getElementById('secretForm').addEventListener('submit', saveSecret);
document.getElementById('refreshRuns').addEventListener('click', loadRuns);
document.getElementById('logoutButton').addEventListener('click', async () => { await fetch('/api/auth/logout', { method:'POST' }); window.location.reload(); });
document.getElementById('advancedMode').addEventListener('change', (event) => { document.getElementById('advancedFields').classList.toggle('active', event.target.checked); });
const moreOptionsToggle = document.getElementById('moreOptionsToggle');
const moreOptionsPanel = document.getElementById('moreOptionsPanel');
if (moreOptionsToggle && moreOptionsPanel) {
  moreOptionsToggle.addEventListener('click', () => {
    const expanded = moreOptionsPanel.classList.toggle('visible');
    moreOptionsToggle.textContent = expanded ? 'Hide extra options' : 'More options';
  });
}
document.addEventListener('click', (event) => {
  const templateButton = event.target.closest('.template-button');
  if (templateButton) {
    event.preventDefault();
    const prompt = document.getElementById('prompt');
    prompt.value = templateButton.getAttribute('data-template') || '';
    prompt.focus();
  }
});
runList.addEventListener('click', (event) => { const deployButton = event.target.closest('[data-deploy-run]'); if (deployButton) { deployRun(deployButton.getAttribute('data-deploy-run')); } });
secretList.addEventListener('click', (event) => { const button = event.target.closest('[data-delete-secret]'); if (button) { deleteSecretByName(button.getAttribute('data-delete-secret')); } });
setInterval(loadRuns, 5000); setInterval(loadSecrets, 15000);
</script>"""
    return f"""<!doctype html>
<html lang="en"{html_attrs}><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>SaaS Generator Control Panel</title>
<style>
:root {{ --ink:#111827; --muted:#5b6472; --card:rgba(255,255,255,0.76); --card-strong:rgba(255,255,255,0.92); --line:rgba(15,23,42,0.08); --accent:#0f766e; --accent-deep:#115e59; --warn:#8a5b10; --danger:#b91c1c; --ok:#166534; --gold:#c89227; --shadow:0 22px 60px rgba(15,23,42,0.10); color-scheme:light dark; }}
* {{ box-sizing:border-box; }} body {{ margin:0; color:var(--ink); font-family:'Manrope','Avenir Next','Segoe UI',sans-serif; background:radial-gradient(circle at 8% 6%, rgba(15,118,110,0.12), transparent 22%), radial-gradient(circle at 92% 14%, rgba(200,146,39,0.10), transparent 18%), linear-gradient(180deg, #f8fbfa 0%, #f1f5f4 46%, #eceff0 100%); }}
.shell {{ max-width:1240px; margin:0 auto; padding:28px 18px 64px; display:grid; gap:18px; }} .hero,.composer,.history,.ops {{ position:relative; overflow:hidden; background:var(--card); border:1px solid var(--line); border-radius:28px; padding:24px; box-shadow:var(--shadow); backdrop-filter:blur(18px); animation:riseIn .55s ease; }}
.hero::after,.composer::after,.history::after,.ops::after {{ content:""; position:absolute; inset:auto -50px -70px auto; width:220px; height:220px; background:radial-gradient(circle, rgba(15,118,110,0.08), transparent 70%); pointer-events:none; }}
.eyebrow {{ margin:0 0 10px; color:var(--accent); text-transform:uppercase; letter-spacing:0.16em; font-size:0.76rem; }} h1,h2,h3,h4,p {{ margin:0; position:relative; z-index:1; }} h1 {{ font-size:clamp(2.8rem,5vw,5rem); line-height:0.9; max-width:10ch; }} .lead {{ margin-top:12px; max-width:68ch; line-height:1.7; font-size:1.02rem; color:var(--muted); }}
.topbar {{ display:flex; justify-content:space-between; gap:18px; align-items:start; }} .user-chip {{ border-radius:999px; padding:10px 14px; background:var(--card-strong); border:1px solid var(--line); box-shadow:inset 0 1px 0 rgba(255,255,255,0.5); }}
.hero-badges {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:16px; position:relative; z-index:1; }} .hero-badge {{ display:inline-flex; align-items:center; gap:8px; border-radius:999px; padding:10px 14px; background:var(--card-strong); border:1px solid var(--line); font-size:0.9rem; box-shadow:inset 0 1px 0 rgba(255,255,255,0.45); }} .hero-badge .mini-icon {{ display:inline-flex; align-items:center; justify-content:center; width:20px; height:20px; border-radius:999px; background:rgba(15,118,110,0.10); color:var(--accent-deep); font-size:0.7rem; font-weight:700; }}
.panel {{ border:1px solid var(--line); border-radius:24px; padding:18px; background:linear-gradient(180deg, var(--card-strong), rgba(255,255,255,0.62)); }}
.composer {{ max-width:980px; margin:0 auto; width:100%; }}
.composer form, .secret-form {{ display:grid; gap:16px; position:relative; z-index:1; }} textarea,input {{ width:100%; border-radius:18px; border:1px solid var(--line); padding:18px; font:inherit; font-size:1rem; color:var(--ink); background:rgba(255,255,255,0.68); resize:vertical; box-shadow:inset 0 1px 0 rgba(255,255,255,0.55); }}
textarea {{ min-height:180px; }}
.controls,.button-row,.secret-row,.stage-row,.template-row {{ display:flex; gap:12px; flex-wrap:wrap; align-items:center; }} .controls label {{ display:flex; gap:10px; align-items:center; font-size:0.96rem; background:var(--card-strong); border:1px solid var(--line); border-radius:999px; padding:8px 12px; }}
button {{ border:0; border-radius:999px; padding:14px 22px; font:inherit; font-weight:700; color:white; background:linear-gradient(135deg,var(--accent),var(--accent-deep)); cursor:pointer; box-shadow:0 14px 30px rgba(15,118,110,0.22); }}
.controls button,.button-row button,.ghost-link,.ghost-button,.secondary-button {{ transition:transform .16s ease, box-shadow .16s ease, opacity .16s ease; }}
.controls button:hover,.button-row button:hover,.ghost-link:hover,.ghost-button:hover,.secondary-button:hover {{ transform:translateY(-1px); }}
.secondary-button {{ color:#7c4a00; background:linear-gradient(135deg, #f8ddb2, #e9b755); }} .ghost-button {{ background:linear-gradient(135deg, #1f2937, #111827); }} .ghost-link {{ display:inline-flex; align-items:center; justify-content:center; border-radius:999px; padding:13px 20px; font-weight:700; color:white; text-decoration:none; background:linear-gradient(135deg, #1f2937, #111827); }} .hint {{ color:var(--muted); font-size:0.94rem; line-height:1.7; }}
.composer-main {{ display:grid; gap:14px; }}
.more-toggle-row {{ display:flex; justify-content:flex-start; }}
.more-options {{ display:none; gap:16px; margin-top:4px; }}
.more-options.visible {{ display:grid; }}
.quiet-grid {{ display:grid; gap:14px; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); }}
.mini-panel {{ border:1px solid var(--line); border-radius:22px; padding:16px; background:var(--card-strong); }}
.error {{ display:none; border-radius:16px; padding:14px 16px; color:var(--danger); background:#fee2e2; border:1px solid #fecaca; }} .history-header,.run-header {{ display:flex; justify-content:space-between; gap:16px; align-items:start; }} .history-header {{ margin-bottom:18px; }}
.run-list {{ display:grid; gap:16px; }} .run-card {{ border-radius:24px; border:1px solid var(--line); padding:22px; background:linear-gradient(180deg, var(--card-strong), rgba(255,255,255,0.58)); box-shadow:0 16px 34px rgba(15,23,42,0.06); }}
.status-pill {{ border-radius:999px; padding:8px 12px; font-size:0.82rem; font-weight:700; text-transform:capitalize; display:inline-flex; align-items:center; gap:8px; }} .status-icon {{ display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px; border-radius:999px; background:rgba(255,255,255,0.55); font-size:0.72rem; }} .status-queued {{ background:#e0f2fe; color:#0c4a6e; }} .status-running,.status-deploying {{ background:#fef3c7; color:var(--warn); }} .status-completed {{ background:#dcfce7; color:var(--ok); }} .status-failed {{ background:#fee2e2; color:var(--danger); }}
.stage-track-wrap {{ min-width:220px; display:grid; gap:8px; }} .stage-pill {{ border-radius:999px; padding:6px 10px; font-size:0.76rem; font-weight:700; background:#e2e8f0; color:#475569; width:max-content; }} .stage-track {{ width:100%; height:7px; border-radius:999px; background:rgba(148,163,184,0.18); overflow:hidden; }} .stage-fill {{ display:block; height:100%; border-radius:999px; background:linear-gradient(90deg, var(--accent), var(--accent-deep)); transition:width .25s ease; }} .stage-done {{ background:#dcfce7; color:#166534; }} .stage-current {{ background:#dbeafe; color:#1d4ed8; }} .stage-failed {{ background:#fee2e2; color:#b91c1c; }} .stage-pending {{ background:#e2e8f0; color:#64748b; }} .stage-fill.stage-failed {{ background:linear-gradient(90deg, #ef4444, #b91c1c); }} .stage-fill.stage-done {{ background:linear-gradient(90deg, #22c55e, #15803d); }}
.prompt-copy {{ margin:12px 0 14px; line-height:1.6; color:#334155; }} .metric-grid,.detail-grid,.ops-grid {{ display:grid; gap:12px; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); }} .metric-grid {{ margin-bottom:14px; }}
.metric {{ border-radius:20px; padding:14px; background:var(--card-strong); border:1px solid var(--line); }} .metric span {{ display:block; font-size:0.76rem; letter-spacing:0.12em; text-transform:uppercase; color:var(--muted); margin-bottom:8px; }}
.empty-state {{ color:var(--muted); font-size:1rem; }} .secret-row {{ justify-content:space-between; padding:12px 0; border-bottom:1px solid var(--line); }} .checklist {{ display:grid; gap:14px; }} .check-row {{ border-radius:18px; padding:14px; border:1px solid var(--line); background:var(--card-strong); }} .check-row p {{ margin-top:8px; color:var(--muted); }} .check-state {{ display:inline-flex; margin-left:10px; font-weight:700; }} .check-state.ok {{ color:#166534; }} .check-state.warn {{ color:#b45309; }} .advanced-fields {{ display:none; gap:12px; }} .advanced-fields.active {{ display:grid; }}
@keyframes riseIn {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:translateY(0); }} }}
@media (prefers-color-scheme: dark) {{ :root {{ --ink:#edf2f7; --muted:#97a5b4; --card:rgba(15,23,42,0.78); --card-strong:rgba(15,23,42,0.92); --line:rgba(148,163,184,0.16); --accent:#2dd4bf; --accent-deep:#14b8a6; --warn:#f5c96a; --ok:#4ade80; --gold:#f6c35b; --shadow:0 28px 80px rgba(2,6,23,0.45); }} body {{ background:radial-gradient(circle at 8% 6%, rgba(45,212,191,0.12), transparent 22%), radial-gradient(circle at 92% 14%, rgba(246,195,91,0.08), transparent 18%), linear-gradient(180deg, #07111e 0%, #0b1424 46%, #111827 100%); }} .panel,.mini-panel,.metric,.check-row,.hero-badge,.user-chip,.controls label,textarea,input {{ background:var(--card-strong); }} .run-card {{ background:linear-gradient(180deg, var(--card-strong), rgba(15,23,42,0.82)); }} .status-icon {{ background:rgba(255,255,255,0.08); }} }}
html[data-theme="dark"], [data-theme="dark"], html.force-dark {{ --ink:#edf2f7; --muted:#97a5b4; --card:rgba(15,23,42,0.78); --card-strong:rgba(15,23,42,0.92); --line:rgba(148,163,184,0.16); --accent:#2dd4bf; --accent-deep:#14b8a6; --warn:#f5c96a; --ok:#4ade80; --gold:#f6c35b; --shadow:0 28px 80px rgba(2,6,23,0.45); }}
body[data-theme="dark"] {{ background:radial-gradient(circle at 8% 6%, rgba(45,212,191,0.12), transparent 22%), radial-gradient(circle at 92% 14%, rgba(246,195,91,0.08), transparent 18%), linear-gradient(180deg, #07111e 0%, #0b1424 46%, #111827 100%); }}
body.force-dark {{ background:radial-gradient(circle at 8% 6%, rgba(45,212,191,0.12), transparent 22%), radial-gradient(circle at 92% 14%, rgba(246,195,91,0.08), transparent 18%), linear-gradient(180deg, #07111e 0%, #0b1424 46%, #111827 100%); }}
body[data-theme="dark"] .panel,body[data-theme="dark"] .mini-panel,body[data-theme="dark"] .metric,body[data-theme="dark"] .check-row,body[data-theme="dark"] .hero-badge,body[data-theme="dark"] .user-chip,body[data-theme="dark"] .controls label,body[data-theme="dark"] textarea,body[data-theme="dark"] input {{ background:var(--card-strong); }}
body.force-dark .panel,body.force-dark .mini-panel,body.force-dark .metric,body.force-dark .check-row,body.force-dark .hero-badge,body.force-dark .user-chip,body.force-dark .controls label,body.force-dark textarea,body.force-dark input {{ background:var(--card-strong); }}
body[data-theme="dark"] .run-card {{ background:linear-gradient(180deg, var(--card-strong), rgba(15,23,42,0.82)); }}
body.force-dark .run-card {{ background:linear-gradient(180deg, var(--card-strong), rgba(15,23,42,0.82)); }}
body[data-theme="dark"] .status-icon {{ background:rgba(255,255,255,0.08); }} body[data-theme="dark"] .stage-track {{ background:rgba(148,163,184,0.18); }}
body.force-dark .status-icon {{ background:rgba(255,255,255,0.08); }} body.force-dark .stage-track {{ background:rgba(148,163,184,0.18); }}
@media (max-width:860px) {{ .topbar,.history-header,.run-header {{ flex-direction:column; }} h1 {{ max-width:none; }} .hero,.composer,.history,.ops {{ padding:20px; border-radius:26px; }} .metric-grid,.detail-grid,.ops-grid,.quiet-grid {{ grid-template-columns:1fr; }} .template-row {{ display:grid; grid-template-columns:1fr; }} .template-button,.ghost-link,.secondary-button,button {{ width:100%; justify-content:center; }} .controls {{ align-items:stretch; }} .controls label {{ width:100%; justify-content:flex-start; }} .hero-badges {{ gap:8px; }} .hero-badge {{ width:100%; justify-content:flex-start; }} .user-chip {{ width:100%; text-align:center; }} }}
.theme-toggle {{ position:relative; z-index:5; pointer-events:auto; border:1px solid var(--line); border-radius:999px; padding:12px 16px; font:inherit; font-weight:700; color:var(--ink); background:var(--card-strong); box-shadow:none; }}
.theme-toggle:hover {{ box-shadow:none; }}
</style></head><body{body_attrs}>
<main class="shell">
<section class="hero"><div class="topbar"><div><p class="eyebrow">Your App Builder</p><h1>Turn an idea into a starter app.</h1><p class="lead">Write what you want to build, follow the progress, and download the result when it is ready.</p><div class="hero-badges"><span class="hero-badge"><span class="mini-icon">1</span>Describe your idea</span><span class="hero-badge"><span class="mini-icon">2</span>Watch it build</span><span class="hero-badge"><span class="mini-icon">3</span>Download the result</span></div></div><div class="controls"><a id="themeToggle" class="theme-toggle" href="/theme/toggle?next=/">{'Light mode' if theme == 'dark' else 'Dark mode'}</a><span class="user-chip">{escape(user['name'])}</span><a class="ghost-link" href="/settings">Settings</a><button id="logoutButton" class="ghost-button" type="button">Logout</button></div></div></section>
{onboarding_markup}
<section class="composer"><div id="errorBox" class="error"></div><form id="generatorForm"><div class="composer-main"><p class="eyebrow">Start Here</p><h2>What would you like to build?</h2><textarea id="prompt" name="prompt" placeholder="Example: Build a booking app for personal trainers with client profiles, session scheduling, and payments."></textarea><div class="template-row">{template_markup}</div><div class="controls"><button type="submit">Build my app</button></div><div class="more-toggle-row"><button id="moreOptionsToggle" class="secondary-button" type="button">More options</button></div><div id="moreOptionsPanel" class="more-options"><div class="quiet-grid"><div class="mini-panel"><div class="controls"><label><input id="runVerification" type="checkbox" checked /> Check the app before finishing</label><label><input id="autoDeploy" type="checkbox" /> Publish online after it works</label><label><input id="advancedMode" type="checkbox" /> Add more details</label></div><div id="advancedFields" class="advanced-fields"><input id="appName" placeholder="App name" /><input id="targetUsers" placeholder="Who will use it?" /><input id="coreEntities" placeholder="Important things in the app" /><input id="coreWorkflows" placeholder="Main actions people take" /></div></div><div class="mini-panel"><p><strong>Builds left this month:</strong> {usage.get('remaining_runs', 0)}</p><p><strong>AI connection:</strong> {escape(provider_status.get('status', 'unknown'))}</p></div></div><div class="mini-panel"><p class="eyebrow">Connected Accounts</p><h3>Save keys for publishing later</h3><form id="secretForm" class="secret-form"><input id="secretName" placeholder="Account name" /><input id="secretValue" placeholder="Key or password" type="password" /><div class="controls"><button type="submit">Save</button></div></form><div id="secretList">{secret_markup}</div></div></div><p class="hint">You have used <strong>{usage.get('monthly_run_usage', 0)}</strong> of <strong>{usage.get('monthly_run_limit', 0)}</strong> app builds this month.</p></div></form></section>
<section class="history"><div class="history-header"><div><p class="eyebrow">Your Apps</p><h2>Recent app builds</h2></div><div class="controls"><a class="ghost-link" href="/settings">Settings</a><button id="refreshRuns" class="secondary-button" type="button">Refresh</button></div></div><div id="runList" class="run-list">{history_markup}</div></section>
</main>
</main>""" + dashboard_script + """</body></html>"""


def _render_settings_page(user, theme="light"):
    html_attrs, body_attrs = _theme_html_attrs(theme)
    usage = get_usage_summary(user["id"]) or {}
    provider = check_openai_generation_access()
    secrets = list_secrets(user["id"])
    secret_markup = "".join(
        f"<li><strong>{escape(secret['name'])}</strong> · updated {escape(secret['updated_at'])}</li>"
        for secret in secrets
    ) or "<li>No stored secrets yet.</li>"
    return f"""<!doctype html>
<html lang="en"{html_attrs}><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Settings</title><style>
body {{ margin:0; font-family:'Manrope','Avenir Next','Segoe UI',sans-serif; background:radial-gradient(circle at top left, rgba(15,118,110,0.12), transparent 22%), linear-gradient(180deg, #f7fbf8 0%, #edf4f1 46%, #eef0ef 100%); color:#111827; }}
.shell {{ max-width:1020px; margin:0 auto; padding:28px 18px 60px; display:grid; gap:16px; }}
.card {{ position:relative; overflow:hidden; background:rgba(255,255,255,0.78); border:1px solid rgba(15,23,42,0.08); border-radius:28px; padding:24px; box-shadow:0 20px 52px rgba(15,23,42,0.10); backdrop-filter:blur(18px); }}
.card::after {{ content:""; position:absolute; inset:auto -40px -60px auto; width:180px; height:180px; background:radial-gradient(circle, rgba(15,118,110,0.08), transparent 70%); }}
.button {{ display:inline-flex; align-items:center; gap:8px; text-decoration:none; color:white; background:linear-gradient(135deg,#0f766e,#115e59); border-radius:999px; padding:12px 18px; font-weight:700; }}
h1,h2,p {{ margin:0; position:relative; z-index:1; }} .hero-copy {{ display:grid; gap:10px; }} .subgrid {{ display:grid; gap:16px; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); }}
.stat {{ border:1px solid rgba(15,23,42,0.08); border-radius:20px; padding:16px; background:rgba(255,255,255,0.9); position:relative; z-index:1; }}
ul {{ padding-left:18px; margin:0; }}
@media (prefers-color-scheme: dark) {{ body {{ background:radial-gradient(circle at top left, rgba(45,212,191,0.12), transparent 22%), linear-gradient(180deg, #07111e 0%, #0b1424 46%, #111827 100%); color:#edf2f7; }} .card,.stat {{ background:rgba(15,23,42,0.84); border-color:rgba(148,163,184,0.16); }} }}
html[data-theme="dark"], [data-theme="dark"] {{ color:#edf2f7; }}
body[data-theme="dark"] {{ background:radial-gradient(circle at top left, rgba(45,212,191,0.12), transparent 22%), linear-gradient(180deg, #07111e 0%, #0b1424 46%, #111827 100%); color:#edf2f7; }}
body[data-theme="dark"] .card,body[data-theme="dark"] .stat {{ background:rgba(15,23,42,0.84); border-color:rgba(148,163,184,0.16); }}
@media (max-width:680px) {{ .shell {{ padding:22px 14px 42px; }} .card {{ padding:20px; border-radius:24px; }} .subgrid {{ grid-template-columns:1fr; }} .button {{ width:100%; justify-content:center; }} }}
.theme-toggle {{ border:1px solid rgba(15,23,42,0.08); border-radius:999px; padding:12px 16px; font:inherit; font-weight:700; color:inherit; background:rgba(255,255,255,0.9); }}
</style></head><body{body_attrs}><main class="shell">
<section class="card hero-copy"><div class="subgrid"><a class="button" href="/"><span>←</span><span>Back to Dashboard</span></a><a id="themeToggle" class="theme-toggle" href="/theme/toggle?next=/settings">{'Light mode' if theme == 'dark' else 'Dark mode'}</a></div><h1>Settings</h1><p>Check whether app building is ready, see how many builds you have left, and manage saved account keys.</p></section>
<section class="subgrid"><section class="card"><h2>○ AI Connection</h2><div class="stat"><p><strong>Status:</strong> {escape(provider.get('status', 'unknown'))}</p><p><strong>Message:</strong> {escape(provider.get('message', ''))}</p></div></section><section class="card"><h2>◔ Usage</h2><div class="stat"><p><strong>Plan:</strong> {escape(usage.get('plan', 'free'))}</p><p><strong>Builds left:</strong> {usage.get('remaining_runs', 0)}</p></div></section></section>
<section class="card"><h2>□ Saved account keys</h2><ul>{secret_markup}</ul></section>
</main></body></html>"""


def _render_run_detail_page(user, run, theme="light"):
    html_attrs, body_attrs = _theme_html_attrs(theme)
    payload = _run_payload(user["id"], run["id"]) or {}
    result = payload.get("result") or {}
    logs = payload.get("logs") or []
    artifacts = payload.get("artifacts") or []
    current_stage = payload.get("current_stage") or _current_stage_indicator(run)
    stage_label = current_stage["label"] if current_stage["state"] != "failed" else "Failed"
    stage_percent = _stage_progress_percent(current_stage)
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
    return f"""<!doctype html>
<html lang="en"{html_attrs}><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Run Details</title><style>
body {{ margin:0; font-family:'Manrope','Avenir Next','Segoe UI',sans-serif; background:radial-gradient(circle at top left, rgba(15,118,110,0.12), transparent 22%), radial-gradient(circle at 94% 10%, rgba(200,146,39,0.10), transparent 18%), linear-gradient(180deg, #f7fbf8 0%, #edf4f1 46%, #eef0ef 100%); color:#111827; }}
.shell {{ max-width:1120px; margin:0 auto; padding:28px 18px 64px; display:grid; gap:16px; }}
.card {{ position:relative; overflow:hidden; background:rgba(255,255,255,0.78); border:1px solid rgba(15,23,42,0.08); border-radius:28px; padding:24px; box-shadow:0 20px 52px rgba(15,23,42,0.10); backdrop-filter:blur(18px); }}
.card::after {{ content:""; position:absolute; inset:auto -40px -60px auto; width:180px; height:180px; background:radial-gradient(circle, rgba(15,118,110,0.08), transparent 70%); }}
.actions {{ display:flex; gap:12px; flex-wrap:wrap; }}
.button {{ display:inline-flex; align-items:center; gap:8px; text-decoration:none; color:white; background:linear-gradient(135deg,#0f766e,#115e59); border-radius:999px; padding:12px 18px; font-weight:700; border:0; }}
.secondary {{ background:linear-gradient(135deg,#f5d58d,#e89d2f); color:#7b4f06; }}
.outcome-banner {{ display:grid; gap:10px; }}
.outcome-ready {{ border-color:#b7e2c5; background:linear-gradient(180deg, rgba(237,255,244,0.96), rgba(255,255,255,0.92)); }}
.outcome-failed {{ border-color:#f4caca; background:linear-gradient(180deg, rgba(255,241,241,0.96), rgba(255,255,255,0.92)); }}
.outcome-progress {{ border-color:#c8ddf4; background:linear-gradient(180deg, rgba(240,248,255,0.96), rgba(255,255,255,0.92)); }}
.summary-grid {{ display:grid; gap:16px; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); }}
.summary-card {{ border-radius:20px; border:1px solid rgba(15,23,42,0.08); padding:16px; background:rgba(255,255,255,0.9); position:relative; z-index:1; }}
.stage-track-wrap {{ min-width:220px; display:grid; gap:8px; }} .stage-pill {{ border-radius:999px; padding:6px 10px; font-size:0.76rem; font-weight:700; background:#e2e8f0; color:#475569; width:max-content; }} .stage-track {{ width:100%; height:7px; border-radius:999px; background:rgba(148,163,184,0.18); overflow:hidden; }} .stage-fill {{ display:block; height:100%; border-radius:999px; background:linear-gradient(90deg, #0f766e, #115e59); transition:width .25s ease; }} .stage-done {{ background:#dcfce7; color:#166534; }} .stage-current {{ background:#dbeafe; color:#1d4ed8; }} .stage-failed {{ background:#fee2e2; color:#b91c1c; }} .stage-pending {{ background:#e2e8f0; color:#64748b; }} .stage-fill.stage-failed {{ background:linear-gradient(90deg, #ef4444, #b91c1c); }} .stage-fill.stage-done {{ background:linear-gradient(90deg, #22c55e, #15803d); }}
pre {{ white-space:pre-wrap; background:#0f172a; color:#e2e8f0; border-radius:18px; padding:18px; overflow:auto; }}
ul {{ padding-left:18px; margin:0; position:relative; z-index:1; }} h1,h2,p {{ margin:0; position:relative; z-index:1; }}
@media (prefers-color-scheme: dark) {{ body {{ background:radial-gradient(circle at top left, rgba(45,212,191,0.12), transparent 22%), radial-gradient(circle at 94% 10%, rgba(246,195,91,0.08), transparent 18%), linear-gradient(180deg, #07111e 0%, #0b1424 46%, #111827 100%); color:#edf2f7; }} .card,.summary-card {{ background:rgba(15,23,42,0.84); border-color:rgba(148,163,184,0.16); }} }}
html[data-theme="dark"], [data-theme="dark"] {{ color:#edf2f7; }}
body[data-theme="dark"] {{ background:radial-gradient(circle at top left, rgba(45,212,191,0.12), transparent 22%), radial-gradient(circle at 94% 10%, rgba(246,195,91,0.08), transparent 18%), linear-gradient(180deg, #07111e 0%, #0b1424 46%, #111827 100%); color:#edf2f7; }}
body[data-theme="dark"] .card,body[data-theme="dark"] .summary-card {{ background:rgba(15,23,42,0.84); border-color:rgba(148,163,184,0.16); }} body[data-theme="dark"] .stage-track {{ background:rgba(148,163,184,0.18); }}
@media (max-width:680px) {{ .shell {{ padding:22px 14px 42px; }} .card {{ padding:20px; border-radius:24px; }} .summary-grid {{ grid-template-columns:1fr; }} .actions {{ display:grid; }} .button {{ width:100%; justify-content:center; }} }}
</style></head><body{body_attrs}><main class="shell">
<section class="card outcome-banner {outcome_class}"><div class="actions"><a class="button" href="/"><span>←</span><span>Back to Dashboard</span></a><a class="button secondary" href="/api/runs/{escape(run['id'])}/download"><span>↓</span><span>Download app</span></a><a class="button" href="/settings"><span>○</span><span>Settings</span></a><a id="themeToggle" class="button" href="/theme/toggle?next=/runs/{escape(run['id'])}"><span>◐</span><span>{'Light mode' if theme == 'dark' else 'Dark mode'}</span></a></div><h1 id="runTitle">{escape(result.get('app_name', 'App details'))}</h1><h2 id="outcomeTitle">{escape(outcome_title)}</h2><p id="outcomeText">{escape(outcome_text)}</p></section>
<section class="card"><h2>□ Summary</h2><div class="summary-grid"><div class="summary-card"><p><strong>App type:</strong> <span id="runFamily">{escape(result.get('closest_family', 'pending').replace('_', ' '))}</span></p></div><div class="summary-card"><p><strong>Build confidence:</strong> <span id="runSupport">{escape(result.get('support_tier', 'pending'))}</span></p></div><div class="summary-card"><p><strong>Quality check:</strong> <span id="runVerification">{'Passed' if result.get('tests_passed') else 'Not passed'}</span></p></div><div class="summary-card"><p><strong>Published online:</strong> <span id="runDeployed">{'Yes' if result.get('deployed') else 'No'}</span></p></div></div></section>
<section class="card"><h2>◔ Progress</h2><p><strong>Status:</strong> <span id="runStatus">{escape(_plain_status_label(run['status']))}</span></p><p><strong>Current step:</strong> <span id="stageTimeline">{stage_markup}</span></p><p><strong>Your idea:</strong> <span id="runPrompt">{escape(run['prompt'])}</span></p><p><strong>Need attention:</strong> <span id="runError">{escape(_friendly_error_message(run.get('error') or result.get('latest_error') or 'None'))}</span></p></section>
<section class="card"><h2>↓ Files</h2><ul id="artifactList">{artifact_markup}</ul></section>
<section class="card"><h2>≡ Logs</h2><pre id="logOutput">{escape(log_text)}</pre></section>
</main>
<script>
const runStream = new EventSource('/api/runs/{escape(run["id"])}/stream');
function escapeHtml(value) {{ return String(value ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'", '&#39;'); }}
function currentStage(payload) {{
  const stages = payload.stages || [];
  const active = stages.find((stage) => stage.state === 'current' || stage.state === 'failed');
  if (active) return active;
  if (String(payload.status || '').toLowerCase() === 'completed') return {{ label: 'Completed', state: 'done' }};
  return {{ label: 'Queued', state: 'pending' }};
}}
function stageProgress(stage) {{
  const order = {{ queued:8, planning:22, generating:40, validating:62, repairing:76, deploying:90, completed:100 }};
  return order[String(stage.key || '').toLowerCase()] || 8;
}}
runStream.onmessage = (event) => {{
  const payload = JSON.parse(event.data);
  const result = payload.result || {{}};
  document.getElementById('runTitle').textContent = result.app_name || 'Run Details';
  document.getElementById('runStatus').textContent = plainStatusLabel(payload.status);
  document.getElementById('runPrompt').textContent = payload.prompt || '';
  document.getElementById('runError').textContent = payload.friendly_error || 'None';
  document.getElementById('runFamily').textContent = result.closest_family || 'pending';
  document.getElementById('runSupport').textContent = result.support_tier || 'pending';
  document.getElementById('runVerification').textContent = result.tests_passed ? 'Passed' : 'Not passed';
  document.getElementById('runDeployed').textContent = result.deployed ? 'Yes' : 'No';
  const outcomeTitle = document.getElementById('outcomeTitle');
  const outcomeText = document.getElementById('outcomeText');
  const banner = document.querySelector('.outcome-banner');
  if (payload.status === 'completed' && result.tests_passed) {{
    outcomeTitle.textContent = 'Your app is ready';
    outcomeText.textContent = 'The build finished and the quality check passed. You can download it now.';
    banner.classList.remove('outcome-progress', 'outcome-failed');
    banner.classList.add('outcome-ready');
  }} else if (payload.status === 'failed') {{
    outcomeTitle.textContent = 'This build needs attention';
    outcomeText.textContent = payload.friendly_error || 'Something went wrong during the build.';
    banner.classList.remove('outcome-progress', 'outcome-ready');
    banner.classList.add('outcome-failed');
  }} else {{
    outcomeTitle.textContent = 'Your app is being built';
    outcomeText.textContent = 'Stay on this page to watch the progress update live.';
    banner.classList.remove('outcome-ready', 'outcome-failed');
    banner.classList.add('outcome-progress');
  }}
  const stage = currentStage(payload);
  document.getElementById('stageTimeline').innerHTML = `<div class="stage-track-wrap"><span class="stage-pill stage-${{escapeHtml(stage.state)}}">${{escapeHtml(stage.state === 'failed' ? 'Failed' : stage.label)}}</span><div class="stage-track"><span class="stage-fill stage-${{escapeHtml(stage.state)}}" style="width:${{escapeHtml(stageProgress(stage))}}%"></span></div></div>`;
  document.getElementById('artifactList').innerHTML = (payload.artifacts || []).map((item) => `<li><strong>${{escapeHtml(item.label)}}</strong><br />${{escapeHtml(item.path)}}</li>`).join('') || '<li>No artifacts yet.</li>';
  document.getElementById('logOutput').textContent = (payload.logs || []).map((entry) => `[${{entry.created_at}}] ${{String(entry.level || '').toUpperCase()}}: ${{entry.message}}`).join('\\n') || 'No logs yet.';
  if (payload.status === 'completed' || payload.status === 'failed') {{
    runStream.close();
  }}
}};
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = _current_user(request)
    theme = _theme_from_request(request)
    if not user:
        return _render_auth_page(theme)
    return _render_dashboard(user, theme)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user = _current_user(request)
    theme = _theme_from_request(request)
    if not user:
        return _render_auth_page(theme)
    return _render_settings_page(user, theme)


@app.get("/runs/{run_id}", response_class=HTMLResponse)
async def run_detail_page(run_id: str, request: Request):
    user = _current_user(request)
    theme = _theme_from_request(request)
    if not user:
        return _render_auth_page(theme)
    run = get_run(user["id"], run_id)
    if not run:
        return HTMLResponse("Run not found.", status_code=404)
    return _render_run_detail_page(user, run, theme)


@app.get("/theme/toggle")
async def toggle_theme(request: Request, next: str = "/"):
    current = _theme_from_request(request)
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
        "runs": [{**run, "friendly_error": _friendly_error_message(run.get("error")), "stages": _run_stage_summary(run)} for run in runs]
    }


@app.get("/api/runs/{run_id}")
async def get_run_status(run_id: str, request: Request):
    user = _current_user(request)
    if not user:
        return _json_error("Unauthorized.", status_code=401)
    run = get_run(user["id"], run_id)
    if not run:
        return _json_error("Run not found.", status_code=404)
    return {**run, "friendly_error": _friendly_error_message(run.get("error")), "stages": _run_stage_summary(run)}


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
    update_run(run_id, status="deploying", error="")
    append_run_log(run_id, "info", "Manual deploy requested from control panel.")
    try:
        deploy_online(app_folder=run["app_root"])
        latest = get_run_by_id(run_id) or run
        latest_result = {**(latest.get("result") or {}), "deployed": True}
        replace_run_artifacts(run_id, artifact_summary(run["app_root"]))
        updated = update_run(run_id, status="completed", result=latest_result, error="")
        append_run_log(run_id, "info", "Deploy completed successfully.")
        return {"ok": True, "run": updated}
    except Exception as exc:  # pragma: no cover
        append_run_log(run_id, "error", str(exc))
        update_run(run_id, status="completed", error=str(exc))
        return _json_error(_friendly_error_message(str(exc)), status_code=500)
