from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None


class DatasetItemIn(BaseModel):
    external_id: str | None = None
    question: str
    expected_answer: str | None = None
    expected_retrieval_doc_ids: list[str] = []
    relevance_grades: dict = {}
    item_metadata: dict = {}


class DatasetVersionCreate(BaseModel):
    commit_message: str | None = None
    items: list[DatasetItemIn]


class DatasetItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    external_id: str | None
    question: str
    expected_answer: str | None
    expected_retrieval_doc_ids: list[str]
    relevance_grades: dict
    item_metadata: dict


class DatasetVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dataset_id: int
    version: int
    commit_message: str | None
    created_at: datetime
    item_count: int = 0


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None
    created_at: datetime


class DatasetWithVersions(DatasetOut):
    versions: list[DatasetVersionOut] = []
