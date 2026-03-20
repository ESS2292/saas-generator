from crewai import Task

from templates.families import render_family_prompt_guide, render_product_boundary_guide


def create_generate_code_task(code_generator, user_idea, architecture_task, intake_context=None, spec_brief=None):
    family_guide = render_family_prompt_guide()
    boundary_guide = render_product_boundary_guide()
    intake_block = ""
    if intake_context:
        intake_block = f"""
        Intake classification:
        - support_tier: {intake_context['support_tier']}
        - closest_family: {intake_context['closest_family']}
        - handoff_mode: {intake_context['handoff_mode']}
        - handoff_notes: {intake_context['handoff_notes']}
        - refinement_steps: {intake_context['refinement_steps']}
        """
    spec_block = ""
    if spec_brief:
        spec_block = f"""
        Refined build brief:
        - goal: {spec_brief['goal']}
        - primary_users: {spec_brief['primary_users']}
        - core_entities: {spec_brief['core_entities']}
        - core_workflows: {spec_brief['core_workflows']}
        - page_intents: {spec_brief['page_intents']}
        - integration_hints: {spec_brief['integration_hints']}
        - risk_flags: {spec_brief['risk_flags']}
        - clarification_prompts: {spec_brief['clarification_prompts']}
        """
    return Task(
        description=f"""
        The user wants this SaaS product:

        {user_idea}

        {intake_block}

        {spec_block}

        Produce a STRICT JSON manifest for a SaaS starter that can be rendered by local templates.
        Do not generate source code.

        Return exactly one JSON object with these top-level keys:
        - app_name: string
        - slug: lowercase kebab-case string
        - app_type: one of saas_dashboard, crm_platform, support_desk, project_management, recruiting_platform, inventory_management, finance_ops, internal_tool, marketplace, booking_platform, content_platform, social_app, learning_platform, ecommerce_app
        - tagline: string
        - summary: string
        - primary_entity: string
        - theme: object with primary_color, accent_color, surface_color as 6-digit hex colors
        - dashboard: object with headline, subheadline, sections
        - pages: list of 1-6 objects with name, purpose, optional layout, optional widgets
        - workflows: list of 1-6 objects with name, steps, optional trigger, optional owner_role, optional states
        - auth: object with enabled, roles, demo_users
        - capabilities: object with search, notifications, automation booleans
        - integrations: object with email, payments, storage, webhook_topics
        - permissions: list of objects with resource, actions, roles
        - layout: object with navigation_style, density, panels
        - family_modules: list of strings naming the domain modules the generator should emphasize
        - support_tier: one of supported, starter_only, out_of_scope
        - closest_family: one of saas_dashboard, crm_platform, support_desk, project_management, recruiting_platform, inventory_management, finance_ops, internal_tool, marketplace, booking_platform, content_platform, social_app, learning_platform, ecommerce_app
        - refinement_steps: list of strings
        - handoff_notes: list of strings
        - spec_brief: object with goal, primary_users, core_entities, core_workflows, page_intents, integration_hints, risk_flags, clarification_prompts
        - data_model: list of 1-5 objects with name and fields
        - api_routes: list of 1-8 objects with path, method, summary
        - sample_records: list of up to 12 flat JSON objects to seed the UI

        App family guide:
        {family_guide}

        Product boundary guide:
        {boundary_guide}

        Rules:
        - Output valid JSON only
        - No markdown
        - No explanations
        - Use only double quotes
        - Choose the closest app_type for the user's request
        - Stay inside the product boundary guide above
        - If the request sounds broader than the supported envelope, downgrade it to the closest family-based starter instead of pretending to generate a fully bespoke system
        - support_tier and closest_family should align with the intake classification unless there is a very strong reason not to
        - spec_brief should align with the refined build brief unless there is a very strong reason not to
        - The local generator will derive the scaffold family and family defaults from app_type, so app_type selection must be deliberate
        - Make pages, workflows, primary_entity, and dashboard sections match the selected family
        - dashboard.sections must be a list of objects with title and description
        - pages must describe the major screens of the app and should include layout/widget hints when useful
        - workflows steps must be short strings and owner_role should come from auth.roles
        - auth.roles must include realistic app roles
        - auth.demo_users must include name, email, and role
        - permissions should describe who can read, create, update, approve, or moderate major resources
        - layout should describe how the app should feel at the shell level
        - family_modules should call out the major app-specific modules, workflows, or panels
        - capabilities booleans should reflect whether the app needs search, notifications, and automation
        - integrations should name realistic providers or provider placeholders for the app type
        - data_model fields must use simple types like string, number, boolean
        - api_routes must be realistic for the product idea
        - Keep sample_records flat and small
        """,
        expected_output="A valid JSON manifest for a SaaS starter project",
        agent=code_generator,
        context=[architecture_task]
    )
