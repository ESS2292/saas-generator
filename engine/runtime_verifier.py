import importlib
import os
import sys
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

from engine.file_writer import GeneratedProjectError


GENERATED_BACKEND_MODULES = ("main", "app_core", "app_config", "database", "providers", "family_logic")


@contextmanager
def _generated_backend_context(app_root):
    backend_root = Path(app_root) / "backend"
    if not backend_root.exists():
        raise GeneratedProjectError(f"Generated backend folder not found: {backend_root}")

    previous_cwd = Path.cwd()
    inserted_path = str(backend_root)
    previous_modules = {name: sys.modules.get(name) for name in GENERATED_BACKEND_MODULES}

    try:
        os.chdir(backend_root)
        sys.path.insert(0, inserted_path)
        for name in GENERATED_BACKEND_MODULES:
            sys.modules.pop(name, None)
        yield backend_root
    finally:
        os.chdir(previous_cwd)
        if sys.path and sys.path[0] == inserted_path:
            sys.path.pop(0)
        for name in GENERATED_BACKEND_MODULES:
            sys.modules.pop(name, None)
        for name, module in previous_modules.items():
            if module is not None:
                sys.modules[name] = module


def verify_generated_backend_runtime(app_root="generated_app", expected_family_route=None):
    with _generated_backend_context(app_root):
        app_module = importlib.import_module("main")
        app = getattr(app_module, "app", None)
        if app is None:
            raise GeneratedProjectError("Generated backend entrypoint does not expose a FastAPI app.")

        with TestClient(app) as client:
            health = client.get("/health")
            config = client.get("/api/config")
            entities = client.get("/api/entities")
            session = client.get("/api/auth/session")
            summary = client.get("/api/summary")
            notifications = client.get("/api/notifications")

            responses = {
                "/health": health,
                "/api/config": config,
                "/api/entities": entities,
                "/api/auth/session": session,
                "/api/summary": summary,
                "/api/notifications": notifications,
            }

            for route, response in responses.items():
                if response.status_code != 200:
                    raise GeneratedProjectError(
                        f"Generated backend runtime check failed for {route}: {response.status_code}"
                    )

            config_payload = config.json()
            entities_payload = entities.json()
            summary_payload = summary.json()
            session_payload = session.json()

            if "entities" not in entities_payload or not entities_payload["entities"]:
                raise GeneratedProjectError("Generated backend runtime response is missing entities.")
            if "user" not in session_payload:
                raise GeneratedProjectError("Generated backend runtime response is missing session user.")
            if "primaryTable" not in config_payload:
                raise GeneratedProjectError("Generated backend runtime response is missing primaryTable.")
            if "totalItems" not in summary_payload:
                raise GeneratedProjectError("Generated backend runtime summary is missing totalItems.")

            family_payload = None
            if expected_family_route:
                family_response = client.get(expected_family_route)
                if family_response.status_code != 200:
                    raise GeneratedProjectError(
                        f"Generated backend runtime check failed for {expected_family_route}: {family_response.status_code}"
                    )
                family_payload = family_response.json()

            return {
                "config": config_payload,
                "entities": entities_payload,
                "session": session_payload,
                "summary": summary_payload,
                "family": family_payload,
            }
