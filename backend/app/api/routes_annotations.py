from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.annotations import Annotation
from app.schemas.annotations import AnnotationCreate, AnnotationOut

router = APIRouter(prefix="/api/annotations", tags=["annotations"])


@router.get("/queue", response_model=list[AnnotationOut])
def annotation_queue(status: str = "pending", db: Session = Depends(get_db)):
    return db.execute(select(Annotation).where(Annotation.status == status).order_by(Annotation.created_at)).scalars().all()


@router.post("", response_model=AnnotationOut, status_code=201)
def create_annotation(payload: AnnotationCreate, db: Session = Depends(get_db)):
    annotation = Annotation(**payload.model_dump())
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation
