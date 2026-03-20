import json
import re
from copy import deepcopy

from engine.file_writer import GeneratedProjectError
from templates.families import (
    apply_family_entity_plan,
    apply_family_pages_plan,
    apply_family_routes_plan,
    apply_family_samples_plan,
    get_family_manifest_defaults,
    get_product_boundary,
    get_family_schema_requirements,
    get_scaffold_family,
)


DEFAULT_MANIFEST = {
    "app_name": "Generated SaaS",
    "slug": "generated-saas",
    "app_type": "saas_dashboard",
    "tagline": "A prompt-built SaaS dashboard",
    "summary": "A lightweight SaaS starter generated from a structured manifest.",
    "primary_entity": "Work Item",
    "scaffold_family": get_scaffold_family("saas_dashboard"),
    "theme": {
        "primary_color": "#0f766e",
        "accent_color": "#f59e0b",
        "surface_color": "#ecfeff",
    },
    "dashboard": {
        "headline": "Operations overview",
        "subheadline": "A starter dashboard scaffolded from the prompt.",
        "sections": [
            {"title": "Pipeline", "description": "Track the active work moving through the system."},
            {"title": "Customers", "description": "Review the latest accounts and engagement signals."},
        ],
    },
    "pages": [
        {
            "name": "Overview",
            "purpose": "See the state of the business at a glance.",
            "layout": "dashboard",
            "widgets": ["summary_cards", "activity_feed"],
        },
        {
            "name": "Records",
            "purpose": "Browse and manage the primary records.",
            "layout": "table",
            "widgets": ["record_grid", "entity_form"],
        },
    ],
    "workflows": [
        {
            "name": "Triage incoming work",
            "steps": ["Capture", "Assign", "Complete"],
            "trigger": "manual",
            "owner_role": "manager",
            "states": ["new", "assigned", "completed"],
        },
        {
            "name": "Review weekly health",
            "steps": ["Measure", "Discuss", "Act"],
            "trigger": "scheduled",
            "owner_role": "owner",
            "states": ["measure", "review", "actioned"],
        },
    ],
    "auth": {
        "enabled": True,
        "roles": ["owner", "manager", "member", "viewer"],
        "demo_users": [
            {"name": "Avery", "email": "avery@example.com", "role": "owner"},
            {"name": "Morgan", "email": "morgan@example.com", "role": "viewer"},
        ],
    },
    "capabilities": {
        "search": True,
        "notifications": True,
        "automation": True,
    },
    "integrations": {
        "email": "sendgrid",
        "payments": "stripe",
        "storage": "s3",
        "webhook_topics": ["record.created", "record.updated"],
    },
    "permissions": [
        {"resource": "WorkItem", "actions": ["create", "read", "update", "delete"], "roles": ["owner", "manager", "member"]},
        {"resource": "Dashboard", "actions": ["read"], "roles": ["owner", "manager", "member", "viewer"]},
    ],
    "layout": {
        "navigation_style": "tabs",
        "density": "comfortable",
        "panels": ["search", "automation", "records"],
    },
    "family_modules": ["dashboard_core"],
    "generator_boundary": get_product_boundary(),
    "support_tier": "supported",
    "closest_family": "saas_dashboard",
    "refinement_steps": [
        "Map the request to the closest supported family.",
        "Generate a family-based starter scaffold rather than bespoke arbitrary code.",
    ],
    "handoff_notes": [],
    "spec_brief": {
        "goal": "Build a family-based application starter from the prompt.",
        "primary_users": ["operator", "customer"],
        "core_entities": ["record"],
        "core_workflows": ["operational workflow"],
        "page_intents": ["overview dashboard", "records management"],
        "integration_hints": [],
        "risk_flags": [],
        "clarification_prompts": [
            "Confirm the main success metric for the first release.",
            "Confirm the highest-priority workflow to optimize first.",
        ],
    },
    "data_model": [
        {
            "name": "WorkItem",
            "fields": [
                {"name": "title", "type": "string"},
                {"name": "status", "type": "string"},
                {"name": "owner", "type": "string"},
            ],
        }
    ],
    "api_routes": [
        {"path": "/items", "method": "GET", "summary": "List work items"},
        {"path": "/summary", "method": "GET", "summary": "Get dashboard summary"},
    ],
    "sample_records": [
        {"title": "Onboard first customer", "status": "active", "owner": "ops"},
        {"title": "Publish metrics dashboard", "status": "planned", "owner": "product"},
    ],
}

