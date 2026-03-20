from templates.family_extensions import (
    BOOKING_EXTENSION,
    CONTENT_EXTENSION,
    CRM_EXTENSION,
    ECOMMERCE_EXTENSION,
    FINANCE_EXTENSION,
    INTERNAL_TOOL_EXTENSION,
    INVENTORY_EXTENSION,
    LEARNING_EXTENSION,
    MARKETPLACE_EXTENSION,
    PROJECT_MANAGEMENT_EXTENSION,
    RECRUITING_EXTENSION,
    SOCIAL_EXTENSION,
    SUPPORT_EXTENSION,
)
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


def render_crm_project(manifest, previous_manifest=None, existing_migration_versions=None):
    return _materialize_project_files(build_dashboard_shell_project_files(manifest, previous_manifest, existing_migration_versions), CRM_EXTENSION)


def render_support_desk_project(manifest, previous_manifest=None, existing_migration_versions=None):
    return _materialize_project_files(build_dashboard_shell_project_files(manifest, previous_manifest, existing_migration_versions), SUPPORT_EXTENSION)


def render_project_management_project(manifest, previous_manifest=None, existing_migration_versions=None):
    return _materialize_project_files(build_dashboard_shell_project_files(manifest, previous_manifest, existing_migration_versions), PROJECT_MANAGEMENT_EXTENSION)


def render_recruiting_platform_project(manifest, previous_manifest=None, existing_migration_versions=None):
    return _materialize_project_files(build_dashboard_shell_project_files(manifest, previous_manifest, existing_migration_versions), RECRUITING_EXTENSION)


def render_inventory_management_project(manifest, previous_manifest=None, existing_migration_versions=None):
    return _materialize_project_files(build_dashboard_shell_project_files(manifest, previous_manifest, existing_migration_versions), INVENTORY_EXTENSION)


def render_finance_ops_project(manifest, previous_manifest=None, existing_migration_versions=None):
    return _materialize_project_files(build_dashboard_shell_project_files(manifest, previous_manifest, existing_migration_versions), FINANCE_EXTENSION)


def render_internal_tool_project(manifest, previous_manifest=None, existing_migration_versions=None):
    return _materialize_project_files(build_dashboard_shell_project_files(manifest, previous_manifest, existing_migration_versions), INTERNAL_TOOL_EXTENSION)


def render_marketplace_project(manifest, previous_manifest=None, existing_migration_versions=None):
    return _materialize_project_files(build_dashboard_shell_project_files(manifest, previous_manifest, existing_migration_versions), MARKETPLACE_EXTENSION)


def render_booking_platform_project(manifest, previous_manifest=None, existing_migration_versions=None):
    return _materialize_project_files(build_dashboard_shell_project_files(manifest, previous_manifest, existing_migration_versions), BOOKING_EXTENSION)


def render_content_platform_project(manifest, previous_manifest=None, existing_migration_versions=None):
    return _materialize_project_files(build_dashboard_shell_project_files(manifest, previous_manifest, existing_migration_versions), CONTENT_EXTENSION)


def render_social_app_project(manifest, previous_manifest=None, existing_migration_versions=None):
    return _materialize_project_files(build_dashboard_shell_project_files(manifest, previous_manifest, existing_migration_versions), SOCIAL_EXTENSION)


def render_learning_platform_project(manifest, previous_manifest=None, existing_migration_versions=None):
    return _materialize_project_files(build_dashboard_shell_project_files(manifest, previous_manifest, existing_migration_versions), LEARNING_EXTENSION)


def render_ecommerce_project(manifest, previous_manifest=None, existing_migration_versions=None):
    return _materialize_project_files(build_dashboard_shell_project_files(manifest, previous_manifest, existing_migration_versions), ECOMMERCE_EXTENSION)


PROJECT_RENDERERS = {
    "saas_dashboard": render_saas_dashboard_project,
    "crm_platform": render_crm_project,
    "support_desk": render_support_desk_project,
    "project_management": render_project_management_project,
    "recruiting_platform": render_recruiting_platform_project,
    "inventory_management": render_inventory_management_project,
    "finance_ops": render_finance_ops_project,
    "internal_tool": render_internal_tool_project,
    "marketplace": render_marketplace_project,
    "booking_platform": render_booking_platform_project,
    "content_platform": render_content_platform_project,
    "social_app": render_social_app_project,
    "learning_platform": render_learning_platform_project,
    "ecommerce_app": render_ecommerce_project,
}


def build_project_files(manifest, previous_manifest=None, existing_migration_versions=None):
    return PROJECT_RENDERERS[manifest["app_type"]](manifest, previous_manifest, existing_migration_versions)
