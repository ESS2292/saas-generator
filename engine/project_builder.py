import json
import re
from pathlib import Path

from engine.file_writer import save_project_files
from engine.manifest import parse_manifest
from templates.renderers import build_project_files


def build_project_from_manifest(output_text, app_root="generated_app", intake_context=None, spec_brief=None):
    root = Path(app_root)
    previous_manifest = None
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        try:
            previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous_manifest = None

    existing_migration_versions = []
    migrations_root = root / "backend" / "migrations"
    if migrations_root.exists():
        for path in migrations_root.glob("*.sql"):
            match = re.match(r"(\d{4})_", path.name)
            if match:
                existing_migration_versions.append(int(match.group(1)))
    if not existing_migration_versions:
        existing_migration_versions = [1]

    manifest = parse_manifest(output_text, intake_context=intake_context, spec_brief=spec_brief)
    files = build_project_files(manifest, previous_manifest=previous_manifest, existing_migration_versions=existing_migration_versions)
    saved_files = save_project_files(files, app_root=app_root)
    manifest_file = [("manifest.json", json.dumps(manifest, indent=2) + "\n")]
    saved_files.extend(save_project_files(manifest_file, app_root=app_root, validate_required=False))
    return manifest, saved_files
