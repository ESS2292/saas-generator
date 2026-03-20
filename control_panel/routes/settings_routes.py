from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from control_panel.app_state import (
    build_run_metrics,
    build_system_metrics,
    current_user,
    json_error,
    readiness_status,
)
from control_panel.schemas import SecretRequest
from memory.control_panel_store import (
    delete_secret,
    get_run,
    get_usage_summary,
    list_secrets,
    store_secret,
)


router = APIRouter()


@router.get("/api/health")
async def health():
    return readiness_status()


@router.get("/api/readiness")
async def readiness():
    payload = readiness_status()
    status_code = 200 if payload["ok"] else 503
    return JSONResponse(payload, status_code=status_code)


@router.get("/api/usage")
async def usage(request: Request):
    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    return get_usage_summary(user["id"])


@router.get("/api/billing/usage")
async def billing_usage(request: Request):
    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    return get_usage_summary(user["id"])


@router.get("/api/provider-status")
async def provider_status(request: Request):
    import web_app

    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    return web_app.check_openai_generation_access()


@router.get("/api/observability/summary")
async def observability_summary(request: Request):
    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    return build_system_metrics()


@router.get("/api/observability/runs/{run_id}")
async def observability_run_metrics(run_id: str, request: Request):
    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    run = get_run(user["id"], run_id)
    if not run:
        return json_error("Run not found.", status_code=404)
    return build_run_metrics(run)


@router.get("/api/secrets")
async def secrets_list(request: Request):
    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    return {"secrets": list_secrets(user["id"])}


@router.post("/api/secrets")
async def secrets_save(payload: SecretRequest, request: Request):
    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    if not payload.name.strip() or not payload.value:
        return json_error("Secret name and value are required.")
    store_secret(user["id"], payload.name.strip(), payload.value)
    return {"ok": True}


@router.delete("/api/secrets/{name}")
async def secrets_delete(name: str, request: Request):
    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    delete_secret(user["id"], name)
    return {"ok": True}
