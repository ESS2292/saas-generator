from pydantic import BaseModel


class GenerateRequest(BaseModel):
    prompt: str
    run_verification: bool = True
    auto_deploy: bool = False
    mode: str = "starter"
    app_name: str = ""
    target_users: str = ""
    core_entities: str = ""
    core_workflows: str = ""


class AuthRequest(BaseModel):
    email: str
    password: str
    name: str | None = None


class SecretRequest(BaseModel):
    name: str
    value: str
