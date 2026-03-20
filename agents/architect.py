from crewai import Agent

architect = Agent(
    role="SaaS Architect",
    goal="Design a complete SaaS application architecture from a user prompt",
    backstory="Expert software architect specializing in scalable SaaS platforms",
    verbose=True
)