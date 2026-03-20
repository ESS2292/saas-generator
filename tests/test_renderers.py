from templates.renderers import PROJECT_RENDERERS, build_project_files


def _manifest(app_type):
    return {
        "app_name": "Demo App",
        "slug": "demo-app",
        "app_type": app_type,
        "tagline": "Demo",
        "summary": "Demo summary",
        "primary_entity": "Record",
        "scaffold_family": {
            "app_type": app_type,
            "template_key": "dashboard_shell",
            "navigation_style": "tabs",
            "summary_cards": ["One", "Two", "Three"],
            "automation_actions": [{"action": "sync-status", "label": "Sync Status"}],
            "record_label": "Records",
            "search_placeholder": "Search records",
            "app_type_label": "Demo Label",
        },
        "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff",
        },
        "dashboard": {
            "headline": "Demo headline",
            "subheadline": "Demo subheadline",
            "sections": [{"title": "Overview", "description": "Section"}],
        },
        "pages": [{"name": "Overview", "purpose": "Demo page"}],
        "workflows": [{"name": "Do work", "steps": ["Start", "Finish"]}],
        "auth": {
            "enabled": True,
            "roles": ["owner"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}],
        },
        "capabilities": {"search": True, "notifications": True, "automation": True},
        "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
        "data_model": [{"name": "Record", "fields": [{"name": "name", "type": "string"}]}],
        "api_routes": [{"path": "/records", "method": "GET", "summary": "List records"}],
        "sample_records": [{"name": "Acme"}],
    }


