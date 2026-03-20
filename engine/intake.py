import re


APP_TYPE_KEYWORDS = {
    "crm_platform": ("crm", "sales pipeline", "lead", "opportunity", "deal", "account executive"),
    "support_desk": ("support desk", "help desk", "customer support", "ticketing", "support ticket", "case"),
    "project_management": ("project management", "project tracker", "task board", "sprint", "roadmap", "milestone"),
    "recruiting_platform": ("recruiting", "hiring", "candidate", "interview", "ats", "talent"),
    "inventory_management": ("inventory", "warehouse", "stock", "sku", "reorder", "supplier"),
    "finance_ops": ("finance ops", "invoice", "billing ops", "accounts receivable", "cashflow", "invoice approval"),
    "marketplace": ("marketplace", "seller", "buyer", "listing", "vendor"),
    "booking_platform": ("booking", "reservation", "schedule", "calendar", "appointment"),
    "content_platform": ("content", "editorial", "publish", "article", "cms"),
    "social_app": ("social", "community", "feed", "post", "moderation"),
    "learning_platform": ("learning", "course", "lesson", "training", "curriculum"),
    "ecommerce_app": ("ecommerce", "commerce", "checkout", "catalog", "order", "store"),
    "internal_tool": ("internal", "ops", "operations", "queue", "approval", "ticket", "incident"),
    "saas_dashboard": ("dashboard", "analytics", "metrics", "pipeline", "accounts", "revenue"),
}

OUT_OF_SCOPE_KEYWORDS = (
    "game engine",
    "operating system",
    "browser",
    "compiler",
    "database engine",
    "distributed database",
    "kernel",
    "3d editor",
    "video editor",
    "cad",
    "autonomous vehicle",
    "robotics control",
)

STARTER_ONLY_KEYWORDS = (
    "realtime chat",
    "live video",
    "streaming",
    "escrow",
    "trading platform",
    "banking",
    "medical diagnosis",
    "ride sharing",
    "uber",
    "airbnb",
    "dating app",
    "blockchain",
    "crypto exchange",
)


def _guess_app_type(user_idea):
    lowered = user_idea.lower()
    for app_type, keywords in APP_TYPE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return app_type
    return "saas_dashboard"


def analyze_product_request(user_idea):
    lowered = re.sub(r"\s+", " ", user_idea.strip().lower())
    closest_family = _guess_app_type(lowered)

    if any(keyword in lowered for keyword in OUT_OF_SCOPE_KEYWORDS):
        support_tier = "out_of_scope"
        handoff_mode = "starter_scaffold_with_gap_report"
        handoff_notes = [
            "The request exceeds the reliable family-based generator boundary.",
            "Generate the closest starter scaffold and list the unsupported bespoke areas explicitly.",
        ]
    elif any(keyword in lowered for keyword in STARTER_ONLY_KEYWORDS):
        support_tier = "starter_only"
        handoff_mode = "starter_scaffold_with_limitations"
        handoff_notes = [
            "The request is only partially supported as a starter scaffold.",
            "Generate the closest family-based starter and preserve limitations in the manifest.",
        ]
    else:
        support_tier = "supported"
        handoff_mode = "full_family_generation"
        handoff_notes = [
            "The request fits the supported family-based generator envelope.",
        ]

    refinement_steps = [
        f"Map the request into the closest supported family: {closest_family}.",
        "Prefer structured entities, workflows, permissions, and deployment artifacts over bespoke one-off code.",
        "If the request exceeds support, downgrade to the closest starter scaffold and retain limitation notes.",
    ]

    return {
        "support_tier": support_tier,
        "closest_family": closest_family,
        "handoff_mode": handoff_mode,
        "handoff_notes": handoff_notes,
        "refinement_steps": refinement_steps,
    }
