"""Retailer-side reference data: who the retailer is and what the plan says.

Factual checks compare the transcript against THIS, never against another model's
opinion of what the plan should be.
"""
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Retailer(Base, TimestampMixin):
    __tablename__ = "retailers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    vertical: Mapped[str] = mapped_column(String(32))  # energy | broadband

    plans: Mapped[list["Plan"]] = relationship(back_populates="retailer")


class Plan(Base, TimestampMixin):
    """The rate card. The 'expected' side of every factual comparison."""

    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    retailer_id: Mapped[str] = mapped_column(ForeignKey("retailers.id"))
    name: Mapped[str] = mapped_column(String(128))

    intro_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    intro_term_months: Mapped[int | None]
    regular_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    download_mbps: Mapped[float | None] = mapped_column(Numeric(10, 2))
    upload_mbps: Mapped[float | None] = mapped_column(Numeric(10, 2))
    contract_term: Mapped[str | None] = mapped_column(String(64))
    modem_model: Mapped[str | None] = mapped_column(String(64))
    modem_upfront_cost: Mapped[float | None] = mapped_column(Numeric(10, 2))
    delivery_days_min: Mapped[int | None]
    delivery_days_max: Mapped[int | None]
    total_minimum_cost: Mapped[float | None] = mapped_column(Numeric(10, 2))
    development_fee: Mapped[float | None] = mapped_column(Numeric(10, 2))

    # Anything that does not deserve a column yet.
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)

    retailer: Mapped[Retailer] = relationship(back_populates="plans")
