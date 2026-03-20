from crewai import Task
from agents.code_generator import code_generator


def recursive_debug(code_output, errors):
    """
    Send errors back to the AI code generator and fix the code automatically.
    """
    debug_task = Task(
        description=f"""
        The following errors were detected in the generated SaaS code:

        {errors}

        The current generated manifest is:

        {code_output}

        Return a corrected JSON manifest only.
        Do not return code blocks, markdown, or explanations.
        """,
        expected_output="A corrected JSON manifest only",
        agent=code_generator
    )

    corrected_code = debug_task.execute_sync(agent=code_generator)
    return str(corrected_code)
