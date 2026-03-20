import json

from engine.file_writer import save_project_files
from engine.manifest import parse_manifest
from engine.validator import validate_project_scaffold
from templates.renderers import build_project_files

ARTIFACT_FILE_PREFIXES = {
    "backend": ("backend/",),
    "frontend": ("frontend/",),
    "deploy": ("deploy/", ".env.example"),
    "scaffold": (),
}

FAILURE_STAGE_ARTIFACTS = {
    "manifest_validation": "scaffold",
    "scaffold_validation": "scaffold",
    "backend_runtime": "backend",
    "frontend_build": "frontend",
    "docker_backend": "backend",
    "integration_tests": "backend",
    "deployment": "deploy",
}


def canonicalize_manifest_output(output_text, intake_context=None, spec_brief=None):
    manifest = parse_manifest(output_text, intake_context=intake_context, spec_brief=spec_brief)
    manifest_text = json.dumps(manifest, indent=2) + "\n"
    return manifest, manifest_text


def rewrite_project_scaffold(manifest, app_root="generated_app"):
    files = build_project_files(manifest)
    saved_files = save_project_files(files, app_root=app_root)
    saved_files.extend(
        save_project_files(
            [("manifest.json", json.dumps(manifest, indent=2) + "\n")],
            app_root=app_root,
            validate_required=False,
        )
    )
    return saved_files


def rewrite_project_artifacts(manifest, artifact_group="scaffold", app_root="generated_app"):
    if artifact_group == "scaffold":
        return rewrite_project_scaffold(manifest, app_root=app_root)

    prefixes = ARTIFACT_FILE_PREFIXES[artifact_group]
    files = [
        (path, content)
        for path, content in build_project_files(manifest)
        if path.startswith(prefixes) or path in prefixes
    ]
    saved_files = save_project_files(files, app_root=app_root, validate_required=False)
    saved_files.extend(
        save_project_files(
            [("manifest.json", json.dumps(manifest, indent=2) + "\n")],
            app_root=app_root,
            validate_required=False,
        )
    )
    return saved_files


def artifact_group_for_failure(failure_stage, error_text=""):
    stage = (failure_stage or "").strip().lower()
    if stage in FAILURE_STAGE_ARTIFACTS:
        return FAILURE_STAGE_ARTIFACTS[stage]

    lowered = (error_text or "").lower()
    if "frontend" in lowered or "npm" in lowered or "vite" in lowered:
        return "frontend"
    if "docker" in lowered or "uvicorn" in lowered or "fastapi" in lowered or "backend" in lowered:
        return "backend"
    if "deploy" in lowered or "render" in lowered or "railway" in lowered:
        return "deploy"
    return "scaffold"


def repair_project_from_output(output_text, app_root="generated_app", intake_context=None, spec_brief=None):
    manifest, manifest_text = canonicalize_manifest_output(
        output_text,
        intake_context=intake_context,
        spec_brief=spec_brief,
    )
    saved_files = rewrite_project_scaffold(manifest, app_root=app_root)
    validate_project_scaffold(app_root)
    return {
        "manifest": manifest,
        "manifest_text": manifest_text,
        "saved_files": saved_files,
    }


def repair_project_for_failure(
    output_text,
    app_root="generated_app",
    intake_context=None,
    spec_brief=None,
    failure_stage=None,
    error_text="",
):
    manifest, manifest_text = canonicalize_manifest_output(
        output_text,
        intake_context=intake_context,
        spec_brief=spec_brief,
    )
    artifact_group = artifact_group_for_failure(failure_stage, error_text=error_text)
    saved_files = rewrite_project_artifacts(manifest, artifact_group=artifact_group, app_root=app_root)
    validate_project_scaffold(app_root)
    return {
        "manifest": manifest,
        "manifest_text": manifest_text,
        "saved_files": saved_files,
        "artifact_group": artifact_group,
    }
