from contextlib import asynccontextmanager
from html import escape
from pathlib import Path
import shutil
import tempfile

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
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


def _setup_checklist(user):
    usage = get_usage_summary(user["id"]) or {}
    provider = check_openai_generation_access()
    secrets = list_secrets(user["id"])
    return [
        {
            "label": "OpenAI provider",
            "ok": provider.get("ok", False),
            "message": provider.get("message", "Unknown provider state."),
        },
        {
            "label": "Run quota",
            "ok": usage.get("remaining_runs", 0) > 0,
            "message": f"{usage.get('remaining_runs', 0)} runs remaining this month.",
        },
        {
            "label": "Deploy/provider secrets",
            "ok": len(secrets) > 0,
            "message": "No secrets stored yet. Add them in settings if you want deployments or provider actions.",
        },
    ]


def _render_auth_page():
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>SaaS Generator Login</title>
<style>
:root { --ink:#102033; --line:#d6dfdc; --accent:#0f766e; --accent-deep:#155e75; --card:rgba(255,255,255,0.9); }
* { box-sizing:border-box; } body { margin:0; color:var(--ink); font-family:Georgia,'Times New Roman',serif; background:radial-gradient(circle at 10% 10%, rgba(15,118,110,0.14), transparent 24%), linear-gradient(180deg, #f7faf9 0%, #eef2f0 42%, #fdf7ed 100%); }
.shell { max-width:960px; margin:0 auto; padding:48px 18px 64px; display:grid; gap:22px; } .card { background:var(--card); border:1px solid var(--line); border-radius:26px; padding:24px; box-shadow:0 18px 46px rgba(15,23,42,0.07); }
.eyebrow { margin:0 0 10px; color:var(--accent); text-transform:uppercase; letter-spacing:0.14em; font-size:0.8rem; } h1,h2,p { margin:0; } h1 { font-size:clamp(2.5rem,5vw,4.6rem); line-height:0.95; max-width:12ch; } .lead { margin-top:12px; max-width:64ch; line-height:1.6; font-size:1.05rem; }
.grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:18px; } form { display:grid; gap:14px; } input { width:100%; border-radius:16px; border:1px solid #bdd2ce; padding:14px; font:inherit; background:#fcfffe; }
button { border:0; border-radius:999px; padding:13px 20px; font:inherit; font-weight:700; color:white; background:linear-gradient(135deg,var(--accent),var(--accent-deep)); cursor:pointer; } .error { display:none; border-radius:16px; padding:14px 16px; color:#b91c1c; background:#fee2e2; border:1px solid #fecaca; }
.hint { color:#475569; font-size:0.94rem; line-height:1.5; }
</style></head><body>
<main class="shell">
<section class="card"><p class="eyebrow">Control Panel Access</p><h1>Sign in before you can launch app-generation runs.</h1><p class="lead">This product layer now includes auth, database-backed users and runs, quotas, stored secrets, queued jobs, logs, and artifact tracking.</p></section>
<div id="errorBox" class="error"></div>
<section class="grid">
<section class="card"><p class="eyebrow">Login</p><h2>Continue to the control panel</h2><form id="loginForm"><input id="loginEmail" type="email" placeholder="you@example.com" /><input id="loginPassword" type="password" placeholder="Password" /><button type="submit">Login</button></form></section>
<section class="card"><p class="eyebrow">Register</p><h2>Create an operator account</h2><form id="registerForm"><input id="registerName" type="text" placeholder="Your name" /><input id="registerEmail" type="email" placeholder="you@example.com" /><input id="registerPassword" type="password" placeholder="Password" /><button type="submit">Register</button></form><p class="hint">This control panel now supports onboarding, settings, prompt templates, advanced build mode, and persistent run detail pages.</p></section>
</section></main>
<script>
const errorBox = document.getElementById('errorBox');
function showError(message){ errorBox.style.display = message ? 'block' : 'none'; errorBox.textContent = message || ''; }
async function submitAuth(path, payload){ const response = await fetch(path,{ method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)}); const data = await response.json(); if(!response.ok){ showError(data.error || 'Authentication failed.'); return; } window.location.reload(); }
document.getElementById('loginForm').addEventListener('submit',(event)=>{ event.preventDefault(); submitAuth('/api/auth/login',{ email:document.getElementById('loginEmail').value, password:document.getElementById('loginPassword').value }); });
document.getElementById('registerForm').addEventListener('submit',(event)=>{ event.preventDefault(); submitAuth('/api/auth/register',{ name:document.getElementById('registerName').value, email:document.getElementById('registerEmail').value, password:document.getElementById('registerPassword').value }); });
</script></body></html>"""


def _render_run_card(run):
    result = run.get("result") or {}
    latest_error = _friendly_error_message(run.get("error") or result.get("latest_error") or "None")
    job = get_job_for_run(run["id"]) or {}
    stages = _run_stage_summary(run)
    stage_markup = "".join(
        f"<span class='stage-pill stage-{escape(stage['state'])}'>{escape(stage['label'])}</span>"
        for stage in stages
    )
    deploy_button = ""
    if run.get("status") == "completed" and result.get("tests_passed") and not result.get("deployed"):
        deploy_button = f'<button class="secondary-button" data-deploy-run="{escape(run["id"])}">Deploy App</button>'
    return f"""
      <article class="run-card" data-run-id="{escape(run['id'])}">
        <div class="run-header">
          <div><p class="eyebrow">Run</p><h3>{escape(result.get('app_name', 'Pending Run'))}</h3></div>
          <span class="status-pill status-{escape(run['status'])}">{escape(run['status'])}</span>
        </div>
        <p class="prompt-copy">{escape(run['prompt'])}</p>
        <div class="stage-row">{stage_markup}</div>
        <div class="metric-grid">
          <div class="metric"><span>Family</span><strong>{escape(result.get('closest_family', 'pending'))}</strong></div>
          <div class="metric"><span>Support</span><strong>{escape(result.get('support_tier', 'pending'))}</strong></div>
          <div class="metric"><span>App Root</span><strong>{escape(run['app_root'])}</strong></div>
          <div class="metric"><span>Worker</span><strong>{escape(job.get('worker_id') or 'queued')}</strong></div>
        </div>
        <div class="detail-grid">
          <div class="panel">
            <h4>Spec</h4>
            <p><strong>Users:</strong> {escape(', '.join(result.get('primary_users', [])) or 'Pending')}</p>
            <p><strong>Entities:</strong> {escape(', '.join(result.get('core_entities', [])) or 'Pending')}</p>
            <p><strong>Workflows:</strong> {escape(', '.join(result.get('core_workflows', [])) or 'Pending')}</p>
          </div>
          <div class="panel">
            <h4>Status</h4>
            <p><strong>Verification:</strong> {'Passed' if result.get('tests_passed') else 'Not passed'}</p>
            <p><strong>Deployed:</strong> {'Yes' if result.get('deployed') else 'No'}</p>
            <p><strong>Error:</strong> {escape(latest_error)}</p>
          </div>
        </div>
        <div class="button-row"><a class="ghost-link" href="/runs/{escape(run['id'])}">Open Run</a>{deploy_button}</div>
      </article>
    """


def _render_dashboard(user):
    runs = list_runs(user["id"], limit=20)
    usage = get_usage_summary(user["id"]) or {}
    secrets = list_secrets(user["id"])
    provider_status = check_openai_generation_access()
    checklist = _setup_checklist(user)
    first_run = len(runs) == 0
    history_markup = "".join(_render_run_card(run) for run in runs) or "<p class='empty-state'>No runs yet. Submit a prompt to start building.</p>"
    secret_markup = "".join(
        f"<div class='secret-row'><strong>{escape(secret['name'])}</strong><span>{escape(secret['updated_at'])}</span><button class='ghost-button' data-delete-secret='{escape(secret['name'])}'>Delete</button></div>"
        for secret in secrets
    ) or "<p class='empty-state'>No stored secrets yet.</p>"
    template_markup = "".join(
        f"<button type='button' class='ghost-button template-button' data-template='{escape(template['prompt'])}'>{escape(template['label'])}</button>"
        for template in PROMPT_TEMPLATES
    )
    checklist_markup = "".join(
        f"<div class='check-row'><strong>{escape(item['label'])}</strong><span class='check-state {'ok' if item['ok'] else 'warn'}'>{'Ready' if item['ok'] else 'Needs attention'}</span><p>{escape(item['message'])}</p></div>"
        for item in checklist
    )
    onboarding_markup = ""
    if first_run:
        onboarding_markup = f"""
<section class="ops"><div class="panel"><p class="eyebrow">First Run Setup</p><h3>Before your first generation</h3><div class="checklist">{checklist_markup}</div><p class="hint">Use a starter template below or switch to advanced mode if you want to specify users, entities, and workflows up front.</p></div></section>
"""
    dashboard_script = """
<script>
const runList = document.getElementById('runList'); const errorBox = document.getElementById('errorBox'); const secretList = document.getElementById('secretList');
function showError(message) { errorBox.style.display = message ? 'block' : 'none'; errorBox.textContent = message || ''; }
function escapeHtml(value) { return String(value ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'", '&#39;'); }
function renderRun(run) {
  const result = run.result || {}; const latestError = run.friendly_error || result.latest_error || 'None';
  const stageMarkup = (run.stages || []).map((stage) => `<span class="stage-pill stage-${escapeHtml(stage.state)}">${escapeHtml(stage.label)}</span>`).join('');
  const deployButton = run.status === 'completed' && result.tests_passed && !result.deployed ? `<button class="secondary-button" data-deploy-run="${escapeHtml(run.id)}">Deploy App</button>` : '';
  return `<article class="run-card" data-run-id="${escapeHtml(run.id)}"><div class="run-header"><div><p class="eyebrow">Run</p><h3>${escapeHtml(result.app_name || 'Pending Run')}</h3></div><span class="status-pill status-${escapeHtml(run.status)}">${escapeHtml(run.status)}</span></div><p class="prompt-copy">${escapeHtml(run.prompt)}</p><div class="stage-row">${stageMarkup}</div><div class="metric-grid"><div class="metric"><span>Family</span><strong>${escapeHtml(result.closest_family || 'pending')}</strong></div><div class="metric"><span>Support</span><strong>${escapeHtml(result.support_tier || 'pending')}</strong></div><div class="metric"><span>App Root</span><strong>${escapeHtml(run.app_root)}</strong></div><div class="metric"><span>Files</span><strong>${result.saved_files_count || 0}</strong></div></div><div class="detail-grid"><div class="panel"><h4>Spec</h4><p><strong>Users:</strong> ${escapeHtml((result.primary_users || []).join(', ') || 'Pending')}</p><p><strong>Entities:</strong> ${escapeHtml((result.core_entities || []).join(', ') || 'Pending')}</p><p><strong>Workflows:</strong> ${escapeHtml((result.core_workflows || []).join(', ') || 'Pending')}</p></div><div class="panel"><h4>Status</h4><p><strong>Verification:</strong> ${result.tests_passed ? 'Passed' : 'Not passed'}</p><p><strong>Deployed:</strong> ${result.deployed ? 'Yes' : 'No'}</p><p><strong>Error:</strong> ${escapeHtml(latestError)}</p></div></div><div class="button-row"><a class="ghost-link" href="/runs/${escapeHtml(run.id)}">Open Run</a>${deployButton}</div></article>`;
}
function renderSecrets(secrets) { secretList.innerHTML = secrets.length ? secrets.map((secret) => `<div class="secret-row"><strong>${escapeHtml(secret.name)}</strong><span>${escapeHtml(secret.updated_at)}</span><button class="ghost-button" data-delete-secret="${escapeHtml(secret.name)}">Delete</button></div>`).join('') : "<p class='empty-state'>No stored secrets yet.</p>"; }
async function loadRuns() { const response = await fetch('/api/runs'); if (response.status === 401) { window.location.reload(); return; } const payload = await response.json(); runList.innerHTML = payload.runs.length ? payload.runs.map(renderRun).join('') : "<p class='empty-state'>No runs yet. Submit a prompt to start building.</p>"; }
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
document.querySelectorAll('.template-button').forEach((button) => { button.addEventListener('click', () => { document.getElementById('prompt').value = button.getAttribute('data-template'); }); });
runList.addEventListener('click', (event) => { const deployButton = event.target.closest('[data-deploy-run]'); if (deployButton) { deployRun(deployButton.getAttribute('data-deploy-run')); } });
secretList.addEventListener('click', (event) => { const button = event.target.closest('[data-delete-secret]'); if (button) { deleteSecretByName(button.getAttribute('data-delete-secret')); } });
setInterval(loadRuns, 5000); setInterval(loadSecrets, 15000);
</script>"""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>SaaS Generator Control Panel</title>
<style>
:root {{ --ink:#102033; --card:rgba(255,255,255,0.88); --line:#d6dfdc; --accent:#0f766e; --accent-deep:#155e75; --warn:#b45309; --danger:#b91c1c; --ok:#166534; }}
* {{ box-sizing:border-box; }} body {{ margin:0; color:var(--ink); font-family:Georgia,'Times New Roman',serif; background:radial-gradient(circle at 10% 10%, rgba(15,118,110,0.14), transparent 24%), linear-gradient(180deg, #f7faf9 0%, #eef2f0 42%, #fdf7ed 100%); }}
.shell {{ max-width:1260px; margin:0 auto; padding:40px 18px 64px; display:grid; gap:22px; }} .hero,.composer,.history,.ops {{ background:var(--card); border:1px solid var(--line); border-radius:26px; padding:24px; box-shadow:0 18px 46px rgba(15,23,42,0.07); backdrop-filter:blur(12px); }}
.eyebrow {{ margin:0 0 10px; color:var(--accent); text-transform:uppercase; letter-spacing:0.14em; font-size:0.8rem; }} h1,h2,h3,h4,p {{ margin:0; }} h1 {{ font-size:clamp(2.5rem,5vw,4.6rem); line-height:0.95; max-width:12ch; }} .lead {{ margin-top:12px; max-width:66ch; line-height:1.6; font-size:1.05rem; }}
.topbar {{ display:flex; justify-content:space-between; gap:16px; align-items:start; }} .user-chip {{ border-radius:999px; padding:10px 14px; background:#ecfeff; border:1px solid #cfe9e4; }}
.panel {{ border:1px solid var(--line); border-radius:22px; padding:18px; background:linear-gradient(180deg, rgba(255,255,255,0.84), rgba(236,254,255,0.7)); }}
.composer form, .secret-form {{ display:grid; gap:16px; }} textarea,input {{ width:100%; border-radius:18px; border:1px solid #bdd2ce; padding:18px; font:inherit; font-size:1rem; background:#fcfffe; resize:vertical; }}
.controls,.button-row,.secret-row,.stage-row,.template-row {{ display:flex; gap:16px; flex-wrap:wrap; align-items:center; }} .controls label {{ display:flex; gap:10px; align-items:center; font-size:0.96rem; }}
button {{ border:0; border-radius:999px; padding:13px 20px; font:inherit; font-weight:700; color:white; background:linear-gradient(135deg,var(--accent),var(--accent-deep)); cursor:pointer; }}
.secondary-button {{ background:linear-gradient(135deg, #92400e, #d97706); }} .ghost-button {{ background:linear-gradient(135deg, #475569, #334155); }} .ghost-link {{ display:inline-flex; align-items:center; justify-content:center; border-radius:999px; padding:13px 20px; font-weight:700; color:white; text-decoration:none; background:linear-gradient(135deg, #475569, #334155); }} .hint {{ color:#475569; font-size:0.92rem; }}
.error {{ display:none; border-radius:16px; padding:14px 16px; color:var(--danger); background:#fee2e2; border:1px solid #fecaca; }} .history-header,.run-header {{ display:flex; justify-content:space-between; gap:16px; align-items:start; }} .history-header {{ margin-bottom:18px; }}
.run-list {{ display:grid; gap:18px; }} .run-card {{ border-radius:22px; border:1px solid var(--line); padding:20px; background:linear-gradient(180deg, rgba(255,255,255,0.85), rgba(248,250,252,0.88)); }}
.status-pill {{ border-radius:999px; padding:8px 12px; font-size:0.82rem; font-weight:700; text-transform:capitalize; }} .status-queued {{ background:#e0f2fe; color:#0c4a6e; }} .status-running,.status-deploying {{ background:#fef3c7; color:var(--warn); }} .status-completed {{ background:#dcfce7; color:var(--ok); }} .status-failed {{ background:#fee2e2; color:var(--danger); }}
.stage-pill {{ border-radius:999px; padding:6px 10px; font-size:0.76rem; font-weight:700; background:#e2e8f0; color:#475569; }} .stage-done {{ background:#dcfce7; color:#166534; }} .stage-current {{ background:#dbeafe; color:#1d4ed8; }} .stage-failed {{ background:#fee2e2; color:#b91c1c; }} .stage-pending {{ background:#e2e8f0; color:#64748b; }}
.prompt-copy {{ margin:12px 0 14px; line-height:1.5; color:#334155; }} .metric-grid,.detail-grid,.ops-grid {{ display:grid; gap:14px; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); }} .metric-grid {{ margin-bottom:16px; }}
.metric {{ border-radius:18px; padding:14px; background:rgba(255,255,255,0.88); border:1px solid #dfe8e5; }} .metric span {{ display:block; font-size:0.76rem; letter-spacing:0.12em; text-transform:uppercase; color:#64748b; margin-bottom:8px; }}
.empty-state {{ color:#475569; font-size:1rem; }} .secret-row {{ justify-content:space-between; padding:12px 0; border-bottom:1px solid #e2e8f0; }} .checklist {{ display:grid; gap:14px; }} .check-row {{ border-radius:18px; padding:14px; border:1px solid #dfe8e5; background:white; }} .check-row p {{ margin-top:8px; color:#475569; }} .check-state {{ display:inline-flex; margin-left:10px; font-weight:700; }} .check-state.ok {{ color:#166534; }} .check-state.warn {{ color:#b45309; }} .advanced-fields {{ display:none; gap:12px; }} .advanced-fields.active {{ display:grid; }}
@media (max-width:860px) {{ .topbar,.history-header,.run-header {{ flex-direction:column; }} }}
</style></head><body>
<main class="shell">
<section class="hero"><div class="topbar"><div><p class="eyebrow">Authenticated Control Panel</p><h1>Launch prompt-driven app builds under your account.</h1><p class="lead">This dashboard now includes user-scoped runs, persistent queued jobs, usage limits, stored deployment secrets, and per-run logs and artifacts.</p></div><div class="controls"><span class="user-chip">{escape(user['name'])} · {escape(user['email'])}</span><a class="ghost-link" href="/settings">Settings</a><button id="logoutButton" class="ghost-button" type="button">Logout</button></div></div></section>
{onboarding_markup}
<section class="composer"><div id="errorBox" class="error"></div><form id="generatorForm"><textarea id="prompt" name="prompt" placeholder="Build a finance ops app for invoice approvals and cashflow tracking."></textarea><div class="template-row">{template_markup}</div><div class="controls"><label><input id="runVerification" type="checkbox" checked /> Run verification</label><label><input id="autoDeploy" type="checkbox" /> Auto deploy after success</label><label><input id="advancedMode" type="checkbox" /> Advanced mode</label><button type="submit">Queue Run</button></div><div id="advancedFields" class="advanced-fields"><input id="appName" placeholder="App name" /><input id="targetUsers" placeholder="Target users" /><input id="coreEntities" placeholder="Core entities" /><input id="coreWorkflows" placeholder="Core workflows" /></div><p class="hint">Runs are queued in the control-panel database and processed by a separate worker service. Monthly usage: <strong>{usage.get('monthly_run_usage', 0)}/{usage.get('monthly_run_limit', 0)}</strong> on the <strong>{escape(usage.get('plan', 'free'))}</strong> plan.</p></form></section>
<section class="ops"><div class="ops-grid">
  <div class="panel"><p class="eyebrow">Billing & Limits</p><h3>Usage</h3><p><strong>Plan:</strong> {escape(usage.get('plan', 'free'))}</p><p><strong>Month:</strong> {escape(usage.get('usage_month', ''))}</p><p><strong>Used:</strong> {usage.get('monthly_run_usage', 0)}</p><p><strong>Remaining:</strong> {usage.get('remaining_runs', 0)}</p><p><strong>Database:</strong> {escape(usage.get('database_url', ''))}</p></div>
  <div class="panel"><p class="eyebrow">LLM Provider</p><h3>OpenAI Access</h3><p><strong>Status:</strong> {escape(provider_status.get('status', 'unknown'))}</p><p><strong>Message:</strong> {escape(provider_status.get('message', ''))}</p></div>
  <div class="panel"><p class="eyebrow">Stored Secrets</p><h3>Deploy & Provider Secrets</h3><form id="secretForm" class="secret-form"><input id="secretName" placeholder="RENDER_API_KEY" /><input id="secretValue" placeholder="Secret value" type="password" /><div class="controls"><button type="submit">Store Secret</button></div></form><div id="secretList">{secret_markup}</div></div>
</div></section>
<section class="history"><div class="history-header"><div><p class="eyebrow">Your Runs</p><h2>Recent generator runs</h2></div><div class="controls"><a class="ghost-link" href="/settings">Provider & Settings</a><button id="refreshRuns" class="secondary-button" type="button">Refresh</button></div></div><div id="runList" class="run-list">{history_markup}</div></section>
</main>
</main>""" + dashboard_script + """</body></html>"""


def _render_settings_page(user):
    usage = get_usage_summary(user["id"]) or {}
    provider = check_openai_generation_access()
    secrets = list_secrets(user["id"])
    secret_markup = "".join(
        f"<li><strong>{escape(secret['name'])}</strong> · updated {escape(secret['updated_at'])}</li>"
        for secret in secrets
    ) or "<li>No stored secrets yet.</li>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Settings</title><style>
body {{ margin:0; font-family:Georgia,'Times New Roman',serif; background:#f8fafc; color:#102033; }}
.shell {{ max-width:980px; margin:0 auto; padding:32px 18px 64px; display:grid; gap:18px; }}
.card {{ background:white; border:1px solid #d6dfdc; border-radius:24px; padding:22px; }}
a.button {{ display:inline-flex; text-decoration:none; color:white; background:#334155; border-radius:999px; padding:12px 18px; font-weight:700; }}
ul {{ padding-left:18px; }}
</style></head><body><main class="shell">
<section class="card"><a class="button" href="/">Back to Dashboard</a><h1>Settings</h1><p>Review provider readiness, account quota, and stored secrets.</p></section>
<section class="card"><h2>Provider Status</h2><p><strong>Status:</strong> {escape(provider.get('status', 'unknown'))}</p><p><strong>Message:</strong> {escape(provider.get('message', ''))}</p></section>
<section class="card"><h2>Usage</h2><p><strong>Plan:</strong> {escape(usage.get('plan', 'free'))}</p><p><strong>Remaining runs:</strong> {usage.get('remaining_runs', 0)}</p><p><strong>Database:</strong> {escape(usage.get('database_url', ''))}</p></section>
<section class="card"><h2>Stored Secrets</h2><ul>{secret_markup}</ul></section>
</main></body></html>"""


def _render_run_detail_page(user, run):
    result = run.get("result") or {}
    logs = list_run_logs(user["id"], run["id"], limit=200) or []
    artifacts = list_run_artifacts(user["id"], run["id"]) or []
    stages = _run_stage_summary(run)
    stage_markup = "".join(
        f"<span class='stage-pill stage-{escape(stage['state'])}'>{escape(stage['label'])}</span>"
        for stage in stages
    )
    log_text = "\n".join(
        f"[{entry['created_at']}] {entry['level'].upper()}: {entry['message']}" for entry in logs
    ) or "No logs yet."
    artifact_markup = "".join(
        f"<li><strong>{escape(item['label'])}</strong><br />{escape(item['path'])}</li>" for item in artifacts
    ) or "<li>No artifacts yet.</li>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Run Details</title><style>
body {{ margin:0; font-family:Georgia,'Times New Roman',serif; background:#f8fafc; color:#102033; }}
.shell {{ max-width:1100px; margin:0 auto; padding:32px 18px 64px; display:grid; gap:18px; }}
.card {{ background:white; border:1px solid #d6dfdc; border-radius:24px; padding:22px; }}
.actions {{ display:flex; gap:12px; flex-wrap:wrap; }}
a.button {{ display:inline-flex; text-decoration:none; color:white; background:#334155; border-radius:999px; padding:12px 18px; font-weight:700; }}
.secondary {{ background:#0f766e; }}
.stage-pill {{ border-radius:999px; padding:6px 10px; font-size:0.76rem; font-weight:700; background:#e2e8f0; color:#475569; margin-right:8px; }}
.stage-done {{ background:#dcfce7; color:#166534; }} .stage-current {{ background:#dbeafe; color:#1d4ed8; }} .stage-failed {{ background:#fee2e2; color:#b91c1c; }} .stage-pending {{ background:#e2e8f0; color:#64748b; }}
pre {{ white-space:pre-wrap; background:#0f172a; color:#e2e8f0; border-radius:16px; padding:16px; overflow:auto; }}
ul {{ padding-left:18px; }}
</style></head><body><main class="shell">
<section class="card"><div class="actions"><a class="button" href="/">Back to Dashboard</a><a class="button secondary" href="/api/runs/{escape(run['id'])}/download">Download App</a><a class="button" href="/settings">Settings</a></div><h1>{escape(result.get('app_name', 'Run Details'))}</h1><p><strong>Status:</strong> {escape(run['status'])}</p><p><strong>Prompt:</strong> {escape(run['prompt'])}</p><p><strong>Error:</strong> {escape(_friendly_error_message(run.get('error') or result.get('latest_error') or 'None'))}</p></section>
<section class="card"><h2>Stage Timeline</h2><div>{stage_markup}</div></section>
<section class="card"><h2>Result Summary</h2><p><strong>Family:</strong> {escape(result.get('closest_family', 'pending'))}</p><p><strong>Support tier:</strong> {escape(result.get('support_tier', 'pending'))}</p><p><strong>Verification:</strong> {'Passed' if result.get('tests_passed') else 'Not passed'}</p><p><strong>Deployed:</strong> {'Yes' if result.get('deployed') else 'No'}</p></section>
<section class="card"><h2>Artifacts</h2><ul>{artifact_markup}</ul></section>
<section class="card"><h2>Logs</h2><pre>{escape(log_text)}</pre></section>
</main></body></html>"""


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = _current_user(request)
    if not user:
        return _render_auth_page()
    return _render_dashboard(user)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user = _current_user(request)
    if not user:
        return _render_auth_page()
    return _render_settings_page(user)


@app.get("/runs/{run_id}", response_class=HTMLResponse)
async def run_detail_page(run_id: str, request: Request):
    user = _current_user(request)
    if not user:
        return _render_auth_page()
    run = get_run(user["id"], run_id)
    if not run:
        return HTMLResponse("Run not found.", status_code=404)
    return _render_run_detail_page(user, run)


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "database_backend": get_database_backend(),
        "worker_mode": "external_service",
        "provider_status": check_openai_generation_access(),
    }


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
