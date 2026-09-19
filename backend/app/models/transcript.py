"""Transcript storage.

Two levels on purpose:
  Transcript  -> the artefact attached to the lead
  Segment     -> one sentence-sized unit, the smallest thing evidence can point at

`redacted_text` is what any human or UI ever sees. `raw_text` is kept so the
extraction layer can work on the messy original, and is never returned by the API.
"""
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import Speaker, TimingSource
from app.models.base import Base, TimestampMixin


class Transcript(Base, TimestampMixin):
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), index=True)
    call_id: Mapped[str] = mapped_column(ForeignKey("calls.id"))

    provider: Mapped[str] = mapped_column(String(64), default="supplied")
    language: Mapped[str] = mapped_column(String(16), default="en-AU")
    timing_source: Mapped[str] = mapped_column(String(16), default=TimingSource.ESTIMATED)
    diarization_reliable: Mapped[bool] = mapped_column(Boolean, default=False)

    segments: Mapped[list["Segment"]] = relationship(
        back_populates="transcript", order_by="Segment.index", cascade="all, delete-orphan"
    )


class Segment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcripts.id"), index=True)

    index: Mapped[int] = mapped_column(Integer)
    turn_index: Mapped[int] = mapped_column(Integer)  # which raw speaker block it came from
    speaker: Mapped[str] = mapped_column(String(16), default=Speaker.UNKNOWN)
    speaker_confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5)

    raw_text: Mapped[str] = mapped_column(Text)
    redacted_text: Mapped[str] = mapped_column(Text)

    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    timing_source: Mapped[str] = mapped_column(String(16), default=TimingSource.ESTIMATED)

    redactions: Mapped[list] = mapped_column(JSONB, default=list)

    transcript: Mapped[Transcript] = relationship(back_populates="segments")

    @property
    def timestamp_label(self) -> str:
        total = self.start_ms // 1000
        return f"{total // 60:02d}:{total % 60:02d}"
