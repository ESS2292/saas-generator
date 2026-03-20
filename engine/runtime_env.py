import os
import importlib
from pathlib import Path
import appdirs


def configure_runtime_environment():
    # CrewAI defaults to user-level storage directories under the home folder.
    # In this project we pin that storage inside the repo so local runs and the
    # worker process stay writable and predictable.
    storage_dir = Path(".crewai_storage").resolve()
    storage_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("CREWAI_STORAGE_DIR", "saas-generator-local")
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")

    def _storage_path():
        return str(storage_dir)

    original_user_data_dir = appdirs.user_data_dir

    def _patched_user_data_dir(appname=None, appauthor=None, version=None, roaming=False):
        # Only redirect CrewAI-owned storage. Everything else should use the
        # normal platform-specific appdirs behavior.
        if appauthor == "CrewAI":
            return str(storage_dir)
        return original_user_data_dir(appname=appname, appauthor=appauthor, version=version, roaming=roaming)

    appdirs.user_data_dir = _patched_user_data_dir

    try:
        crew_paths = importlib.import_module("crewai.utilities.paths")
        crew_paths.db_storage_path = _storage_path
    except Exception:
        pass

    # Some CrewAI modules import and bind the path helper at import time, so we
    # patch the commonly used storage modules directly as well.
    for module_name in (
        "crewai.memory.storage.kickoff_task_outputs_storage",
        "crewai.memory.storage.ltm_sqlite_storage",
        "crewai.memory.storage.rag_storage",
        "crewai.events.listeners.tracing.utils",
    ):
        try:
            module = importlib.import_module(module_name)
            module.db_storage_path = _storage_path
        except Exception:
            continue

    return {
        "crewai_storage_dir": str(storage_dir),
        "otel_disabled": os.environ.get("OTEL_SDK_DISABLED", ""),
    }
