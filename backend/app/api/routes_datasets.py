from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.datasets import Dataset, DatasetItem, DatasetVersion
from app.schemas.datasets import (
    DatasetCreate,
    DatasetItemOut,
    DatasetOut,
    DatasetVersionCreate,
    DatasetVersionOut,
    DatasetWithVersions,
)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetOut])
def list_datasets(db: Session = Depends(get_db)):
    return db.execute(select(Dataset).order_by(Dataset.name)).scalars().all()


@router.post("", response_model=DatasetOut, status_code=201)
def create_dataset(payload: DatasetCreate, db: Session = Depends(get_db)):
    if db.execute(select(Dataset).where(Dataset.name == payload.name)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="dataset name already exists")
    dataset = Dataset(**payload.model_dump())
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@router.get("/{dataset_id}", response_model=DatasetWithVersions)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="dataset not found")
    return dataset


@router.get("/{dataset_id}/versions", response_model=list[DatasetVersionOut])
def list_dataset_versions(dataset_id: int, db: Session = Depends(get_db)):
    rows = db.execute(
        select(DatasetVersion, func.count(DatasetItem.id))
        .outerjoin(DatasetItem, DatasetItem.dataset_version_id == DatasetVersion.id)
        .where(DatasetVersion.dataset_id == dataset_id)
        .group_by(DatasetVersion.id)
        .order_by(DatasetVersion.version)
    ).all()
    out = []
    for version, item_count in rows:
        dto = DatasetVersionOut.model_validate(version)
        dto.item_count = item_count
        out.append(dto)
    return out


@router.post("/{dataset_id}/versions", response_model=DatasetVersionOut, status_code=201)
def create_dataset_version(dataset_id: int, payload: DatasetVersionCreate, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="dataset not found")
    next_version = (
        db.execute(select(func.max(DatasetVersion.version)).where(DatasetVersion.dataset_id == dataset_id)).scalar_one() or 0
    ) + 1
    version = DatasetVersion(dataset_id=dataset_id, version=next_version, commit_message=payload.commit_message)
    db.add(version)
    db.flush()
    for item_in in payload.items:
        db.add(DatasetItem(dataset_version_id=version.id, **item_in.model_dump()))
    db.commit()
    db.refresh(version)
    dto = DatasetVersionOut.model_validate(version)
    dto.item_count = len(payload.items)
    return dto


@router.get("/{dataset_id}/versions/{version}/items", response_model=list[DatasetItemOut])
def get_dataset_version_items(dataset_id: int, version: int, db: Session = Depends(get_db)):
    dv = db.execute(
        select(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id, DatasetVersion.version == version)
    ).scalar_one_or_none()
    if dv is None:
        raise HTTPException(status_code=404, detail="dataset version not found")
    return db.execute(select(DatasetItem).where(DatasetItem.dataset_version_id == dv.id)).scalars().all()
