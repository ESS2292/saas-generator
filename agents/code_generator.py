from crewai import Agent

code_generator = Agent(
    role="Senior Full Stack Engineer",
    goal="Generate complete SaaS application code based on architecture plans",
    backstory="Expert developer skilled in FastAPI, React, and database design",
    verbose=True
)