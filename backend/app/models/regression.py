from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class RegressionTestRun(Base):
    __tablename__ = "regression_test_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False)
    prompt_version_id: Mapped[int] = mapped_column(ForeignKey("prompt_versions.id"), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    baseline_run_id: Mapped[int | None] = mapped_column(ForeignKey("regression_test_runs.id"), nullable=True)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="running")
    summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["RegressionTestItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", foreign_keys="RegressionTestItem.regression_test_run_id"
    )


class RegressionTestItem(Base):
    __tablename__ = "regression_test_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    regression_test_run_id: Mapped[int] = mapped_column(ForeignKey("regression_test_runs.id"), nullable=False)
    dataset_item_id: Mapped[int] = mapped_column(ForeignKey("dataset_items.id"), nullable=False)
    trace_id: Mapped[str] = mapped_column(ForeignKey("traces.trace_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped["RegressionTestRun"] = relationship(
        back_populates="items", foreign_keys=[regression_test_run_id]
    )
