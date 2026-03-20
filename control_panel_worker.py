from threading import Event

from engine.runtime_env import configure_runtime_environment
from memory.control_panel_store import get_database_backend, init_db
from engine.control_panel_jobs import build_worker_id, worker_loop


def main():
    runtime = configure_runtime_environment()
    init_db()
    worker_id = build_worker_id("service-worker")
    stop_event = Event()
    print(
        "Control-panel worker started with "
        f"id={worker_id} backend={get_database_backend()} storage={runtime['crewai_storage_dir']}"
    )
    worker_loop(stop_event, worker_id)


if __name__ == "__main__":
    main()
