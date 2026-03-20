from crewai import Task


def create_plan_task(architect, user_idea, intake_context=None, spec_brief=None):
    intake_block = ""
    if intake_context:
        intake_block = f"""
        Intake classification:
        - support_tier: {intake_context['support_tier']}
        - closest_family: {intake_context['closest_family']}
        - handoff_mode: {intake_context['handoff_mode']}
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
        The user wants to build this SaaS product:

        {user_idea}

        {intake_block}

        {spec_block}

        Design a complete SaaS architecture for this exact product.

        You must define:
        1. what the SaaS does
        2. target users
        3. backend API needs
        4. frontend dashboard needs
        5. authentication needs
        6. database structure
        7. deployment approach

        Be specific to the user's idea.
        """,
        expected_output="""
        A tailored SaaS architecture plan specific to the user's idea,
        including backend, frontend, authentication, database, and deployment.
        """,
        agent=architect
    )
