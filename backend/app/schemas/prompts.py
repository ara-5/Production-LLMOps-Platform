from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PromptCreate(BaseModel):
    name: str


class PromptVersionCreate(BaseModel):
    template: str
    variables: dict = {}
    commit_message: str | None = None
    created_by: str | None = None


class RollbackRequest(BaseModel):
    to_version: int
    created_by: str | None = None


class PromptVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    prompt_id: int
    version: int
    template: str
    variables: dict
    commit_message: str | None
    created_by: str | None
    is_active: bool
    created_at: datetime


class PromptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: datetime


class PromptWithVersions(PromptOut):
    versions: list[PromptVersionOut] = []


class PromptDiffOut(BaseModel):
    prompt_id: int
    from_version: int
    to_version: int
    diff: str
