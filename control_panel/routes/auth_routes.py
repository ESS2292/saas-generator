from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from control_panel.app_state import SESSION_COOKIE, current_user, json_error
from control_panel.schemas import AuthRequest
from memory.control_panel_store import authenticate_user, create_session, delete_session, get_usage_summary, register_user


router = APIRouter()


@router.get("/api/me")
async def me(request: Request):
    user = current_user(request)
    if not user:
        return json_error("Unauthorized.", status_code=401)
    return {"user": user, "usage": get_usage_summary(user["id"])}


@router.post("/api/auth/register")
async def register(payload: AuthRequest):
    try:
        user = register_user(payload.email, payload.password, payload.name or payload.email)
    except ValueError as exc:
        return json_error(str(exc))
    token = create_session(user["id"])
    response = JSONResponse({"ok": True, "user": user})
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax")
    return response


@router.post("/api/auth/login")
async def login(payload: AuthRequest):
    user = authenticate_user(payload.email, payload.password)
    if not user:
        return json_error("Invalid email or password.", status_code=401)
    token = create_session(user["id"])
    response = JSONResponse({"ok": True, "user": user})
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax")
    return response


@router.post("/api/auth/logout")
async def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        delete_session(token)
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE)
    return response
