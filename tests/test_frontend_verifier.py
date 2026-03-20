import json

from engine.frontend_verifier import verify_generated_frontend_build, verify_generated_frontend_preview
from engine.project_builder import build_project_from_manifest
from tests.golden_prompts import GOLDEN_PROMPTS


def test_frontend_verifier_builds_live_fixture(tmp_path):
    frontend_root = tmp_path / "frontend"
    frontend_root.mkdir(parents=True)

    package_json = {
        "name": "fixture-frontend",
        "private": True,
        "version": "0.1.0",
        "scripts": {
            "build": "node -e \"const fs=require('fs'); fs.mkdirSync('dist',{recursive:true}); fs.writeFileSync('dist/index.html','<html></html>');\""
        },
    }
    (frontend_root / "package.json").write_text(json.dumps(package_json), encoding="utf-8")

    result = verify_generated_frontend_build(str(tmp_path), install_deps=False)

    assert result["dist_index"].endswith("dist/index.html")


def test_generated_frontend_package_includes_router_dependency(tmp_path):
    app_root = tmp_path / "generated"
    build_project_from_manifest(GOLDEN_PROMPTS[0]["manifest_output"], app_root=str(app_root))

    package_json = json.loads((app_root / "frontend" / "package.json").read_text(encoding="utf-8"))

    assert package_json["dependencies"]["react-router-dom"] == "^6.28.0"


def test_frontend_preview_serves_live_routes_from_fixture(tmp_path):
    app_root = tmp_path / "fixture"
    frontend_root = app_root / "frontend"
    frontend_root.mkdir(parents=True)
    (app_root / "manifest.json").write_text(
        json.dumps(
            {
                "pages": [
                    {"name": "Overview"},
                    {"name": "Clients"},
                ]
            }
        ),
        encoding="utf-8",
    )
    package_json = {
        "name": "fixture-preview",
        "private": True,
        "version": "0.1.0",
        "scripts": {
            "build": (
                "node -e \"const fs=require('fs');"
                "fs.mkdirSync('dist/assets',{recursive:true});"
                "fs.writeFileSync('dist/index.html','<!doctype html><html><body><div id=\\\"root\\\"></div><script type=\\\"module\\\" src=\\\"/assets/app.js\\\"></script></body></html>');"
                "fs.writeFileSync('dist/assets/app.js','console.log(\\\"fixture\\\")');\""
            ),
            "preview": (
                "PORT=4130 node -e \"const http=require('http'); const fs=require('fs'); const path=require('path');"
                "const port=4130; const root=path.join(process.cwd(),'dist');"
                "const index=fs.readFileSync(path.join(root,'index.html'));"
                "http.createServer((req,res)=>{"
                "if(req.url.startsWith('/assets/')){"
                "const file=path.join(root, req.url.slice(1));"
                "res.writeHead(200, {'Content-Type':'application/javascript'}); res.end(fs.readFileSync(file)); return;}"
                "res.writeHead(200, {'Content-Type':'text/html'}); res.end(index);"
                "}).listen(port,'127.0.0.1');\""
            ),
        },
    }
    (frontend_root / "package.json").write_text(json.dumps(package_json), encoding="utf-8")

    result = verify_generated_frontend_preview(str(app_root), install_deps=False, build_first=True)

    assert result["mode"] in {"preview", "static_fallback"}
    assert "/" in result["checked_routes"]
    assert "/clients" in result["checked_routes"]
    assert result["asset_paths"]
