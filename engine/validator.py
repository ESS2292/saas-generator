import json
import re
from pathlib import Path

from engine.file_writer import GeneratedProjectError
from templates.family_extensions import FAMILY_PACKS


def _page_component_filename(page_name):
    component_name = f"{re.sub(r'[^A-Za-z0-9]', '', page_name.title()) or 'Generated'}Page"
    return f"{component_name}.jsx"


def _validate_family_specific_markers(app_type, backend_source, frontend_source):
    pack = FAMILY_PACKS.get(app_type)
    if not pack:
        return

    for marker in pack.backend_markers:
        if marker not in backend_source:
            raise GeneratedProjectError(f"Generated {app_type} scaffold is missing marker: {marker}")

    for marker in pack.frontend_markers:
        if marker not in frontend_source:
            raise GeneratedProjectError(f"Generated {app_type} scaffold is missing marker: {marker}")


def _validate_family_specific_files(app_type, root):
    if app_type not in FAMILY_PACKS:
        return

    backend_family_logic = root / "backend" / "family_logic.py"
    frontend_family_panel = root / "frontend" / "src" / "familyPanel.jsx"
    for path in (backend_family_logic, frontend_family_panel):
        if not path.exists():
            raise GeneratedProjectError(f"Generated {app_type} scaffold is missing required family file: {path}")


