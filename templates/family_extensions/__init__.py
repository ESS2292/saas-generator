from templates.family_extensions.booking import BOOKING_EXTENSION, BOOKING_VALIDATION
from templates.family_extensions.content import CONTENT_EXTENSION, CONTENT_VALIDATION
from templates.family_extensions.crm import CRM_EXTENSION, CRM_VALIDATION
from templates.family_extensions.ecommerce import ECOMMERCE_EXTENSION, ECOMMERCE_VALIDATION
from templates.family_extensions.finance import FINANCE_EXTENSION, FINANCE_VALIDATION
from templates.family_extensions.internal_tool import INTERNAL_TOOL_EXTENSION, INTERNAL_TOOL_VALIDATION
from templates.family_extensions.inventory import INVENTORY_EXTENSION, INVENTORY_VALIDATION
from templates.family_extensions.learning import LEARNING_EXTENSION, LEARNING_VALIDATION
from templates.family_extensions.marketplace import MARKETPLACE_EXTENSION, MARKETPLACE_VALIDATION
from templates.family_extensions.project_management import PROJECT_MANAGEMENT_EXTENSION, PROJECT_MANAGEMENT_VALIDATION
from templates.family_extensions.recruiting import RECRUITING_EXTENSION, RECRUITING_VALIDATION
from templates.family_extensions.social import SOCIAL_EXTENSION, SOCIAL_VALIDATION
from templates.family_extensions.support import SUPPORT_EXTENSION, SUPPORT_VALIDATION


FAMILY_VALIDATIONS = {
    "booking_platform": BOOKING_VALIDATION,
    "content_platform": CONTENT_VALIDATION,
    "crm_platform": CRM_VALIDATION,
    "finance_ops": FINANCE_VALIDATION,
    "inventory_management": INVENTORY_VALIDATION,
    "project_management": PROJECT_MANAGEMENT_VALIDATION,
    "internal_tool": INTERNAL_TOOL_VALIDATION,
    "learning_platform": LEARNING_VALIDATION,
    "marketplace": MARKETPLACE_VALIDATION,
    "recruiting_platform": RECRUITING_VALIDATION,
    "social_app": SOCIAL_VALIDATION,
    "support_desk": SUPPORT_VALIDATION,
    "ecommerce_app": ECOMMERCE_VALIDATION,
}


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
    "FAMILY_VALIDATIONS",
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
]
