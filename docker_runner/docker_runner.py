import os
import subprocess


def _remove_container(container_name, app_folder):
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        cwd=app_folder,
        capture_output=True,
        text=True
    )

def build_and_run_docker(app_folder="generated_app"):
    """
    Builds and runs the backend Docker container for the generated SaaS app,
    automatically installing all dependencies from requirements.txt
    """
    backend_folder = os.path.join(app_folder, "backend")
    backend_dockerfile = os.path.join(backend_folder, "Dockerfile")

    if not os.path.isdir(backend_folder):
        raise FileNotFoundError(f"Backend folder not found: {backend_folder}")

    # Step 1: Create Dockerfile if it does not exist
    if not os.path.exists(backend_dockerfile):
        raise FileNotFoundError(f"Backend Dockerfile not found: {backend_dockerfile}")

    # Step 2: Build Docker image
    print("Building Docker image for backend...")
    subprocess.run(
        ["docker", "build", "-t", "saas_backend", "-f", "backend/Dockerfile", "."],
        cwd=app_folder,
        check=True
    )

    # Step 3: Run Docker container
    print("Running Docker container for backend...")
    _remove_container("saas_backend_container", app_folder)
    subprocess.run(
        ["docker", "run", "-d", "-p", "8000:8000", "--name", "saas_backend_container", "saas_backend"],
        cwd=app_folder,
        check=True
    )

    print("Backend running at http://localhost:8000")
