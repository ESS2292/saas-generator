import re


ACTOR_KEYWORDS = (
    ("admin", ("admin", "administrator")),
    ("manager", ("manager", "operator", "ops", "operations")),
    ("customer", ("customer", "client", "buyer", "shopper", "guest")),
    ("seller", ("seller", "vendor", "merchant", "creator")),
    ("member", ("member", "team", "staff", "employee", "user")),
    ("student", ("student", "learner")),
    ("teacher", ("teacher", "instructor", "coach")),
)

ENTITY_KEYWORDS = (
    ("booking", ("booking", "reservation", "appointment")),
    ("order", ("order", "checkout", "purchase")),
    ("listing", ("listing", "catalog", "product")),
    ("customer", ("customer", "client", "account")),
    ("content", ("content", "article", "post")),
    ("lesson", ("lesson", "course", "training")),
    ("ticket", ("ticket", "incident", "approval")),
)

WORKFLOW_HINTS = (
    ("approval flow", ("approve", "approval", "review")),
    ("fulfillment flow", ("fulfillment", "shipment", "delivery", "order")),
    ("scheduling flow", ("schedule", "booking", "reservation", "appointment")),
    ("publishing flow", ("publish", "editorial", "content", "article")),
    ("moderation flow", ("moderation", "report", "community", "social")),
    ("learning progress flow", ("lesson", "course", "curriculum", "training")),
)

INTEGRATION_HINTS = (
    ("payments", ("payment", "checkout", "billing", "subscription", "invoice")),
    ("email", ("email", "notification", "newsletter")),
    ("storage", ("upload", "file", "asset", "image", "document")),
    ("calendar", ("calendar", "schedule", "booking", "appointment")),
    ("messaging", ("chat", "sms", "message")),
)

RISK_HINTS = (
    ("realtime", ("realtime", "real-time", "live", "streaming")),
    ("compliance", ("medical", "healthcare", "legal", "finance", "banking")),
    ("market network effects", ("marketplace", "social", "community")),
    ("complex infrastructure", ("browser", "operating system", "compiler", "engine")),
)


def _collect_matches(text, keyword_map, limit=5):
    matches = []
    for label, keywords in keyword_map:
        if any(keyword in text for keyword in keywords):
            matches.append(label)
    return matches[:limit]


def _normalize_goal(user_idea):
    collapsed = re.sub(r"\s+", " ", user_idea.strip())
    if not collapsed:
        return "Build a family-based application starter from the prompt."
    sentence = collapsed[0].upper() + collapsed[1:]
    return sentence[:-1] if sentence.endswith(".") else sentence


def refine_product_spec(user_idea, intake_context):
    lowered = re.sub(r"\s+", " ", user_idea.strip().lower())
    closest_family = intake_context["closest_family"]

    primary_users = _collect_matches(lowered, ACTOR_KEYWORDS)
    if not primary_users:
        primary_users = ["operator", "customer"]

    core_entities = _collect_matches(lowered, ENTITY_KEYWORDS)
    if closest_family == "booking_platform" and "booking" not in core_entities:
        core_entities.insert(0, "booking")
    if closest_family == "crm_platform" and "customer" not in core_entities:
        core_entities.insert(0, "customer")
    if closest_family == "support_desk" and "ticket" not in core_entities:
        core_entities.insert(0, "ticket")
    if closest_family == "project_management" and "project" not in core_entities:
        core_entities.insert(0, "project")
    if closest_family == "recruiting_platform" and "candidate" not in core_entities:
        core_entities.insert(0, "candidate")
    if closest_family == "inventory_management" and "item" not in core_entities:
        core_entities.insert(0, "item")
    if closest_family == "finance_ops" and "invoice" not in core_entities:
        core_entities.insert(0, "invoice")
    if closest_family == "marketplace" and "listing" not in core_entities:
        core_entities.insert(0, "listing")
    if closest_family == "ecommerce_app" and "order" not in core_entities:
        core_entities.insert(0, "order")
    core_entities = core_entities[:5] or ["record"]

    workflows = _collect_matches(lowered, WORKFLOW_HINTS)
    if not workflows:
        workflows = ["operational workflow"]

    integrations = _collect_matches(lowered, INTEGRATION_HINTS)
    risk_flags = _collect_matches(lowered, RISK_HINTS)
    if intake_context["support_tier"] != "supported":
        risk_flags.append("support boundary")
    risk_flags = list(dict.fromkeys(risk_flags))[:6]

    page_intents = [
        "overview dashboard",
        f"{closest_family.replace('_', ' ')} workspace",
        "records management",
    ]
    if "approval flow" in workflows:
        page_intents.append("approval queue")
    if "publishing flow" in workflows:
        page_intents.append("content calendar")
    if "fulfillment flow" in workflows:
        page_intents.append("order pipeline")
    if "scheduling flow" in workflows:
        page_intents.append("availability board")
    page_intents = list(dict.fromkeys(page_intents))[:5]

    clarification_prompts = [
        f"Confirm the main success metric for the {closest_family.replace('_', ' ')} app.",
        "Confirm the highest-priority workflow to optimize first.",
        "Confirm the minimum set of entities required for the first version.",
    ]
    if integrations:
        clarification_prompts.append("Confirm which external integrations are required in the first release.")
    clarification_prompts = clarification_prompts[:4]

    return {
        "goal": _normalize_goal(user_idea),
        "closest_family": closest_family,
        "support_tier": intake_context["support_tier"],
        "primary_users": primary_users,
        "core_entities": core_entities,
        "core_workflows": workflows,
        "page_intents": page_intents,
        "integration_hints": integrations,
        "risk_flags": risk_flags,
        "clarification_prompts": clarification_prompts,
    }