APP_TYPES = {
    "saas_dashboard",
    "crm_platform",
    "support_desk",
    "project_management",
    "recruiting_platform",
    "inventory_management",
    "finance_ops",
    "internal_tool",
    "marketplace",
    "booking_platform",
    "content_platform",
    "social_app",
    "learning_platform",
    "ecommerce_app",
}


def _extract_json_blob(text):
    fenced_match = re.search(r"```json\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced_match:
        return fenced_match.group(1)

    brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if brace_match:
        return brace_match.group(1)

    raise GeneratedProjectError("No JSON object was found in the generated output.")


def _merge(default_value, incoming_value):
    if isinstance(default_value, dict):
        result = deepcopy(default_value)
        if isinstance(incoming_value, dict):
            for key, value in incoming_value.items():
                result[key] = _merge(result.get(key), value) if key in result else value
        return result

    if isinstance(default_value, list):
        return incoming_value if isinstance(incoming_value, list) and incoming_value else deepcopy(default_value)

    return incoming_value if incoming_value not in (None, "") else default_value


def _ensure_list_of_dicts(items, field_name):
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise GeneratedProjectError(f"Manifest field '{field_name}' must be a list of objects.")


def _normalize_pages(pages):
    normalized_pages = []
    for page in pages:
        entry = deepcopy(page)
        if not isinstance(entry.get("name"), str) or not entry["name"].strip():
            raise GeneratedProjectError("Each page must include a non-empty name.")
        if not isinstance(entry.get("purpose"), str) or not entry["purpose"].strip():
            raise GeneratedProjectError("Each page must include a non-empty purpose.")
        entry["name"] = entry["name"].strip()
        entry["purpose"] = entry["purpose"].strip()
        layout = entry.get("layout") or ("dashboard" if entry["name"].lower() == "overview" else "workspace")
        if not isinstance(layout, str) or not layout.strip():
            raise GeneratedProjectError("Each page layout must be a non-empty string.")
        widgets = entry.get("widgets")
        if widgets is None:
            widgets = ["summary_cards"] if layout == "dashboard" else ["record_grid"]
        if not isinstance(widgets, list) or not all(isinstance(widget, str) and widget.strip() for widget in widgets):
            raise GeneratedProjectError("Each page.widgets field must be a list of non-empty strings.")
        entry["layout"] = layout.strip()
        entry["widgets"] = [widget.strip() for widget in widgets][:6]
        normalized_pages.append(entry)
    return normalized_pages


def _normalize_workflows(workflows, auth_roles):
    normalized_workflows = []
    default_role = auth_roles[0] if auth_roles else "owner"
    for workflow in workflows:
        entry = deepcopy(workflow)
        if not isinstance(entry.get("name"), str) or not entry["name"].strip():
            raise GeneratedProjectError("Each workflow must include a non-empty name.")
        steps = entry.get("steps")
        if not isinstance(steps, list) or not all(isinstance(step, str) and step.strip() for step in steps):
            raise GeneratedProjectError("Each workflow.steps field must be a list of non-empty strings.")
        entry["name"] = entry["name"].strip()
        entry["steps"] = [step.strip() for step in steps][:8]
        trigger = entry.get("trigger") or "manual"
        owner_role = entry.get("owner_role") or default_role
        states = entry.get("states") or [re.sub(r"[^a-z0-9]+", "_", step.lower()).strip("_") or "step" for step in entry["steps"]]
        if not isinstance(trigger, str) or not trigger.strip():
            raise GeneratedProjectError("Each workflow.trigger field must be a non-empty string.")
        if not isinstance(owner_role, str) or not owner_role.strip():
            raise GeneratedProjectError("Each workflow.owner_role field must be a non-empty string.")
        if not isinstance(states, list) or not all(isinstance(state, str) and state.strip() for state in states):
            raise GeneratedProjectError("Each workflow.states field must be a list of non-empty strings.")
        entry["trigger"] = trigger.strip()
        entry["owner_role"] = owner_role.strip()
        entry["states"] = [state.strip() for state in states][:8]
        normalized_workflows.append(entry)
    return normalized_workflows


def _normalize_permissions(permissions, auth_roles, primary_entity):
    normalized_permissions = []
    using_defaults = not (isinstance(permissions, list) and permissions)
    entries = permissions if isinstance(permissions, list) and permissions else deepcopy(DEFAULT_MANIFEST["permissions"])
    role_set = {role.strip() for role in auth_roles}
    for permission in entries:
        if not isinstance(permission, dict):
            raise GeneratedProjectError("Manifest field 'permissions' must be a list of objects.")
        resource = str(permission.get("resource") or primary_entity).strip()
        if resource == "WorkItem":
            resource = primary_entity
        actions = permission.get("actions") or ["read"]
        roles = permission.get("roles") or auth_roles[:]
        if using_defaults:
            roles = [role for role in roles if role.strip() in role_set] or auth_roles[:]
        if not resource:
            raise GeneratedProjectError("Each permission.resource field must be a non-empty string.")
        if not isinstance(actions, list) or not all(isinstance(action, str) and action.strip() for action in actions):
            raise GeneratedProjectError("Each permission.actions field must be a list of non-empty strings.")
        if not isinstance(roles, list) or not all(isinstance(role, str) and role.strip() for role in roles):
            raise GeneratedProjectError("Each permission.roles field must be a list of non-empty strings.")
        unknown_roles = [role for role in roles if role.strip() not in role_set]
        if unknown_roles:
            raise GeneratedProjectError("Each permission role must exist in auth.roles.")
        normalized_permissions.append(
            {
                "resource": resource,
                "actions": [action.strip() for action in actions][:8],
                "roles": [role.strip() for role in roles][:8],
            }
        )
    return normalized_permissions


def _normalize_layout(layout, scaffold_family):
    merged = _merge(DEFAULT_MANIFEST["layout"], layout if isinstance(layout, dict) else {})
    for field_name in ("navigation_style", "density"):
        value = merged.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise GeneratedProjectError(f"Manifest field 'layout.{field_name}' must be a non-empty string.")
        merged[field_name] = value.strip()
    panels = merged.get("panels", [])
    if not isinstance(panels, list) or not all(isinstance(panel, str) and panel.strip() for panel in panels):
        raise GeneratedProjectError("Manifest field 'layout.panels' must be a list of non-empty strings.")
    merged["panels"] = [panel.strip() for panel in panels][:8]
    if not merged["navigation_style"]:
        merged["navigation_style"] = scaffold_family.get("navigation_style", "tabs")
    return merged


def _normalize_spec_brief(spec_brief, intake_context, app_type):
    merged = _merge(DEFAULT_MANIFEST["spec_brief"], spec_brief if isinstance(spec_brief, dict) else {})
    if intake_context:
        merged["closest_family"] = intake_context["closest_family"]
        merged["support_tier"] = intake_context["support_tier"]
    else:
        merged["closest_family"] = app_type
        merged["support_tier"] = merged.get("support_tier") or "supported"

    if not isinstance(merged.get("goal"), str) or not merged["goal"].strip():
        raise GeneratedProjectError("Manifest field 'spec_brief.goal' must be a non-empty string.")
    merged["goal"] = merged["goal"].strip()

    for field_name in (
        "primary_users",
        "core_entities",
        "core_workflows",
        "page_intents",
        "integration_hints",
        "risk_flags",
        "clarification_prompts",
    ):
        value = merged.get(field_name)
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            raise GeneratedProjectError(f"Manifest field 'spec_brief.{field_name}' must be a list of non-empty strings.")
        merged[field_name] = [item.strip() for item in value][:6]

    if merged.get("closest_family") not in APP_TYPES:
        raise GeneratedProjectError("Manifest field 'spec_brief.closest_family' must be one of the supported app types.")
    if merged.get("support_tier") not in {"supported", "starter_only", "out_of_scope"}:
        raise GeneratedProjectError("Manifest field 'spec_brief.support_tier' must be supported, starter_only, or out_of_scope.")
    return merged


def _normalize_family_modules(family_modules, app_type):
    modules = family_modules if isinstance(family_modules, list) and family_modules else []
    modules = [module for module in modules if isinstance(module, str) and module.strip()]
    modules = [module.strip() for module in modules]
    if "dashboard_core" not in modules:
        modules.insert(0, "dashboard_core")
    if app_type not in {"saas_dashboard"}:
        family_module = f"{app_type}_module"
        if family_module not in modules:
            modules.append(family_module)
    return modules[:8]


def _validate_family_schema_requirements(app_type, data_model):
    requirements = get_family_schema_requirements(app_type)
    if not requirements:
        return

    field_names = {
        str(field.get("name", "")).strip().lower()
        for entity in data_model
        for field in entity.get("fields", [])
        if isinstance(field, dict)
    }

    for required_name in requirements.get("required_field_names", ()):
        if required_name.lower() not in field_names:
            raise GeneratedProjectError(
                f"Manifest data_model for '{app_type}' must include a field named '{required_name}'."
            )

    any_names = tuple(requirements.get("required_any_field_names", ()))
    if any_names and not any(name.lower() in field_names for name in any_names):
        joined = ", ".join(any_names)
        raise GeneratedProjectError(
            f"Manifest data_model for '{app_type}' must include at least one of these fields: {joined}."
        )

    for group in requirements.get("required_field_groups", ()):
        lowered = tuple(name.lower() for name in group)
        if not any(name in field_names for name in lowered):
            joined = ", ".join(group)
            raise GeneratedProjectError(
                f"Manifest data_model for '{app_type}' must include at least one of these fields: {joined}."
            )


def normalize_manifest(manifest, intake_context=None, spec_brief=None):
    preliminary = _merge(DEFAULT_MANIFEST, manifest)

    app_type = preliminary.get("app_type")
    if not isinstance(app_type, str) or not app_type.strip():
        raise GeneratedProjectError("Manifest field 'app_type' must be a non-empty string.")
    app_type = app_type.strip()
    if app_type not in APP_TYPES:
        allowed = ", ".join(sorted(APP_TYPES))
        raise GeneratedProjectError(f"Manifest field 'app_type' must be one of: {allowed}")

    family_defaults = get_family_manifest_defaults(app_type)
    normalized = _merge(_merge(DEFAULT_MANIFEST, family_defaults), manifest)

    for field_name in ("app_name", "slug", "app_type", "tagline", "summary", "primary_entity"):
        if not isinstance(normalized[field_name], str) or not normalized[field_name].strip():
            raise GeneratedProjectError(f"Manifest field '{field_name}' must be a non-empty string.")
        normalized[field_name] = normalized[field_name].strip()

    slug = normalized["slug"].strip().lower()
    slug = re.sub(r"[^a-z0-9-]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        raise GeneratedProjectError("Manifest field 'slug' could not be normalized into a valid slug.")
    normalized["slug"] = slug

    normalized["scaffold_family"] = get_scaffold_family(normalized["app_type"])
    normalized["generator_boundary"] = get_product_boundary()
    if intake_context:
        normalized["support_tier"] = intake_context["support_tier"]
        normalized["closest_family"] = intake_context["closest_family"]
        normalized["refinement_steps"] = intake_context["refinement_steps"]
        normalized["handoff_notes"] = intake_context["handoff_notes"]
    else:
        normalized["closest_family"] = normalized["app_type"]
    normalized["spec_brief"] = _normalize_spec_brief(
        spec_brief if spec_brief is not None else normalized.get("spec_brief", {}),
        intake_context=intake_context,
        app_type=normalized["app_type"],
    )
    normalized["data_model"] = apply_family_entity_plan(
        normalized["app_type"],
        normalized.get("data_model", []),
        normalized.get("primary_entity"),
    )
    normalized["pages"] = apply_family_pages_plan(normalized["app_type"], normalized.get("pages", []))
    normalized["api_routes"] = apply_family_routes_plan(normalized["app_type"], normalized.get("api_routes", []))
    normalized["sample_records"] = apply_family_samples_plan(
        normalized["app_type"], normalized.get("sample_records", [])
    )

    for color_key in ("primary_color", "accent_color", "surface_color"):
        color_value = normalized["theme"].get(color_key)
        if not isinstance(color_value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color_value):
            raise GeneratedProjectError(f"Manifest theme field '{color_key}' must be a hex color like #0f766e.")

    auth = normalized.get("auth", {})
    if not isinstance(auth, dict):
        raise GeneratedProjectError("Manifest field 'auth' must be an object.")
    if not isinstance(auth.get("enabled"), bool):
        raise GeneratedProjectError("Manifest field 'auth.enabled' must be a boolean.")
    if not isinstance(auth.get("roles"), list) or not all(isinstance(role, str) and role.strip() for role in auth["roles"]):
        raise GeneratedProjectError("Manifest field 'auth.roles' must be a list of non-empty strings.")
    _ensure_list_of_dicts(auth.get("demo_users", []), "auth.demo_users")
    if not auth["demo_users"]:
        raise GeneratedProjectError("Manifest field 'auth.demo_users' must contain at least one demo user.")
    auth["roles"] = [role.strip() for role in auth["roles"] if role.strip()]

    capabilities = normalized.get("capabilities", {})
    if not isinstance(capabilities, dict):
        raise GeneratedProjectError("Manifest field 'capabilities' must be an object.")
    for capability_name in ("search", "notifications", "automation"):
        if not isinstance(capabilities.get(capability_name), bool):
            raise GeneratedProjectError(f"Manifest field 'capabilities.{capability_name}' must be a boolean.")

    integrations = normalized.get("integrations", {})
    if not isinstance(integrations, dict):
        raise GeneratedProjectError("Manifest field 'integrations' must be an object.")
    for provider_name in ("email", "payments", "storage"):
        if not isinstance(integrations.get(provider_name), str) or not integrations[provider_name].strip():
            raise GeneratedProjectError(f"Manifest field 'integrations.{provider_name}' must be a non-empty string.")
    if not isinstance(integrations.get("webhook_topics"), list) or not all(isinstance(topic, str) and topic.strip() for topic in integrations["webhook_topics"]):
        raise GeneratedProjectError("Manifest field 'integrations.webhook_topics' must be a list of non-empty strings.")

    _ensure_list_of_dicts(normalized["dashboard"]["sections"], "dashboard.sections")
    _ensure_list_of_dicts(normalized["pages"], "pages")
    _ensure_list_of_dicts(normalized["workflows"], "workflows")
    _ensure_list_of_dicts(normalized["data_model"], "data_model")
    _ensure_list_of_dicts(normalized["api_routes"], "api_routes")
    _ensure_list_of_dicts(normalized["sample_records"], "sample_records")
    normalized["pages"] = _normalize_pages(normalized["pages"])
    normalized["workflows"] = _normalize_workflows(normalized["workflows"], auth["roles"])
    normalized["permissions"] = _normalize_permissions(
        manifest.get("permissions"), auth["roles"], normalized["primary_entity"]
    )
    normalized["layout"] = _normalize_layout(normalized.get("layout", {}), normalized["scaffold_family"])
    normalized["family_modules"] = _normalize_family_modules(
        normalized.get("family_modules", []), normalized["app_type"]
    )
    if normalized.get("closest_family") not in APP_TYPES:
        raise GeneratedProjectError("Manifest field 'closest_family' must be one of the supported app types.")
    if normalized.get("support_tier") not in {"supported", "starter_only", "out_of_scope"}:
        raise GeneratedProjectError("Manifest field 'support_tier' must be supported, starter_only, or out_of_scope.")
    if not isinstance(normalized.get("refinement_steps"), list) or not all(isinstance(step, str) and step.strip() for step in normalized["refinement_steps"]):
        raise GeneratedProjectError("Manifest field 'refinement_steps' must be a list of non-empty strings.")
    if not isinstance(normalized.get("handoff_notes"), list) or not all(isinstance(note, str) and note.strip() for note in normalized["handoff_notes"]):
        raise GeneratedProjectError("Manifest field 'handoff_notes' must be a list of non-empty strings.")
    normalized["refinement_steps"] = [step.strip() for step in normalized["refinement_steps"]][:8]
    normalized["handoff_notes"] = [note.strip() for note in normalized["handoff_notes"]][:8]
    _validate_family_schema_requirements(normalized["app_type"], normalized["data_model"])

    if len(normalized["dashboard"]["sections"]) > 6:
        normalized["dashboard"]["sections"] = normalized["dashboard"]["sections"][:6]
    if len(normalized["pages"]) > 6:
        normalized["pages"] = normalized["pages"][:6]
    if len(normalized["workflows"]) > 6:
        normalized["workflows"] = normalized["workflows"][:6]
    if len(normalized["permissions"]) > 12:
        normalized["permissions"] = normalized["permissions"][:12]
    if len(normalized["data_model"]) > 5:
        normalized["data_model"] = normalized["data_model"][:5]
    if len(normalized["api_routes"]) > 8:
        normalized["api_routes"] = normalized["api_routes"][:8]
    if len(normalized["sample_records"]) > 12:
        normalized["sample_records"] = normalized["sample_records"][:12]
    if len(auth["roles"]) > 6:
        auth["roles"] = auth["roles"][:6]
    if len(auth["demo_users"]) > 8:
        auth["demo_users"] = auth["demo_users"][:8]

    if not normalized["pages"]:
        raise GeneratedProjectError("Manifest field 'pages' must contain at least one page.")
    if not normalized["workflows"]:
        raise GeneratedProjectError("Manifest field 'workflows' must contain at least one workflow.")

    role_set = {role.strip() for role in auth["roles"]}
    for user in auth["demo_users"]:
        if user.get("role") not in role_set:
            raise GeneratedProjectError("Each auth.demo_user role must exist in auth.roles.")
        if not user.get("email") or not user.get("name"):
            raise GeneratedProjectError("Each auth.demo_user must include name and email.")

    return normalized


def parse_manifest(output_text, intake_context=None, spec_brief=None):
    json_blob = _extract_json_blob(output_text)
    try:
        manifest = json.loads(json_blob)
    except json.JSONDecodeError as exc:
        raise GeneratedProjectError(f"Generated manifest is not valid JSON: {exc}") from exc

    if not isinstance(manifest, dict):
        raise GeneratedProjectError("Generated manifest must be a JSON object.")

    return normalize_manifest(manifest, intake_context=intake_context, spec_brief=spec_brief)
