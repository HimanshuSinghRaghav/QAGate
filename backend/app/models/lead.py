"""The sale in CRM, plus the CRM field values a factual check reads back against."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    retailer_id: Mapped[str] = mapped_column(ForeignKey("retailers.id"))
    plan_id: Mapped[str | None] = mapped_column(ForeignKey("plans.id"))

    agent_id: Mapped[str] = mapped_column(String(64))
    tl_id: Mapped[str | None] = mapped_column(String(64))
    campaign: Mapped[str | None] = mapped_column(String(64))
    site: Mapped[str | None] = mapped_column(String(64))
    last_completed_step: Mapped[str | None] = mapped_column(String(64))

    # Synthetic / sanitised only. Mirrors the mock identity filled into the
    # transcript so a factual comparison is still a real comparison.
    crm_fields: Mapped[dict] = mapped_column(JSONB, default=dict)

    calls: Mapped[list["Call"]] = relationship(back_populates="lead")


class Call(Base, TimestampMixin):
    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), index=True)

    recording_url: Mapped[str | None] = mapped_column(String(512))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None]
    status: Mapped[str] = mapped_column(String(32), default="ingested")

    lead: Mapped[Lead] = relationship(back_populates="calls")
