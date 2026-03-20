import subprocess
import os


def _remove_container(container_name, app_folder):
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        cwd=app_folder,
        capture_output=True,
        text=True
    )


def deploy_online(app_folder="generated_app"):
    """
    Deploy the full SaaS app online automatically.
    Assumes Dockerized backend and frontend.
    """
    frontend_folder = os.path.join(app_folder, "frontend")

    if not os.path.isdir(os.path.join(app_folder, "backend")):
        raise FileNotFoundError(f"Backend folder not found: {app_folder}/backend")
    if not os.path.isdir(frontend_folder):
        raise FileNotFoundError(f"Frontend folder not found: {frontend_folder}")
    if not os.path.exists(os.path.join(frontend_folder, "package.json")):
        raise FileNotFoundError(f"Frontend package.json not found: {frontend_folder}/package.json")

    # Step 1: Build backend Docker
    subprocess.run(["docker", "build", "-t", "saas_backend", "-f", "backend/Dockerfile", "."], cwd=app_folder, check=True)
    # Step 2: Run backend Docker container
    _remove_container("saas_backend_container", app_folder)
    subprocess.run(["docker", "run", "-d", "-p", "8000:8000", "--name", "saas_backend_container", "saas_backend"], cwd=app_folder, check=True)

    # Step 3: Build frontend (assuming Node.js/React)
    subprocess.run(["npm", "install"], cwd=frontend_folder, check=True)
    subprocess.run(["npm", "run", "build"], cwd=frontend_folder, check=True)
    _remove_container("saas_frontend_container", app_folder)
    subprocess.run(["docker", "build", "-t", "saas_frontend", "."], cwd=frontend_folder, check=True)
    subprocess.run(["docker", "run", "-d", "-p", "3000:3000", "--name", "saas_frontend_container", "saas_frontend"], cwd=frontend_folder, check=True)

    print("Frontend running at http://localhost:3000")
    print("Backend running at http://localhost:8000")
    print("SaaS deployed locally and ready for online deployment")
