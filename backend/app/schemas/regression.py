from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RegressionRunCreate(BaseModel):
    name: str
    dataset_version_id: int
    prompt_version_id: int
    model_id: str
    baseline_run_id: int | None = None
    limit: int | None = None


class RegressionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    dataset_version_id: int
    prompt_version_id: int
    model_id: str
    baseline_run_id: int | None
    status: str
    summary: dict
    started_at: datetime
    ended_at: datetime | None


class SetBaselineRequest(BaseModel):
    pass
