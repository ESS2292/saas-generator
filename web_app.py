from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from control_panel.app_state import SESSION_COOKIE
from control_panel.routes import auth_router, page_router, run_router, settings_router
from deployment.deploy import deploy_online
from engine.pipeline import app_root_for_idea
from engine.provider_health import check_openai_generation_access
from memory.control_panel_store import init_db


@asynccontextmanager
async def app_lifespan(_app):
    init_db()
    yield


app = FastAPI(title="SaaS Generator Control Panel", lifespan=app_lifespan)

# Mount the lightweight browser client separately from the server-rendered templates.
app.mount("/static", StaticFiles(directory="control_panel/static"), name="static")

for router in (page_router, auth_router, settings_router, run_router):
    app.include_router(router)


__all__ = ["SESSION_COOKIE", "app", "app_root_for_idea", "check_openai_generation_access", "deploy_online"]
