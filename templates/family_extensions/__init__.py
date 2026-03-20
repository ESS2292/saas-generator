from templates.family_extensions.booking import BOOKING_EXTENSION, BOOKING_VALIDATION
from templates.family_extensions.content import CONTENT_EXTENSION, CONTENT_VALIDATION
from templates.family_extensions.crm import CRM_EXTENSION, CRM_VALIDATION
from templates.family_extensions.ecommerce import ECOMMERCE_EXTENSION, ECOMMERCE_VALIDATION
from templates.family_extensions.finance import FINANCE_EXTENSION, FINANCE_VALIDATION
from templates.family_extensions.internal_tool import INTERNAL_TOOL_EXTENSION, INTERNAL_TOOL_VALIDATION
from templates.family_extensions.inventory import INVENTORY_EXTENSION, INVENTORY_VALIDATION
from templates.family_extensions.learning import LEARNING_EXTENSION, LEARNING_VALIDATION
from templates.family_extensions.marketplace import MARKETPLACE_EXTENSION, MARKETPLACE_VALIDATION
from templates.family_extensions.pack import FamilyPack, FamilyValidation, build_family_pack
from templates.family_extensions.project_management import PROJECT_MANAGEMENT_EXTENSION, PROJECT_MANAGEMENT_VALIDATION
from templates.family_extensions.recruiting import RECRUITING_EXTENSION, RECRUITING_VALIDATION
from templates.family_extensions.social import SOCIAL_EXTENSION, SOCIAL_VALIDATION
from templates.family_extensions.support import SUPPORT_EXTENSION, SUPPORT_VALIDATION


FAMILY_PACKS = {
    "booking_platform": build_family_pack("booking_platform", BOOKING_EXTENSION, BOOKING_VALIDATION),
    "content_platform": build_family_pack("content_platform", CONTENT_EXTENSION, CONTENT_VALIDATION),
    "crm_platform": build_family_pack("crm_platform", CRM_EXTENSION, CRM_VALIDATION),
    "finance_ops": build_family_pack("finance_ops", FINANCE_EXTENSION, FINANCE_VALIDATION),
    "inventory_management": build_family_pack("inventory_management", INVENTORY_EXTENSION, INVENTORY_VALIDATION),
    "project_management": build_family_pack("project_management", PROJECT_MANAGEMENT_EXTENSION, PROJECT_MANAGEMENT_VALIDATION),
    "internal_tool": build_family_pack("internal_tool", INTERNAL_TOOL_EXTENSION, INTERNAL_TOOL_VALIDATION),
    "learning_platform": build_family_pack("learning_platform", LEARNING_EXTENSION, LEARNING_VALIDATION),
    "marketplace": build_family_pack("marketplace", MARKETPLACE_EXTENSION, MARKETPLACE_VALIDATION),
    "recruiting_platform": build_family_pack("recruiting_platform", RECRUITING_EXTENSION, RECRUITING_VALIDATION),
    "social_app": build_family_pack("social_app", SOCIAL_EXTENSION, SOCIAL_VALIDATION),
    "support_desk": build_family_pack("support_desk", SUPPORT_EXTENSION, SUPPORT_VALIDATION),
    "ecommerce_app": build_family_pack("ecommerce_app", ECOMMERCE_EXTENSION, ECOMMERCE_VALIDATION),
}


FAMILY_VALIDATIONS = {
    app_type: pack.validation.as_mapping()
    for app_type, pack in FAMILY_PACKS.items()
}


def get_family_pack(app_type):
    return FAMILY_PACKS.get(app_type)


__all__ = [
    "BOOKING_EXTENSION",
    "BOOKING_VALIDATION",
    "CONTENT_EXTENSION",
    "CONTENT_VALIDATION",
    "CRM_EXTENSION",
    "CRM_VALIDATION",
    "ECOMMERCE_EXTENSION",
    "ECOMMERCE_VALIDATION",
    "FINANCE_EXTENSION",
    "FINANCE_VALIDATION",
    "FAMILY_PACKS",
    "FAMILY_VALIDATIONS",
    "FamilyPack",
    "FamilyValidation",
    "INTERNAL_TOOL_EXTENSION",
    "INTERNAL_TOOL_VALIDATION",
    "INVENTORY_EXTENSION",
    "INVENTORY_VALIDATION",
    "LEARNING_EXTENSION",
    "LEARNING_VALIDATION",
    "MARKETPLACE_EXTENSION",
    "MARKETPLACE_VALIDATION",
    "PROJECT_MANAGEMENT_EXTENSION",
    "PROJECT_MANAGEMENT_VALIDATION",
    "RECRUITING_EXTENSION",
    "RECRUITING_VALIDATION",
    "SOCIAL_EXTENSION",
    "SOCIAL_VALIDATION",
    "SUPPORT_EXTENSION",
    "SUPPORT_VALIDATION",
    "build_family_pack",
    "get_family_pack",
]
