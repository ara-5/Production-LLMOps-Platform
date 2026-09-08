from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnnotationCreate(BaseModel):
    trace_id: str
    annotator_email: str | None = None
    label: str | None = None
    score: float | None = None
    comment: str | None = None
    status: str = "completed"


class AnnotationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    trace_id: str
    annotator_email: str | None
    label: str | None
    score: float | None
    comment: str | None
    status: str
    created_at: datetime
