import asyncio
import json
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from control_panel.app_state import (
    build_prompt,
    current_user,
    friendly_error_message,
    json_error,
    run_payload,
    run_summary_payload,
)
from control_panel.lifecycle import transition_status
from control_panel.schemas import GenerateRequest
from engine.control_panel_jobs import artifact_summary
from memory.control_panel_store import (
    append_run_log,
    create_run,
    get_run,
    get_run_by_id,
    list_run_artifacts,
    list_run_logs,
    list_runs,
    replace_run_artifacts,
    update_run,
)


router = APIRouter()


@router.get("/api/runs")
async def get_runs(request: Request):
    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    runs = list_runs(user["id"], limit=20)
    return {"runs": [run_summary_payload(run) for run in runs]}


@router.get("/api/runs/{run_id}")
async def get_run_status(run_id: str, request: Request):
    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    run = get_run(user["id"], run_id)
    if not run:
        return json_error("Run not found.", status_code=404)
    return run_summary_payload(run)


@router.get("/api/runs/{run_id}/stream")
async def stream_run_status(run_id: str, request: Request, once: bool = False):
    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    if not get_run(user["id"], run_id):
        return json_error("Run not found.", status_code=404)

    async def event_stream():
        last_payload = None
        while True:
            payload = run_payload(user["id"], run_id)
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


@router.get("/api/runs/{run_id}/logs")
async def get_run_logs_api(run_id: str, request: Request):
    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    logs = list_run_logs(user["id"], run_id)
    if logs is None:
        return json_error("Run not found.", status_code=404)
    return {"logs": logs}


@router.get("/api/runs/{run_id}/artifacts")
async def get_run_artifacts_api(run_id: str, request: Request):
    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    artifacts = list_run_artifacts(user["id"], run_id)
    if artifacts is None:
        return json_error("Run not found.", status_code=404)
    return {"artifacts": artifacts}


@router.get("/api/runs/{run_id}/download")
async def download_run_bundle(run_id: str, request: Request):
    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    run = get_run(user["id"], run_id)
    if not run:
        return json_error("Run not found.", status_code=404)
    app_root = Path(run["app_root"])
    if not app_root.exists():
        return json_error("Generated app files are not available for download.", status_code=404)
    bundle_dir = Path(tempfile.mkdtemp(prefix="control-panel-bundle-"))
    archive_base = bundle_dir / run_id
    archive_path = shutil.make_archive(str(archive_base), "zip", root_dir=app_root)
    return FileResponse(archive_path, media_type="application/zip", filename=f"{run_id}.zip")


@router.post("/api/runs")
async def create_run_api(payload: GenerateRequest, request: Request):
    import web_app

    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    if not payload.prompt.strip():
        return json_error("Prompt is required.")
    provider = web_app.check_openai_generation_access()
    if not provider.get("ok"):
        return json_error(
            f"OpenAI provider is not ready: {friendly_error_message(provider.get('message', 'Unknown provider error.'))}",
            status_code=503,
        )
    final_prompt = build_prompt(payload)
    app_root = web_app.app_root_for_idea(payload.prompt)
    try:
        run = create_run(
            user["id"],
            final_prompt,
            app_root=app_root,
            run_verification=payload.run_verification,
            auto_deploy=payload.auto_deploy,
        )
    except ValueError as exc:
        return json_error(str(exc), status_code=403)
    append_run_log(run["id"], "info", "Run queued.")
    if payload.mode == "advanced":
        append_run_log(run["id"], "info", "Advanced brief attached to run prompt.")
    return JSONResponse(run, status_code=202)


@router.post("/api/runs/{run_id}/deploy")
async def deploy_run_api(run_id: str, request: Request):
    import web_app

    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    run = get_run(user["id"], run_id)
    if not run:
        return json_error("Run not found.", status_code=404)
    if run.get("status") != "completed":
        return json_error("Run has not completed successfully yet.")
    result = run.get("result") or {}
    if not result.get("tests_passed"):
        return json_error("Cannot deploy a run that did not pass verification.")
    if result.get("deployed"):
        return {"ok": True, "message": "Run already deployed."}
    deploying_status = transition_status(run["status"], "deploying")
    update_run(run_id, status=deploying_status, error="")
    append_run_log(run_id, "info", "Manual deploy requested from control panel.")
    try:
        web_app.deploy_online(app_folder=run["app_root"])
        latest = get_run_by_id(run_id) or run
        latest_result = {**(latest.get("result") or {}), "deployed": True}
        replace_run_artifacts(run_id, artifact_summary(run["app_root"]))
        updated = update_run(run_id, status=transition_status(deploying_status, "completed"), result=latest_result, error="")
        append_run_log(run_id, "info", "Deploy completed successfully.")
        return {"ok": True, "run": updated}
    except Exception as exc:  # pragma: no cover
        append_run_log(run_id, "error", str(exc))
        update_run(run_id, status=transition_status(deploying_status, "failed"), error=str(exc))
        return json_error(friendly_error_message(str(exc)), status_code=500)
