from pydantic import BaseModel, Field


class RunStage(BaseModel):
    key: str
    label: str
    state: str


class RunArtifact(BaseModel):
    artifact_type: str
    label: str
    path: str


class RunLogEntry(BaseModel):
    level: str
    message: str
    created_at: str


class RunResultSummary(BaseModel):
    success: bool = False
    app_root: str | None = None
    tests_passed: bool = False
    deployed: bool = False
    latest_error: str = ""
    saved_files_count: int = 0
    app_name: str = "Generated App"
    closest_family: str = ""
    support_tier: str = ""
    primary_users: list[str] = Field(default_factory=list)
    core_entities: list[str] = Field(default_factory=list)
    core_workflows: list[str] = Field(default_factory=list)


class RunView(BaseModel):
    id: str
    user_id: int
    prompt: str
    app_root: str
    run_verification: bool
    auto_deploy: bool
    status: str
    created_at: str
    updated_at: str
    result: RunResultSummary | None = None
    error: str = ""
    friendly_error: str = ""
    stages: list[RunStage] = Field(default_factory=list)
    current_stage: RunStage | None = None
    logs: list[RunLogEntry] = Field(default_factory=list)
    artifacts: list[RunArtifact] = Field(default_factory=list)
