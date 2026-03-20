import json

from engine.project_builder import build_project_from_manifest
from engine.validator import validate_project_scaffold


def test_build_project_from_manifest_writes_scaffold(tmp_path):
    output = """
    {
      "app_name": "Client Pulse",
      "slug": "client-pulse",
      "app_type": "marketplace",
      "tagline": "Know every account",
      "summary": "Customer health monitoring for agencies",
      "primary_entity": "Client",
      "theme": {
        "primary_color": "#0f766e",
        "accent_color": "#f59e0b",
        "surface_color": "#ecfeff"
      },
      "dashboard": {
        "headline": "Client pulse overview",
        "subheadline": "Watch account health in one place",
        "sections": [{"title": "Health", "description": "Review account status"}]
      },
      "pages": [{"name": "Overview", "purpose": "Health summary"}, {"name": "Clients", "purpose": "Browse clients"}],
      "workflows": [{"name": "Manage account", "steps": ["Review", "Contact", "Resolve"]}],
      "auth": {
        "enabled": true,
        "roles": ["owner", "manager", "viewer"],
        "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
      },
      "capabilities": {"search": true, "notifications": true, "automation": true},
      "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
      "data_model": [
        {"name": "Client", "fields": [{"name": "name", "type": "string"}, {"name": "status", "type": "string"}, {"name": "seller", "type": "string"}, {"name": "price", "type": "number"}]},
        {"name": "Project", "fields": [{"name": "title", "type": "string"}, {"name": "client_id", "type": "number"}]}
      ],
      "api_routes": [{"path": "/clients", "method": "GET", "summary": "List clients"}],
      "sample_records": [{"title": "Acme", "status": "healthy", "owner": "amy", "seller": "amy", "price": 199}]
    }
    """

    manifest, saved_files = build_project_from_manifest(output, app_root=str(tmp_path))

    assert manifest["app_name"] == "Client Pulse"
    assert manifest["app_type"] == "marketplace"
    assert manifest["scaffold_family"]["app_type"] == "marketplace"
    assert manifest["scaffold_family"]["summary_cards"] == ["Listings", "Primary Route", "Participants"]
    assert manifest["layout"]["navigation_style"] == "tabs"
    assert manifest["permissions"][0]["resource"] == "Client"
    assert "marketplace_module" in manifest["family_modules"]
    assert manifest["generator_boundary"]["mode"] == "family_based_generator"
    assert manifest["support_tier"] == "supported"
    assert manifest["closest_family"] == "marketplace"
    assert manifest["spec_brief"]["closest_family"] == "marketplace"
    assert ".env.example" in saved_files
    assert "backend/main.py" in saved_files
    assert "backend/app_config.py" in saved_files
    assert "backend/app_core.py" in saved_files
    assert "backend/database.py" in saved_files
    assert "backend/providers.py" in saved_files
    assert "backend/.env.example" in saved_files
    assert "backend/seed_data.json" in saved_files
    assert "backend/migrations/0001_initial.sql" in saved_files
    assert "backend/migrations/schema_snapshot.json" in saved_files
    assert "backend/migrations/history.json" in saved_files
    assert "backend/migrations/README.md" in saved_files
    assert "frontend/src/api.js" in saved_files
    assert "frontend/src/App.jsx" in saved_files
    assert "frontend/src/appShell.jsx" in saved_files
    assert "frontend/src/entityUtils.js" in saved_files
    assert "frontend/src/routes.js" in saved_files
    assert "frontend/src/pages/index.js" in saved_files
    assert "frontend/src/pages/pageHelpers.jsx" in saved_files
    assert "frontend/src/pages/OverviewPage.jsx" in saved_files
    assert "frontend/src/pages/ClientsPage.jsx" in saved_files
    assert "frontend/src/components/SummaryCards.jsx" in saved_files
    assert "frontend/src/components/SearchPanel.jsx" in saved_files
    assert "frontend/src/components/AutomationPanel.jsx" in saved_files
    assert "frontend/src/components/EntityForm.jsx" in saved_files
    assert "frontend/src/components/SectionsPanel.jsx" in saved_files
    assert "frontend/src/components/WorkflowPanel.jsx" in saved_files
    assert "frontend/src/components/IntegrationsPanel.jsx" in saved_files
    assert "frontend/src/components/FeedPanels.jsx" in saved_files
    assert "frontend/src/components/RecordGrid.jsx" in saved_files
    assert "deploy/docker-compose.yml" in saved_files
    assert "deploy/render.yaml" in saved_files
    assert "deploy/railway.json" in saved_files
    assert "deploy/README.md" in saved_files
    assert json.loads((tmp_path / "manifest.json").read_text())["slug"] == "client-pulse"
    root_env_source = (tmp_path / ".env.example").read_text()
    backend_env_source = (tmp_path / "backend" / ".env.example").read_text()
    backend_entry_source = (tmp_path / "backend" / "main.py").read_text()
    backend_config_source = (tmp_path / "backend" / "app_config.py").read_text()
    backend_source = (tmp_path / "backend" / "app_core.py").read_text()
    backend_database_source = (tmp_path / "backend" / "database.py").read_text()
    provider_source = (tmp_path / "backend" / "providers.py").read_text()
    migration_source = (tmp_path / "backend" / "migrations" / "0001_initial.sql").read_text()
    schema_snapshot_source = (tmp_path / "backend" / "migrations" / "schema_snapshot.json").read_text()
    migration_history_source = (tmp_path / "backend" / "migrations" / "history.json").read_text()
    migration_readme_source = (tmp_path / "backend" / "migrations" / "README.md").read_text()
    frontend_entry_source = (tmp_path / "frontend" / "src" / "App.jsx").read_text()
    frontend_api_source = (tmp_path / "frontend" / "src" / "api.js").read_text()
    frontend_source = (tmp_path / "frontend" / "src" / "appShell.jsx").read_text()
    frontend_utils_source = (tmp_path / "frontend" / "src" / "entityUtils.js").read_text()
    frontend_routes_source = (tmp_path / "frontend" / "src" / "routes.js").read_text()
    frontend_pages_index_source = (tmp_path / "frontend" / "src" / "pages" / "index.js").read_text()
    frontend_page_helpers_source = (tmp_path / "frontend" / "src" / "pages" / "pageHelpers.jsx").read_text()
    frontend_overview_page_source = (tmp_path / "frontend" / "src" / "pages" / "OverviewPage.jsx").read_text()
    frontend_summary_source = (tmp_path / "frontend" / "src" / "components" / "SummaryCards.jsx").read_text()
    frontend_search_source = (tmp_path / "frontend" / "src" / "components" / "SearchPanel.jsx").read_text()
    frontend_automation_source = (tmp_path / "frontend" / "src" / "components" / "AutomationPanel.jsx").read_text()
    frontend_form_source = (tmp_path / "frontend" / "src" / "components" / "EntityForm.jsx").read_text()
    frontend_sections_source = (tmp_path / "frontend" / "src" / "components" / "SectionsPanel.jsx").read_text()
    frontend_workflow_source = (tmp_path / "frontend" / "src" / "components" / "WorkflowPanel.jsx").read_text()
    frontend_integrations_source = (tmp_path / "frontend" / "src" / "components" / "IntegrationsPanel.jsx").read_text()
    frontend_feed_panels_source = (tmp_path / "frontend" / "src" / "components" / "FeedPanels.jsx").read_text()
    frontend_grid_source = (tmp_path / "frontend" / "src" / "components" / "RecordGrid.jsx").read_text()
    deploy_compose_source = (tmp_path / "deploy" / "docker-compose.yml").read_text()
    deploy_render_source = (tmp_path / "deploy" / "render.yaml").read_text()
    deploy_railway_source = (tmp_path / "deploy" / "railway.json").read_text()
    assert "from app_core import app" in backend_entry_source
    assert "APP_NAME=" in root_env_source
    assert "PAYMENTS_SECRET_KEY=" in root_env_source
    assert "EMAIL_FROM_EMAIL=" in backend_env_source
    assert "APP_BASE_URL=" in backend_env_source
    assert "AWS_ACCESS_KEY_ID=" in backend_env_source
    assert "APP_CONFIG =" in backend_config_source
    assert "DEFAULT_FORM_VALUES =" in backend_config_source
    assert "create_engine(" in backend_database_source
    assert "SessionLocal = sessionmaker" in backend_database_source
    assert "import AppShell from './appShell.jsx'" in frontend_entry_source
    assert "BrowserRouter" in frontend_entry_source
    assert "export const API_BASE =" in frontend_api_source
    assert "export function entityToTableName" in frontend_utils_source
    assert "export const APP_ROUTES =" in frontend_routes_source
    assert "export const PAGE_COMPONENTS =" in frontend_pages_index_source
    assert "export default function GeneratedPageLayout" in frontend_page_helpers_source
    assert "GeneratedPageLayout" in frontend_overview_page_source
    assert "export default function SummaryCards" in frontend_summary_source
    assert "export default function SearchPanel" in frontend_search_source
    assert "export default function AutomationPanel" in frontend_automation_source
    assert "automationActions.map" in frontend_automation_source
    assert "export default function EntityForm" in frontend_form_source
    assert "export default function SectionsPanel" in frontend_sections_source
    assert "export default function WorkflowPanel" in frontend_workflow_source
    assert "export default function IntegrationsPanel" in frontend_integrations_source
    assert "export function IntegrationEventsPanel" in frontend_feed_panels_source
    assert "export default function RecordGrid" in frontend_grid_source
    assert "services:" in deploy_compose_source
    assert "backend:" in deploy_compose_source
    assert "frontend:" in deploy_compose_source
    assert "services:" in deploy_render_source
    assert '"deploy"' in deploy_railway_source
    assert "@app.get('/api/clients')" in backend_source
    assert "@app.get('/api/projects')" in backend_source
    assert "@app.post('/api/clients')" in backend_source
    assert "@app.put('/api/projects'" in backend_source
    assert "@app.get('/api/projects'" in backend_source
    assert "@app.get('/api/entities')" in backend_source
    assert "@app.get('/api/auth/session')" in backend_source
    assert "@app.get('/api/search')" in backend_source
    assert "@app.get('/api/notifications')" in backend_source
    assert "@app.post('/api/automation/run')" in backend_source
    assert "@app.get('/api/integrations')" in backend_source
    assert "@app.post('/api/integrations/test')" in backend_source
    assert "@app.post('/api/integrations/payment/checkout')" in backend_source
    assert "@app.post('/api/integrations/email/send')" in backend_source
    assert "@app.post('/api/integrations/storage/presign')" in backend_source
    assert "@app.post('/api/webhooks/{provider}')" in backend_source
    assert "def build_checkout_session" in provider_source
    assert "def send_email_message" in provider_source
    assert "def build_storage_upload" in provider_source
    assert "https://api.stripe.com/v1/checkout/sessions" in provider_source
    assert "https://api.sendgrid.com/v3/mail/send" in provider_source
    assert "https://api.resend.com/emails" in provider_source
    assert "X-Amz-Algorithm" in provider_source
    assert "api.cloudinary.com" in provider_source
    assert "Base.metadata.create_all" in backend_source
    assert "ForeignKey('clients.id')" in backend_source
    assert "relationship('Client')" in backend_source
    assert "FOREIGN KEY (client_id) REFERENCES clients(id)" in migration_source
    assert json.loads(schema_snapshot_source)["entities"][0]["table"] == "clients"
    assert json.loads(migration_history_source)["current_version"] == 1
    assert "NNNN_schema_update.sql" in migration_readme_source
    assert "import { API_BASE } from './api.js'" in frontend_source
    assert "import { entityToTableName } from './entityUtils.js'" in frontend_source
    assert "import { APP_ROUTES } from './routes.js'" in frontend_source
    assert "import { PAGE_COMPONENTS } from './pages/index.js'" in frontend_source
    assert "handleSaveRecord" in frontend_source
    assert "handleDeleteRecord" in frontend_source
    assert "handleUserChange" in frontend_source
    assert "beginEdit" in frontend_source
    assert "handleEntityChange" in frontend_source
    assert "handleSearch" in frontend_source
    assert "handleAutomation" in frontend_source
    assert "handleIntegrationTest" in frontend_source
    assert "handleProviderAction" in frontend_source
    assert "config.scaffoldFamily" in frontend_source
    assert "Routes" in frontend_source
    assert "NavLink" in frontend_source
    assert "PAGE_COMPONENTS" in frontend_source
    assert validate_project_scaffold(str(tmp_path)) is True


