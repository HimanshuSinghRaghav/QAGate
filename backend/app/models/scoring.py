"""Scoring runs, per-check results, human overrides and the audit trail."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ScoringRun(Base, TimestampMixin):
    __tablename__ = "scoring_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), index=True)
    call_id: Mapped[str] = mapped_column(ForeignKey("calls.id"))
    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcripts.id"))

    call_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    engine_version: Mapped[str] = mapped_column(String(32), default="1.0.0")

    gate_decision: Mapped[str] = mapped_column(String(32))
    gate_reason: Mapped[str] = mapped_column(Text)

    score_with_fatals: Mapped[float] = mapped_column(Numeric(6, 3), default=0)
    score_without_fatals: Mapped[float] = mapped_column(Numeric(6, 3), default=0)
    lowest_confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=1)

    checks_total: Mapped[int] = mapped_column(Integer, default=0)
    criticals_failed: Mapped[int] = mapped_column(Integer, default=0)
    sampled_for_human: Mapped[bool] = mapped_column(Boolean, default=False)

    results: Mapped[list["CheckResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class CheckResult(Base, TimestampMixin):
    __tablename__ = "check_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("scoring_runs.id"), index=True)
    lead_id: Mapped[str] = mapped_column(String(64), index=True)

    check_id: Mapped[str] = mapped_column(String(64), index=True)
    check_version: Mapped[int] = mapped_column(Integer)
    check_name: Mapped[str] = mapped_column(String(160))
    type: Mapped[str] = mapped_column(String(16))
    critical: Mapped[bool] = mapped_column(Boolean, default=False)
    weight: Mapped[float] = mapped_column(Numeric(6, 3), default=1.0)

    status: Mapped[str] = mapped_column(String(20), index=True)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0)
    method: Mapped[str] = mapped_column(String(32))  # deterministic | fuzzy | llm | hybrid
    reason: Mapped[str] = mapped_column(Text, default="")

    expected: Mapped[dict | None] = mapped_column(JSONB)
    observed: Mapped[dict | None] = mapped_column(JSONB)
    # [{segment_id, text, timestamp, start_ms, end_ms, timing_source, context}]
    evidence: Mapped[list] = mapped_column(JSONB, default=list)
    # Full observation history for stateful checks (e.g. the address correction).
    observation_trail: Mapped[list] = mapped_column(JSONB, default=list)

    run: Mapped[ScoringRun] = relationship(back_populates="results")


class Override(Base, TimestampMixin):
    """A human overturning the machine. Logged, never silently dropped."""

    __tablename__ = "overrides"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    result_id: Mapped[str] = mapped_column(ForeignKey("check_results.id"), index=True)
    lead_id: Mapped[str] = mapped_column(String(64), index=True)

    previous_status: Mapped[str] = mapped_column(String(20))
    new_status: Mapped[str] = mapped_column(String(20))
    previous_gate: Mapped[str] = mapped_column(String(32))
    new_gate: Mapped[str] = mapped_column(String(32))

    overridden_by: Mapped[str] = mapped_column(String(64))
    reason_code: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text)


class AuditEvent(Base, TimestampMixin):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lead_id: Mapped[str | None] = mapped_column(String(64), index=True)
    actor: Mapped[str] = mapped_column(String(64), default="system")
    event: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
