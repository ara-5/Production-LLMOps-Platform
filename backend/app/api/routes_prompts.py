import difflib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.prompts import Prompt, PromptVersion
from app.schemas.prompts import (
    PromptCreate,
    PromptDiffOut,
    PromptOut,
    PromptVersionCreate,
    PromptVersionOut,
    PromptWithVersions,
    RollbackRequest,
)

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.get("", response_model=list[PromptOut])
def list_prompts(db: Session = Depends(get_db)):
    return db.execute(select(Prompt).order_by(Prompt.name)).scalars().all()


@router.post("", response_model=PromptOut, status_code=201)
def create_prompt(payload: PromptCreate, db: Session = Depends(get_db)):
    if db.execute(select(Prompt).where(Prompt.name == payload.name)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="prompt name already exists")
    prompt = Prompt(name=payload.name)
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt


@router.get("/{prompt_id}", response_model=PromptWithVersions)
def get_prompt(prompt_id: int, db: Session = Depends(get_db)):
    prompt = db.get(Prompt, prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="prompt not found")
    return prompt


@router.get("/{prompt_id}/versions", response_model=list[PromptVersionOut])
def list_prompt_versions(prompt_id: int, db: Session = Depends(get_db)):
    return (
        db.execute(select(PromptVersion).where(PromptVersion.prompt_id == prompt_id).order_by(PromptVersion.version))
        .scalars()
        .all()
    )


@router.post("/{prompt_id}/versions", response_model=PromptVersionOut, status_code=201)
def create_prompt_version(prompt_id: int, payload: PromptVersionCreate, db: Session = Depends(get_db)):
    prompt = db.get(Prompt, prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="prompt not found")
    next_version = (db.execute(select(func.max(PromptVersion.version)).where(PromptVersion.prompt_id == prompt_id)).scalar_one() or 0) + 1
    version = PromptVersion(prompt_id=prompt_id, version=next_version, **payload.model_dump())
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def _get_version(db: Session, prompt_id: int, version_number: int) -> PromptVersion:
    version = db.execute(
        select(PromptVersion).where(PromptVersion.prompt_id == prompt_id, PromptVersion.version == version_number)
    ).scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=404, detail=f"prompt version {version_number} not found")
    return version


@router.get("/{prompt_id}/diff", response_model=PromptDiffOut)
def diff_prompt_versions(prompt_id: int, from_version: int, to_version: int, db: Session = Depends(get_db)):
    v_from = _get_version(db, prompt_id, from_version)
    v_to = _get_version(db, prompt_id, to_version)
    diff_lines = difflib.unified_diff(
        v_from.template.splitlines(keepends=True),
        v_to.template.splitlines(keepends=True),
        fromfile=f"v{from_version}",
        tofile=f"v{to_version}",
    )
    return PromptDiffOut(prompt_id=prompt_id, from_version=from_version, to_version=to_version, diff="".join(diff_lines))


@router.post("/{prompt_id}/rollback", response_model=PromptVersionOut, status_code=201)
def rollback_prompt(prompt_id: int, payload: RollbackRequest, db: Session = Depends(get_db)):
    target = _get_version(db, prompt_id, payload.to_version)
    next_version = (db.execute(select(func.max(PromptVersion.version)).where(PromptVersion.prompt_id == prompt_id)).scalar_one() or 0) + 1
    new_version = PromptVersion(
        prompt_id=prompt_id,
        version=next_version,
        template=target.template,
        variables=target.variables,
        commit_message=f"Rollback to v{payload.to_version}",
        created_by=payload.created_by,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version
