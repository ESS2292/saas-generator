from functools import partial

from templates.family_extensions import get_family_pack
from templates.scaffold import build_dashboard_shell_project_files


FAMILY_SLOT_DEFAULTS = {
    "__FAMILY_BACKEND_IMPORTS__": "",
    "__FAMILY_BACKEND_ROUTES__": "",
    "__FAMILY_FRONTEND_IMPORTS__": "",
    "__FAMILY_FRONTEND_STATE__": "",
    "__FAMILY_FRONTEND_LOADERS__": "",
    "__FAMILY_FRONTEND_LOAD_DATA__": "",
    "__FAMILY_FRONTEND_AFTER_NOTIFICATION__": "",
    "__FAMILY_FRONTEND_AFTER_INTEGRATION__": "",
    "__FAMILY_FRONTEND_PANEL__": "",
}


def _build_family_slots(extension=None):
    slots = dict(FAMILY_SLOT_DEFAULTS)
    if not extension:
        return slots

    slots["__FAMILY_BACKEND_IMPORTS__"] = extension.get("backend_import", "")
    slots["__FAMILY_BACKEND_ROUTES__"] = extension.get("backend_routes", "")

    frontend = extension.get("frontend", {})
    slots["__FAMILY_FRONTEND_IMPORTS__"] = extension.get("frontend_import", "")
    slots["__FAMILY_FRONTEND_STATE__"] = frontend.get("state", "")
    slots["__FAMILY_FRONTEND_LOADERS__"] = frontend.get("loader", "")
    slots["__FAMILY_FRONTEND_LOAD_DATA__"] = frontend.get("load_data", "")
    slots["__FAMILY_FRONTEND_AFTER_NOTIFICATION__"] = frontend.get("after_notification", "")
    slots["__FAMILY_FRONTEND_AFTER_INTEGRATION__"] = frontend.get("after_integration", "")
    slots["__FAMILY_FRONTEND_PANEL__"] = frontend.get("panel", "")
    return slots


def _materialize_slots(content, slots):
    for marker, replacement in slots.items():
        content = content.replace(marker, replacement)
    return content


def _materialize_project_files(files, extension=None):
    slots = _build_family_slots(extension)
    rendered_files = []
    for path, content in files:
        rendered_files.append((path, _materialize_slots(content, slots)))

    if extension and extension.get("backend_module_path") and extension.get("backend_module_source"):
        rendered_files.append((extension["backend_module_path"], extension["backend_module_source"].rstrip() + "\n"))
    if extension and extension.get("frontend_module_path") and extension.get("frontend_module_source"):
        rendered_files.append((extension["frontend_module_path"], extension["frontend_module_source"].rstrip() + "\n"))
    return rendered_files


def render_saas_dashboard_project(manifest, previous_manifest=None, existing_migration_versions=None):
    return _materialize_project_files(build_dashboard_shell_project_files(manifest, previous_manifest, existing_migration_versions))


def _render_family_project(app_type, manifest, previous_manifest=None, existing_migration_versions=None):
    pack = get_family_pack(app_type)
    extension = pack.extension if pack else None
    return _materialize_project_files(
        build_dashboard_shell_project_files(manifest, previous_manifest, existing_migration_versions),
        extension,
    )


PROJECT_RENDERERS = {
    "saas_dashboard": render_saas_dashboard_project,
    "crm_platform": partial(_render_family_project, "crm_platform"),
    "support_desk": partial(_render_family_project, "support_desk"),
    "project_management": partial(_render_family_project, "project_management"),
    "recruiting_platform": partial(_render_family_project, "recruiting_platform"),
    "inventory_management": partial(_render_family_project, "inventory_management"),
    "finance_ops": partial(_render_family_project, "finance_ops"),
    "internal_tool": partial(_render_family_project, "internal_tool"),
    "marketplace": partial(_render_family_project, "marketplace"),
    "booking_platform": partial(_render_family_project, "booking_platform"),
    "content_platform": partial(_render_family_project, "content_platform"),
    "social_app": partial(_render_family_project, "social_app"),
    "learning_platform": partial(_render_family_project, "learning_platform"),
    "ecommerce_app": partial(_render_family_project, "ecommerce_app"),
}


def build_project_files(manifest, previous_manifest=None, existing_migration_versions=None):
    return PROJECT_RENDERERS[manifest["app_type"]](manifest, previous_manifest, existing_migration_versions)
