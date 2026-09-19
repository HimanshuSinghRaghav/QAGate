"""Versioned check library.

A check is never scored by id alone. It is scored by the version that was in effect
on the call date, which is why (check_id, version) is the primary key and every
result stores the resolved version back.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CheckDefinition(Base, TimestampMixin):
    __tablename__ = "check_definitions"

    check_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)

    retailer_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)

    type: Mapped[str] = mapped_column(String(16))          # CheckType
    critical: Mapped[bool] = mapped_column(Boolean, default=False)
    weight: Mapped[float] = mapped_column(Numeric(6, 3), default=1.0)

    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # How to evaluate it. Read by the handler registry; keeps logic declarative.
    # e.g. {"handler": "money_match", "fact": "intro_price", "plan_field": "intro_price",
    #       "tolerance": 0.0}
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
