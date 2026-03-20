from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from control_panel.app_state import current_user, render_auth_page, render_dashboard, render_run_detail_page, render_settings_page
from control_panel.theme import THEME_COOKIE, theme_from_request
from memory.control_panel_store import get_run


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = current_user(request)
    theme = theme_from_request(request)
    if not user:
        return render_auth_page(theme)
    return render_dashboard(user, theme)


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user = current_user(request)
    theme = theme_from_request(request)
    if not user:
        return render_auth_page(theme)
    return render_settings_page(user, theme)


@router.get("/runs/{run_id}", response_class=HTMLResponse)
async def run_detail_page(run_id: str, request: Request):
    user = current_user(request)
    theme = theme_from_request(request)
    if not user:
        return render_auth_page(theme)
    run = get_run(user["id"], run_id)
    if not run:
        return HTMLResponse("Run not found.", status_code=404)
    return render_run_detail_page(user, run, theme)


@router.get("/theme/toggle")
async def toggle_theme(request: Request, next: str = "/"):
    current = theme_from_request(request)
    new_theme = "light" if current == "dark" else "dark"
    response = RedirectResponse(url=next, status_code=303)
    response.set_cookie(THEME_COOKIE, new_theme, httponly=False, samesite="lax")
    return response
