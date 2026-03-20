from engine.pipeline import generate_saas_app


def main():
    user_idea = input("Describe the SaaS you want to build: ").strip()
    if not user_idea:
        print("No SaaS idea entered. Exiting.")
        return

    result = generate_saas_app(user_idea)

    print(
        f"Support tier: {result['intake_context']['support_tier']} | "
        f"Closest family: {result['intake_context']['closest_family']} | "
        f"Handoff mode: {result['intake_context']['handoff_mode']}"
    )
    print(
        f"Spec brief: users={', '.join(result['spec_brief']['primary_users'])} | "
        f"entities={', '.join(result['spec_brief']['core_entities'])} | "
        f"workflows={', '.join(result['spec_brief']['core_workflows'])}"
    )

    if result["manifest_text"]:
        print(result["manifest_text"])

    if result["tests_passed"]:
        if result["deployed"]:
            print("Tests passed. SaaS deployed.")
        else:
            print("Tests passed. Deployment skipped.")
    else:
        print(f"Generation finished with errors: {result['latest_error'] or 'Verification not run.'}")


if __name__ == "__main__":
    main()
