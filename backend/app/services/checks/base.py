"""Contract every check handler implements, plus the handler registry.

A handler receives a CheckContext (everything already loaded and extracted) and
returns a CheckOutcome. Handlers never touch the database and never decide the
gate; they report a status, a confidence and their evidence. That separation is
what makes the gate auditable.
"""
from collections.abc import Callable
from dataclasses import dataclass, field

from app.core.enums import CheckStatus
from app.models import CheckDefinition, Lead, Plan, Segment, Transcript
from app.services.extraction.facts import FactStore


@dataclass
class CheckContext:
    lead: Lead
    plan: Plan | None
    transcript: Transcript
    segments: list[Segment]
    facts: FactStore
    definition: CheckDefinition

    @property
    def config(self) -> dict:
        return self.definition.config or {}

    @property
    def crm(self) -> dict:
        return self.lead.crm_fields or {}

    def segment_by_id(self, segment_id: str) -> Segment | None:
        return next((s for s in self.segments if s.id == segment_id), None)


@dataclass
class CheckOutcome:
    status: CheckStatus
    confidence: float
    method: str = "deterministic"
    reason: str = ""
    expected: dict | None = None
    observed: dict | None = None
    evidence: list[dict] = field(default_factory=list)
    observation_trail: list[dict] = field(default_factory=list)

    @classmethod
    def not_applicable(cls, reason: str) -> "CheckOutcome":
        """Used when the inputs cannot support a judgement at all.

        This is the anti-false-critical valve: a check with no usable input is
        reported as un-scorable, not failed.
        """
        return cls(status=CheckStatus.NOT_APPLICABLE, confidence=0.0,
                   method="deterministic", reason=reason)

    @classmethod
    def error(cls, reason: str) -> "CheckOutcome":
        return cls(status=CheckStatus.ERROR, confidence=0.0, method="deterministic",
                   reason=reason)


Handler = Callable[[CheckContext], CheckOutcome]
_REGISTRY: dict[str, Handler] = {}


def handler(name: str) -> Callable[[Handler], Handler]:
    def wrap(fn: Handler) -> Handler:
        _REGISTRY[name] = fn
        return fn
    return wrap


def get_handler(name: str) -> Handler | None:
    return _REGISTRY.get(name)


def registered() -> list[str]:
    return sorted(_REGISTRY)


def evidence_from(obs) -> dict:
    """Build the evidence dict every result must carry."""
    return {
        "segment_id": obs.segment_id,
        "text": obs.text,
        "timestamp": obs.timestamp,
        "start_ms": obs.start_ms,
        "end_ms": obs.end_ms,
        "timing_source": obs.timing_source,
        "speaker": obs.speaker,
        "speaker_confidence": obs.speaker_confidence,
        "note": obs.note,
    }


def evidence_from_segment(seg: Segment, note: str = "") -> dict:
    return {
        "segment_id": seg.id,
        "text": seg.redacted_text,
        "timestamp": seg.timestamp_label,
        "start_ms": seg.start_ms,
        "end_ms": seg.end_ms,
        "timing_source": seg.timing_source,
        "speaker": seg.speaker,
        "speaker_confidence": float(seg.speaker_confidence),
        "note": note,
    }
