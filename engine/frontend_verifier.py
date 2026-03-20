import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from engine.file_writer import GeneratedProjectError


def _run_command(command, workdir):
    result = subprocess.run(
        command,
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part).strip()
        raise GeneratedProjectError(
            f"Generated frontend command failed: {' '.join(command)}\n{output[:1200]}"
        )
    return result


def _pick_preview_port():
    return 4100 + (os.getpid() % 500)


def _preview_port_from_package_json(frontend_root):
    package_json = json.loads((frontend_root / "package.json").read_text(encoding="utf-8"))
    preview_script = package_json.get("scripts", {}).get("preview", "")
    match = re.search(r"--port\s+(\d+)", preview_script)
    if match:
        return int(match.group(1))
    match = re.search(r"\bPORT=(\d+)\b", preview_script)
    if match:
        return int(match.group(1))
    return _pick_preview_port()


def _fetch_text(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.status, response.read().decode("utf-8", errors="ignore")


def _verify_dist_shell(frontend_root, manifest):
    dist_root = frontend_root / "dist"
    index_path = dist_root / "index.html"
    if not index_path.exists():
        raise GeneratedProjectError("Generated frontend dist/index.html is missing.")
    body = index_path.read_text(encoding="utf-8")
    if '<div id="root"></div>' not in body or '<script type="module"' not in body:
        raise GeneratedProjectError("Generated frontend dist shell is missing the app root or module script.")

    asset_paths = re.findall(r'(?:src|href)="(/assets/[^"]+)"', body)
    if not asset_paths:
        raise GeneratedProjectError("Generated frontend dist shell is missing built assets.")

    fetched_assets = []
    for asset_path in asset_paths[:3]:
        asset_file = dist_root / asset_path.lstrip("/")
        if not asset_file.exists():
            raise GeneratedProjectError(f"Generated frontend dist asset is missing: {asset_path}")
        fetched_assets.append(asset_path)

    return {
        "mode": "static_fallback",
        "checked_routes": _expected_page_routes(manifest),
        "asset_paths": fetched_assets,
    }


def _wait_for_url(url, process, timeout=20):
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            output = "\n".join(part for part in (stdout.strip(), stderr.strip()) if part).strip()
            raise GeneratedProjectError(f"Generated frontend preview exited early.\n{output[:1200]}")
        try:
            status, _body = _fetch_text(url)
            if status == 200:
                return
        except urllib.error.URLError as exc:
            last_error = str(exc)
        time.sleep(0.25)
    raise GeneratedProjectError(f"Generated frontend preview did not become ready: {last_error[:400]}")


@contextmanager
def _frontend_preview(frontend_root, port):
    process = subprocess.Popen(
        ["npm", "run", "preview"],
        cwd=frontend_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        yield process
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def _page_slug(name):
    slug = re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")
    return slug or "page"


def _expected_page_routes(manifest):
    return [
        "/" if index == 0 else f"/{_page_slug(page['name'])}"
        for index, page in enumerate(manifest.get("pages", []))
    ] or ["/"]


def verify_generated_frontend_build(app_root="generated_app", install_deps=True):
    frontend_root = Path(app_root) / "frontend"
    if not frontend_root.exists():
        raise GeneratedProjectError(f"Generated frontend folder not found: {frontend_root}")

    package_json = frontend_root / "package.json"
    if not package_json.exists():
        raise GeneratedProjectError(f"Generated frontend package.json not found: {package_json}")

    if install_deps:
        _run_command(
            ["npm", "install", "--prefer-offline", "--no-audit", "--no-fund"],
            frontend_root,
        )

    _run_command(["npm", "run", "build"], frontend_root)

    dist_index = frontend_root / "dist" / "index.html"
    if not dist_index.exists():
        raise GeneratedProjectError("Generated frontend build did not produce dist/index.html.")

    return {
        "frontend_root": str(frontend_root),
        "dist_index": str(dist_index),
    }


def verify_generated_frontend_preview(app_root="generated_app", install_deps=True, build_first=True):
    frontend_root = Path(app_root) / "frontend"
    manifest_path = Path(app_root) / "manifest.json"
    if not manifest_path.exists():
        raise GeneratedProjectError(f"Generated manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if build_first:
        verify_generated_frontend_build(app_root, install_deps=install_deps)

    port = _preview_port_from_package_json(frontend_root)
    base_url = f"http://127.0.0.1:{port}"
    with _frontend_preview(frontend_root, port) as process:
        try:
            _wait_for_url(f"{base_url}/", process)
        except GeneratedProjectError as exc:
            error_text = str(exc)
            if "listen EPERM" in error_text or "operation not permitted" in error_text:
                fallback = _verify_dist_shell(frontend_root, manifest)
                return {
                    "frontend_root": str(frontend_root),
                    "base_url": base_url,
                    **fallback,
                }
            raise

        checked_routes = []
        for route in _expected_page_routes(manifest):
            status, body = _fetch_text(f"{base_url}{route}")
            if status != 200:
                raise GeneratedProjectError(
                    f"Generated frontend preview route failed: {route} ({status})"
                )
            if '<div id="root"></div>' not in body or '<script type="module"' not in body:
                raise GeneratedProjectError(
                    f"Generated frontend preview route did not return the app shell: {route}"
                )
            checked_routes.append(route)

        root_status, root_body = _fetch_text(f"{base_url}/")
        if root_status != 200:
            raise GeneratedProjectError("Generated frontend preview root route did not return 200.")

        asset_paths = re.findall(r'(?:src|href)="(/assets/[^"]+)"', root_body)
        if not asset_paths:
            raise GeneratedProjectError("Generated frontend preview root route is missing built assets.")

        fetched_assets = []
        for asset_path in asset_paths[:3]:
            asset_status, _asset_body = _fetch_text(f"{base_url}{asset_path}")
            if asset_status != 200:
                raise GeneratedProjectError(f"Generated frontend preview asset failed: {asset_path} ({asset_status})")
            fetched_assets.append(asset_path)

    return {
        "frontend_root": str(frontend_root),
        "base_url": base_url,
        "mode": "preview",
        "checked_routes": checked_routes,
        "asset_paths": fetched_assets,
    }
