from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import CheckStatus, GateDecision


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IngestRequest(BaseModel):
    lead_id: str
    retailer_id: str
    plan_id: str | None = None
    recording_url: str | None = None
    call_started_at: datetime
    duration_seconds: int | None = None
    # Supplied transcript text. Replace with the transcription callback on real traffic.
    transcript_text: str | None = None


class IngestResponse(BaseModel):
    lead_id: str
    call_id: str
    transcript_id: str | None
    segments: int
    diarization_reliable: bool
    timing_source: str


class SegmentOut(ORMModel):
    id: str
    index: int
    speaker: str
    speaker_confidence: float
    text: str = Field(validation_alias="redacted_text")
    start_ms: int
    end_ms: int
    timing_source: str
    timestamp: str = Field(validation_alias="timestamp_label")


class TranscriptOut(BaseModel):
    transcript_id: str
    lead_id: str
    timing_source: str
    diarization_reliable: bool
    segments: list[SegmentOut]


class EvidenceOut(BaseModel):
    segment_id: str | None = None
    text: str | None = None
    timestamp: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    timing_source: str | None = None
    speaker: str | None = None
    speaker_confidence: float | None = None
    note: str | None = None


class CheckResultOut(ORMModel):
    id: str
    check_id: str
    check_version: int
    check_name: str
    type: str
    critical: bool
    weight: float
    status: CheckStatus
    confidence: float
    method: str
    reason: str
    expected: dict | None
    observed: dict | None
    evidence: list[dict]
    observation_trail: list[dict]
    expected_label: str | None = None
    observed_label: str | None = None
    expected_caption: str | None = None
    observed_caption: str | None = None
    status_label: str | None = None
    type_label: str | None = None
    issue: str | None = None


class ScoringRunOut(ORMModel):
    id: str
    lead_id: str
    call_id: str
    transcript_id: str
    call_date: datetime
    engine_version: str
    gate_decision: GateDecision
    gate_reason: str
    score_with_fatals: float
    score_without_fatals: float
    lowest_confidence: float
    checks_total: int
    criticals_failed: int
    sampled_for_human: bool


class ScoredLeadOut(BaseModel):
    run: ScoringRunOut
    critical: list[CheckResultOut]
    non_critical: list[CheckResultOut]
    unscorable: list[CheckResultOut]
    case: dict | None = None


class OverrideRequest(BaseModel):
    new_status: CheckStatus
    actor: str
    reason: str = Field(min_length=3)
    reason_code: str = "auditor_judgement"


class OverrideResponse(BaseModel):
    result: CheckResultOut
    run: ScoringRunOut
    previous_gate: GateDecision
    new_gate: GateDecision
