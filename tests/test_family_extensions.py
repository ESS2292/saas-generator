from templates.family_extensions import FAMILY_PACKS, FAMILY_VALIDATIONS, FamilyPack, get_family_pack


def test_family_validation_registry_covers_divergent_families():
    assert set(FAMILY_VALIDATIONS) == {
        "booking_platform",
        "content_platform",
        "crm_platform",
        "finance_ops",
        "inventory_management",
        "project_management",
        "internal_tool",
        "learning_platform",
        "marketplace",
        "recruiting_platform",
        "social_app",
        "support_desk",
        "ecommerce_app",
    }


def test_family_pack_registry_exposes_typed_family_packs():
    crm_pack = get_family_pack("crm_platform")

    assert set(FAMILY_PACKS) == set(FAMILY_VALIDATIONS)
    assert isinstance(crm_pack, FamilyPack)
    assert crm_pack.app_type == "crm_platform"
    assert crm_pack.has_extension is True
    assert "@app.get('/api/crm/pipeline')" in crm_pack.backend_markers
    assert "CrmFamilyPanel" in crm_pack.frontend_markers


def test_family_validation_registry_exposes_backend_and_frontend_markers():
    booking = FAMILY_VALIDATIONS["booking_platform"]

    assert "@app.get('/api/booking/availability')" in booking["backend_markers"]
    assert "BookingFamilyPanel" in booking["frontend_markers"]

    internal_tool = FAMILY_VALIDATIONS["internal_tool"]
    assert "@app.get('/api/internal/queue')" in internal_tool["backend_markers"]
    assert "InternalToolFamilyPanel" in internal_tool["frontend_markers"]

    crm = FAMILY_VALIDATIONS["crm_platform"]
    assert "@app.get('/api/crm/pipeline')" in crm["backend_markers"]
    assert "@app.get('/api/crm/account-health')" in crm["backend_markers"]
    assert "@app.get('/api/crm/activity')" in crm["backend_markers"]
    assert "@app.post('/api/crm/deals/{item_id}/reassign')" in crm["backend_markers"]
    assert "@app.post('/api/crm/deals/{item_id}/advance')" in crm["backend_markers"]
    assert "CrmFamilyPanel" in crm["frontend_markers"]
    assert "crmAccountHealth" in crm["frontend_markers"]
    assert "crmActivity" in crm["frontend_markers"]

    project_management = FAMILY_VALIDATIONS["project_management"]
    assert "@app.get('/api/project-management/board')" in project_management["backend_markers"]
    assert "@app.post('/api/project-management/projects/{item_id}/advance')" in project_management["backend_markers"]
    assert "ProjectManagementFamilyPanel" in project_management["frontend_markers"]

    recruiting = FAMILY_VALIDATIONS["recruiting_platform"]
    assert "@app.get('/api/recruiting/pipeline')" in recruiting["backend_markers"]
    assert "@app.post('/api/recruiting/candidates/{item_id}/advance')" in recruiting["backend_markers"]
    assert "RecruitingFamilyPanel" in recruiting["frontend_markers"]

    inventory = FAMILY_VALIDATIONS["inventory_management"]
    assert "@app.get('/api/inventory/stock')" in inventory["backend_markers"]
    assert "@app.post('/api/inventory/items/{item_id}/reorder')" in inventory["backend_markers"]
    assert "InventoryFamilyPanel" in inventory["frontend_markers"]

    finance = FAMILY_VALIDATIONS["finance_ops"]
    assert "@app.get('/api/finance/cashflow')" in finance["backend_markers"]
    assert "@app.post('/api/finance/invoices/{item_id}/approve')" in finance["backend_markers"]
    assert "FinanceFamilyPanel" in finance["frontend_markers"]