def test_project_renderers_cover_all_supported_app_types():
    assert set(PROJECT_RENDERERS) == {
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


def test_build_project_files_routes_through_renderer_registry():
    files = build_project_files(_manifest("marketplace"))

    paths = {path for path, _content in files}
    assert "backend/main.py" in paths
    assert "frontend/src/App.jsx" in paths


def test_internal_tool_renderer_adds_queue_backend_and_frontend():
    files = build_project_files(_manifest("internal_tool"))
    file_map = dict(files)

    assert "@app.get('/api/internal/queue')" in file_map["backend/app_core.py"]
    assert "@app.get('/api/internal/approvals')" in file_map["backend/app_core.py"]
    assert "from family_logic import build_internal_approvals, build_internal_queue" in file_map["backend/app_core.py"]
    assert "build_internal_queue" in file_map["backend/family_logic.py"]
    assert "InternalToolFamilyPanel" in file_map["frontend/src/appShell.jsx"]
    assert "export function InternalToolFamilyPanel" in file_map["frontend/src/familyPanel.jsx"]
    assert "loadInternalOperations" in file_map["frontend/src/appShell.jsx"]


def test_crm_renderer_adds_pipeline_backend_and_frontend():
    files = build_project_files(_manifest("crm_platform"))
    file_map = dict(files)

    assert "@app.get('/api/crm/pipeline')" in file_map["backend/app_core.py"]
    assert "@app.get('/api/crm/accounts')" in file_map["backend/app_core.py"]
    assert "@app.post('/api/crm/deals/{item_id}/advance')" in file_map["backend/app_core.py"]
    assert "from family_logic import advance_crm_deal_status, build_crm_accounts, build_crm_pipeline" in file_map["backend/app_core.py"]
    assert "build_crm_pipeline" in file_map["backend/family_logic.py"]
    assert "CrmFamilyPanel" in file_map["frontend/src/appShell.jsx"]
    assert "export function CrmFamilyPanel" in file_map["frontend/src/familyPanel.jsx"]
    assert "loadCrmOperations" in file_map["frontend/src/appShell.jsx"]


def test_support_renderer_adds_queue_backend_and_frontend():
    files = build_project_files(_manifest("support_desk"))
    file_map = dict(files)

    assert "@app.get('/api/support/queue')" in file_map["backend/app_core.py"]
    assert "@app.get('/api/support/escalations')" in file_map["backend/app_core.py"]
    assert "@app.post('/api/support/tickets/{item_id}/escalate')" in file_map["backend/app_core.py"]
    assert "from family_logic import build_support_escalations, build_support_queue, escalate_support_ticket" in file_map["backend/app_core.py"]
    assert "build_support_queue" in file_map["backend/family_logic.py"]
    assert "SupportFamilyPanel" in file_map["frontend/src/appShell.jsx"]
    assert "export function SupportFamilyPanel" in file_map["frontend/src/familyPanel.jsx"]
    assert "loadSupportOperations" in file_map["frontend/src/appShell.jsx"]


def test_project_management_renderer_adds_board_backend_and_frontend():
    files = build_project_files(_manifest("project_management"))
    file_map = dict(files)

    assert "@app.get('/api/project-management/board')" in file_map["backend/app_core.py"]
    assert "@app.get('/api/project-management/milestones')" in file_map["backend/app_core.py"]
    assert "@app.post('/api/project-management/projects/{item_id}/advance')" in file_map["backend/app_core.py"]
    assert "from family_logic import advance_project_status, build_project_board, build_project_milestones" in file_map["backend/app_core.py"]
    assert "build_project_board" in file_map["backend/family_logic.py"]
    assert "ProjectManagementFamilyPanel" in file_map["frontend/src/appShell.jsx"]
    assert "export function ProjectManagementFamilyPanel" in file_map["frontend/src/familyPanel.jsx"]
    assert "loadProjectOperations" in file_map["frontend/src/appShell.jsx"]


def test_recruiting_renderer_adds_pipeline_backend_and_frontend():
    files = build_project_files(_manifest("recruiting_platform"))
    file_map = dict(files)

    assert "@app.get('/api/recruiting/pipeline')" in file_map["backend/app_core.py"]
    assert "@app.get('/api/recruiting/interviews')" in file_map["backend/app_core.py"]
    assert "@app.post('/api/recruiting/candidates/{item_id}/advance')" in file_map["backend/app_core.py"]
    assert "from family_logic import advance_candidate_stage, build_recruiting_interviews, build_recruiting_pipeline" in file_map["backend/app_core.py"]
    assert "build_recruiting_pipeline" in file_map["backend/family_logic.py"]
    assert "RecruitingFamilyPanel" in file_map["frontend/src/appShell.jsx"]
    assert "export function RecruitingFamilyPanel" in file_map["frontend/src/familyPanel.jsx"]
    assert "loadRecruitingOperations" in file_map["frontend/src/appShell.jsx"]


def test_inventory_renderer_adds_stock_backend_and_frontend():
    files = build_project_files(_manifest("inventory_management"))
    file_map = dict(files)

    assert "@app.get('/api/inventory/stock')" in file_map["backend/app_core.py"]
    assert "@app.get('/api/inventory/reorders')" in file_map["backend/app_core.py"]
    assert "@app.post('/api/inventory/items/{item_id}/reorder')" in file_map["backend/app_core.py"]
    assert "from family_logic import build_inventory_reorders, build_inventory_stock, create_reorder_request" in file_map["backend/app_core.py"]
    assert "build_inventory_stock" in file_map["backend/family_logic.py"]
    assert "InventoryFamilyPanel" in file_map["frontend/src/appShell.jsx"]
    assert "export function InventoryFamilyPanel" in file_map["frontend/src/familyPanel.jsx"]
    assert "loadInventoryOperations" in file_map["frontend/src/appShell.jsx"]


def test_finance_renderer_adds_cashflow_backend_and_frontend():
    files = build_project_files(_manifest("finance_ops"))
    file_map = dict(files)

    assert "@app.get('/api/finance/cashflow')" in file_map["backend/app_core.py"]
    assert "@app.get('/api/finance/approvals')" in file_map["backend/app_core.py"]
    assert "@app.post('/api/finance/invoices/{item_id}/approve')" in file_map["backend/app_core.py"]
    assert "from family_logic import approve_finance_invoice, build_finance_approvals, build_finance_cashflow" in file_map["backend/app_core.py"]
    assert "build_finance_cashflow" in file_map["backend/family_logic.py"]
    assert "FinanceFamilyPanel" in file_map["frontend/src/appShell.jsx"]
    assert "export function FinanceFamilyPanel" in file_map["frontend/src/familyPanel.jsx"]
    assert "loadFinanceOperations" in file_map["frontend/src/appShell.jsx"]


def test_content_renderer_adds_publishing_backend_and_frontend():
    files = build_project_files(_manifest("content_platform"))
    file_map = dict(files)

    assert "@app.get('/api/content/pipeline')" in file_map["backend/app_core.py"]
    assert "@app.get('/api/content/calendar')" in file_map["backend/app_core.py"]
    assert "from family_logic import build_content_calendar, build_content_pipeline" in file_map["backend/app_core.py"]
    assert "build_content_pipeline" in file_map["backend/family_logic.py"]
    assert "ContentFamilyPanel" in file_map["frontend/src/appShell.jsx"]
    assert "export function ContentFamilyPanel" in file_map["frontend/src/familyPanel.jsx"]
    assert "loadContentOperations" in file_map["frontend/src/appShell.jsx"]


def test_social_renderer_adds_engagement_backend_and_frontend():
    files = build_project_files(_manifest("social_app"))
    file_map = dict(files)

    assert "@app.get('/api/social/engagement')" in file_map["backend/app_core.py"]
    assert "@app.get('/api/social/moderation')" in file_map["backend/app_core.py"]
    assert "from family_logic import build_social_engagement, build_social_moderation" in file_map["backend/app_core.py"]
    assert "build_social_engagement" in file_map["backend/family_logic.py"]
    assert "SocialFamilyPanel" in file_map["frontend/src/appShell.jsx"]
    assert "export function SocialFamilyPanel" in file_map["frontend/src/familyPanel.jsx"]
    assert "loadSocialActivity" in file_map["frontend/src/appShell.jsx"]


def test_learning_renderer_adds_progress_backend_and_frontend():
    files = build_project_files(_manifest("learning_platform"))
    file_map = dict(files)

    assert "@app.get('/api/learning/progress')" in file_map["backend/app_core.py"]
    assert "@app.get('/api/learning/lessons')" in file_map["backend/app_core.py"]
    assert "from family_logic import build_learning_progress, build_learning_readiness" in file_map["backend/app_core.py"]
    assert "build_learning_progress" in file_map["backend/family_logic.py"]
    assert "LearningFamilyPanel" in file_map["frontend/src/appShell.jsx"]
    assert "export function LearningFamilyPanel" in file_map["frontend/src/familyPanel.jsx"]
    assert "loadLearningProgress" in file_map["frontend/src/appShell.jsx"]


def test_marketplace_renderer_adds_marketplace_specific_backend_and_frontend():
    files = build_project_files(_manifest("marketplace"))
    file_map = dict(files)

    assert "@app.get('/api/marketplace/activity')" in file_map["backend/app_core.py"]
    assert "@app.post('/api/marketplace/moderation/{item_id}')" in file_map["backend/app_core.py"]
    assert "from family_logic import build_marketplace_activity" in file_map["backend/app_core.py"]
    assert "build_marketplace_activity" in file_map["backend/family_logic.py"]
    assert "MarketplaceFamilyPanel" in file_map["frontend/src/appShell.jsx"]
    assert "export function MarketplaceFamilyPanel" in file_map["frontend/src/familyPanel.jsx"]
    assert "loadMarketplaceActivity" in file_map["frontend/src/appShell.jsx"]
    assert "marketplaceModeration" in file_map["frontend/src/appShell.jsx"]


def test_ecommerce_renderer_adds_order_pipeline_backend_and_frontend():
    files = build_project_files(_manifest("ecommerce_app"))
    file_map = dict(files)

    assert "@app.get('/api/ecommerce/orders')" in file_map["backend/app_core.py"]
    assert "@app.post('/api/ecommerce/orders/{item_id}/advance')" in file_map["backend/app_core.py"]
    assert "from family_logic import advance_order_status, build_order_pipeline" in file_map["backend/app_core.py"]
    assert "build_order_pipeline" in file_map["backend/family_logic.py"]
    assert "EcommerceFamilyPanel" in file_map["frontend/src/appShell.jsx"]
    assert "export function EcommerceFamilyPanel" in file_map["frontend/src/familyPanel.jsx"]
    assert "loadOrderPipeline" in file_map["frontend/src/appShell.jsx"]
    assert "fulfillmentSummary" in file_map["frontend/src/appShell.jsx"]


def test_booking_renderer_adds_booking_specific_backend_and_frontend():
    files = build_project_files(_manifest("booking_platform"))
    file_map = dict(files)

    assert "@app.get('/api/booking/availability')" in file_map["backend/app_core.py"]
    assert "def get_booking_availability()" in file_map["backend/app_core.py"]
    assert "from family_logic import build_booking_availability" in file_map["backend/app_core.py"]
    assert "build_booking_availability" in file_map["backend/family_logic.py"]
    assert "BookingFamilyPanel" in file_map["frontend/src/appShell.jsx"]
    assert "export function BookingFamilyPanel" in file_map["frontend/src/familyPanel.jsx"]
    assert "loadBookingAvailability" in file_map["frontend/src/appShell.jsx"]