def validate_project_scaffold(app_root="generated_app"):
    root = Path(app_root)
    required_files = [
        root / ".env.example",
        root / "backend" / "main.py",
        root / "backend" / "app_config.py",
        root / "backend" / "app_core.py",
        root / "backend" / "database.py",
        root / "backend" / "providers.py",
        root / "backend" / "requirements.txt",
        root / "backend" / "Dockerfile",
        root / "backend" / ".env.example",
        root / "backend" / "seed_data.json",
        root / "backend" / "migrations" / "0001_initial.sql",
        root / "backend" / "migrations" / "schema_snapshot.json",
        root / "backend" / "migrations" / "history.json",
        root / "backend" / "migrations" / "README.md",
        root / "frontend" / "package.json",
        root / "frontend" / "src" / "App.jsx",
        root / "frontend" / "src" / "api.js",
        root / "frontend" / "src" / "appShell.jsx",
        root / "frontend" / "src" / "entityUtils.js",
        root / "frontend" / "src" / "routes.js",
        root / "frontend" / "src" / "pages" / "index.js",
        root / "frontend" / "src" / "pages" / "pageHelpers.jsx",
        root / "frontend" / "src" / "components" / "SummaryCards.jsx",
        root / "frontend" / "src" / "components" / "SearchPanel.jsx",
        root / "frontend" / "src" / "components" / "AutomationPanel.jsx",
        root / "frontend" / "src" / "components" / "EntityForm.jsx",
        root / "frontend" / "src" / "components" / "SectionsPanel.jsx",
        root / "frontend" / "src" / "components" / "WorkflowPanel.jsx",
        root / "frontend" / "src" / "components" / "IntegrationsPanel.jsx",
        root / "frontend" / "src" / "components" / "FeedPanels.jsx",
        root / "frontend" / "src" / "components" / "RecordGrid.jsx",
        root / "frontend" / "src" / "main.jsx",
        root / "deploy" / "docker-compose.yml",
        root / "deploy" / "render.yaml",
        root / "deploy" / "railway.json",
        root / "deploy" / "README.md",
    ]

    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    for page in manifest.get("pages", []):
        required_files.append(root / "frontend" / "src" / "pages" / _page_component_filename(page["name"]))

    missing_files = [str(path) for path in required_files if not path.exists()]
    if missing_files:
        raise GeneratedProjectError(f"Generated scaffold is missing required files: {', '.join(missing_files)}")

    backend_main_path = root / "backend" / "main.py"
    backend_main_source = backend_main_path.read_text(encoding="utf-8")
    compile(backend_main_source, str(backend_main_path), "exec")
    backend_path = root / "backend" / "app_core.py"
    backend_source = backend_path.read_text(encoding="utf-8")
    compile(backend_source, str(backend_path), "exec")
    if "from app_core import app" not in backend_main_source:
        raise GeneratedProjectError("Generated backend entrypoint does not import the shared app module.")
    backend_config_source = (root / "backend" / "app_config.py").read_text(encoding="utf-8")
    backend_database_source = (root / "backend" / "database.py").read_text(encoding="utf-8")
    if "FastAPI(" not in backend_source:
        raise GeneratedProjectError("Generated backend does not define a FastAPI application.")
    for marker in ("APP_CONFIG =", "DEMO_USERS =", "ENTITY_MAP =", "DEFAULT_FORM_VALUES =", "DATABASE_URL =", "PRIMARY_TABLE ="):
        if marker not in backend_config_source:
            raise GeneratedProjectError(f"Generated backend config is missing marker: {marker}")
    for marker in ("create_engine(", "SessionLocal = sessionmaker", "Base = declarative_base()"):
        if marker not in backend_database_source:
            raise GeneratedProjectError(f"Generated backend database module is missing marker: {marker}")
    for marker in ("@app.get('/api/entities')", "@app.get('/api/auth/session')", "@app.get('/api/search')", "@app.get('/api/notifications')", "@app.post('/api/automation/run')", "@app.get('/api/integrations')", "@app.post('/api/integrations/test')", "@app.post('/api/integrations/payment/checkout')", "@app.post('/api/integrations/email/send')", "@app.post('/api/integrations/storage/presign')", "@app.post('/api/webhooks/{provider}')", "Base.metadata.create_all", "PRIMARY_TABLE"):
        if marker not in backend_source:
            raise GeneratedProjectError(f"Generated backend is missing CRUD marker: {marker}")

    provider_source = (root / "backend" / "providers.py").read_text(encoding="utf-8")
    for marker in ("def build_checkout_session", "def send_email_message", "def build_storage_upload", "_missing_credentials", "https://api.stripe.com/v1/checkout/sessions", "https://api.sendgrid.com/v3/mail/send", "https://api.resend.com/emails", "X-Amz-Algorithm", "api.cloudinary.com"):
        if marker not in provider_source:
            raise GeneratedProjectError(f"Generated provider adapter is missing marker: {marker}")

    migration_source = (root / "backend" / "migrations" / "0001_initial.sql").read_text(encoding="utf-8")
    if "CREATE TABLE IF NOT EXISTS" not in migration_source:
        raise GeneratedProjectError("Generated migration does not define any tables.")
    schema_snapshot = json.loads((root / "backend" / "migrations" / "schema_snapshot.json").read_text(encoding="utf-8"))
    migration_history = json.loads((root / "backend" / "migrations" / "history.json").read_text(encoding="utf-8"))
    migration_readme = (root / "backend" / "migrations" / "README.md").read_text(encoding="utf-8")
    if not schema_snapshot.get("entities"):
        raise GeneratedProjectError("Generated schema snapshot is missing entity definitions.")
    if migration_history.get("current_version", 0) < 1 or not migration_history.get("migrations"):
        raise GeneratedProjectError("Generated migration history is missing versions.")
    if "schema_snapshot.json" not in migration_readme or "NNNN_schema_update.sql" not in migration_readme:
        raise GeneratedProjectError("Generated migration README is missing schema evolution guidance.")
    for migration_entry in migration_history["migrations"]:
        path = root / "backend" / "migrations" / migration_entry["file"]
        if not path.exists():
            raise GeneratedProjectError(f"Generated migration history references a missing file: {migration_entry['file']}")

    root_env_source = (root / ".env.example").read_text(encoding="utf-8")
    for marker in ("APP_NAME=", "EMAIL_API_KEY=", "PAYMENTS_SECRET_KEY="):
        if marker not in root_env_source:
            raise GeneratedProjectError(f"Generated root env example is missing marker: {marker}")

    compose_source = (root / "deploy" / "docker-compose.yml").read_text(encoding="utf-8")
    for marker in ("services:", "backend:", "frontend:"):
        if marker not in compose_source:
            raise GeneratedProjectError(f"Generated docker compose file is missing marker: {marker}")

    render_source = (root / "deploy" / "render.yaml").read_text(encoding="utf-8")
    if "services:" not in render_source:
        raise GeneratedProjectError("Generated Render config is missing services.")

    railway_source = (root / "deploy" / "railway.json").read_text(encoding="utf-8")
    if "\"build\"" not in railway_source or "\"deploy\"" not in railway_source:
        raise GeneratedProjectError("Generated Railway config is missing build/deploy sections.")

    package_json = json.loads((root / "frontend" / "package.json").read_text(encoding="utf-8"))
    dependencies = package_json.get("dependencies", {})
    scripts = package_json.get("scripts", {})
    for script_name in ("dev", "build", "preview"):
        if script_name not in scripts:
            raise GeneratedProjectError(f"Frontend package.json is missing the '{script_name}' script.")
    if "react-router-dom" not in dependencies:
        raise GeneratedProjectError("Frontend package.json is missing the react-router-dom dependency.")

    frontend_entry_source = (root / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    if "import AppShell from './appShell.jsx'" not in frontend_entry_source or "BrowserRouter" not in frontend_entry_source:
        raise GeneratedProjectError("Generated frontend entrypoint does not wrap the shared app shell in the router.")
    frontend_api_source = (root / "frontend" / "src" / "api.js").read_text(encoding="utf-8")
    frontend_utils_source = (root / "frontend" / "src" / "entityUtils.js").read_text(encoding="utf-8")
    frontend_routes_source = (root / "frontend" / "src" / "routes.js").read_text(encoding="utf-8")
    frontend_pages_index_source = (root / "frontend" / "src" / "pages" / "index.js").read_text(encoding="utf-8")
    frontend_page_helpers_source = (root / "frontend" / "src" / "pages" / "pageHelpers.jsx").read_text(encoding="utf-8")
    frontend_summary_source = (root / "frontend" / "src" / "components" / "SummaryCards.jsx").read_text(encoding="utf-8")
    frontend_search_source = (root / "frontend" / "src" / "components" / "SearchPanel.jsx").read_text(encoding="utf-8")
    frontend_automation_source = (root / "frontend" / "src" / "components" / "AutomationPanel.jsx").read_text(encoding="utf-8")
    frontend_form_source = (root / "frontend" / "src" / "components" / "EntityForm.jsx").read_text(encoding="utf-8")
    frontend_sections_source = (root / "frontend" / "src" / "components" / "SectionsPanel.jsx").read_text(encoding="utf-8")
    frontend_workflow_source = (root / "frontend" / "src" / "components" / "WorkflowPanel.jsx").read_text(encoding="utf-8")
    frontend_integrations_source = (root / "frontend" / "src" / "components" / "IntegrationsPanel.jsx").read_text(encoding="utf-8")
    frontend_feed_panels_source = (root / "frontend" / "src" / "components" / "FeedPanels.jsx").read_text(encoding="utf-8")
    frontend_grid_source = (root / "frontend" / "src" / "components" / "RecordGrid.jsx").read_text(encoding="utf-8")
    frontend_source = (root / "frontend" / "src" / "appShell.jsx").read_text(encoding="utf-8")
    for marker in ("export const API_BASE =", "export async function requestJson"):
        if marker not in frontend_api_source:
            raise GeneratedProjectError(f"Generated frontend API module is missing marker: {marker}")
    for marker in ("export function entityToTableName", "export function formatRecordValue"):
        if marker not in frontend_utils_source:
            raise GeneratedProjectError(f"Generated frontend utility module is missing marker: {marker}")
    if "export const APP_ROUTES =" not in frontend_routes_source:
        raise GeneratedProjectError("Generated frontend routes module is missing the APP_ROUTES export.")
    if "export const PAGE_COMPONENTS =" not in frontend_pages_index_source:
        raise GeneratedProjectError("Generated frontend page index is missing the PAGE_COMPONENTS export.")
    if "export default function GeneratedPageLayout" not in frontend_page_helpers_source:
        raise GeneratedProjectError("Generated frontend page helpers module is missing the GeneratedPageLayout export.")
    if "export default function SummaryCards" not in frontend_summary_source:
        raise GeneratedProjectError("Generated frontend summary card component is missing the SummaryCards export.")
    if "export default function SearchPanel" not in frontend_search_source:
        raise GeneratedProjectError("Generated frontend search component is missing the SearchPanel export.")
    if "export default function AutomationPanel" not in frontend_automation_source:
        raise GeneratedProjectError("Generated frontend automation component is missing the AutomationPanel export.")
    if "export default function EntityForm" not in frontend_form_source:
        raise GeneratedProjectError("Generated frontend form component is missing the EntityForm export.")
    if "export default function SectionsPanel" not in frontend_sections_source:
        raise GeneratedProjectError("Generated frontend sections component is missing the SectionsPanel export.")
    if "export default function WorkflowPanel" not in frontend_workflow_source:
        raise GeneratedProjectError("Generated frontend workflow component is missing the WorkflowPanel export.")
    if "export default function IntegrationsPanel" not in frontend_integrations_source:
        raise GeneratedProjectError("Generated frontend integrations component is missing the IntegrationsPanel export.")
    for marker in ("export function IntegrationEventsPanel", "export function ProviderResponsesPanel", "export function NotificationsPanel", "export function EntityMapPanel"):
        if marker not in frontend_feed_panels_source:
            raise GeneratedProjectError(f"Generated frontend feed panel module is missing marker: {marker}")
    if "export default function RecordGrid" not in frontend_grid_source:
        raise GeneratedProjectError("Generated frontend record grid component is missing the RecordGrid export.")
    for marker in ("handleSaveRecord", "handleDeleteRecord", "beginEdit", "handleUserChange", "handleEntityChange", "handleSearch", "handleAutomation", "handleIntegrationTest", "handleProviderAction", "config.scaffoldFamily", "fetch(`${API_BASE}/api/auth/session`)", "Routes", "APP_ROUTES", "PAGE_COMPONENTS", "NavLink"):
        if marker not in frontend_source:
            raise GeneratedProjectError(f"Generated frontend is missing CRUD marker: {marker}")
    for field_name in ("app_type", "primary_entity", "pages", "workflows", "auth", "capabilities", "integrations", "permissions", "layout", "family_modules", "generator_boundary", "support_tier", "closest_family", "refinement_steps", "handoff_notes", "spec_brief", "scaffold_family"):
        if field_name not in manifest:
            raise GeneratedProjectError(f"Manifest is missing required field '{field_name}'.")
    if manifest["scaffold_family"].get("app_type") != manifest["app_type"]:
        raise GeneratedProjectError("Manifest scaffold_family must align with app_type.")
    _validate_family_specific_files(manifest["app_type"], root)
    _validate_family_specific_markers(manifest["app_type"], backend_source, frontend_source)
    if any(field["name"].endswith("_id") for entity in manifest["data_model"] for field in entity.get("fields", [])):
        if "ForeignKey(" not in backend_source:
            raise GeneratedProjectError("Generated backend is missing inferred foreign keys.")
        if "relationship(" not in backend_source:
            raise GeneratedProjectError("Generated backend is missing inferred ORM relationships.")
        if "FOREIGN KEY" not in migration_source:
            raise GeneratedProjectError("Generated migration is missing foreign key definitions.")

    return True