def test_build_project_from_manifest_emits_incremental_schema_migration(tmp_path):
    original_output = """
    {
      "app_name": "Client Pulse",
      "slug": "client-pulse",
      "app_type": "crm_platform",
      "primary_entity": "Client",
      "data_model": [
        {"name": "Client", "fields": [{"name": "name", "type": "string"}, {"name": "status", "type": "string"}]}
      ],
      "sample_records": [{"name": "Acme", "status": "active"}]
    }
    """
    updated_output = """
    {
      "app_name": "Client Pulse",
      "slug": "client-pulse",
      "app_type": "crm_platform",
      "primary_entity": "Client",
      "data_model": [
        {"name": "Client", "fields": [{"name": "name", "type": "string"}, {"name": "status", "type": "string"}, {"name": "health_score", "type": "number"}]},
        {"name": "Note", "fields": [{"name": "client_id", "type": "number"}, {"name": "body", "type": "string"}]}
      ],
      "sample_records": [{"name": "Acme", "status": "active", "health_score": 91}]
    }
    """

    build_project_from_manifest(original_output, app_root=str(tmp_path))
    _manifest, saved_files = build_project_from_manifest(updated_output, app_root=str(tmp_path))

    assert "backend/migrations/0002_schema_update.sql" in saved_files
    incremental_source = (tmp_path / "backend" / "migrations" / "0002_schema_update.sql").read_text()
    migration_history = json.loads((tmp_path / "backend" / "migrations" / "history.json").read_text())
    schema_snapshot = json.loads((tmp_path / "backend" / "migrations" / "schema_snapshot.json").read_text())

    assert "ALTER TABLE clients ADD COLUMN health_score REAL;" in incremental_source
    assert "CREATE TABLE IF NOT EXISTS notes" in incremental_source
    assert migration_history["current_version"] == 2
    assert migration_history["migrations"][-1]["file"] == "0002_schema_update.sql"
    assert any(entity["table"] == "notes" for entity in schema_snapshot["entities"])
    assert validate_project_scaffold(str(tmp_path)) is True
