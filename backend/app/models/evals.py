from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class EvalScore(Base):
    __tablename__ = "eval_scores"
    __table_args__ = (
        Index("ix_eval_scores_trace_metric", "trace_id", "metric_name"),
        Index("ix_eval_scores_metric_name", "metric_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trace_id: Mapped[str] = mapped_column(ForeignKey("traces.trace_id"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    judge_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    judge_trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trace: Mapped["Trace"] = relationship(back_populates="eval_scores")
