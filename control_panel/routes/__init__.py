from control_panel.routes.auth_routes import router as auth_router
from control_panel.routes.page_routes import router as page_router
from control_panel.routes.run_routes import router as run_router
from control_panel.routes.settings_routes import router as settings_router


__all__ = ["auth_router", "page_router", "run_router", "settings_router"]
