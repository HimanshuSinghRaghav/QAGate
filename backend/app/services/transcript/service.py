"""Transcript ingestion: raw text in, stored + redacted + timed segments out."""
import uuid

from sqlalchemy.orm import Session

from app.core.enums import TimingSource
from app.models import Segment, Transcript
from app.services.transcript import parser, timing
from app.services.transcript.redaction import redact


def ingest_transcript(
    db: Session,
    *,
    lead_id: str,
    call_id: str,
    raw_text: str,
    provider: str = "supplied",
    timings: list[dict] | None = None,
) -> Transcript:
    """Store a transcript as timed, redacted segments.

    `timings` is the provider's timed payload - [{"text", "start_ms", "end_ms"}] of
    characters or words. When it is present every segment carries a real audio
    position; when it is absent the spans are estimated and labelled as such.
    """
    parsed, diarization_reliable = parser.parse(raw_text)
    texts = [p.text for p in parsed]

    if timings:
        spans = timing.apply_asr_timings(timings, texts)
        timing_source = TimingSource.ASR
    else:
        spans = timing.estimate_timings(texts)
        timing_source = TimingSource.ESTIMATED

    transcript = Transcript(
        id=f"tr_{uuid.uuid4().hex[:12]}",
        lead_id=lead_id,
        call_id=call_id,
        provider=provider,
        timing_source=timing_source,
        diarization_reliable=diarization_reliable,
    )
    db.add(transcript)

    for index, (p, (start_ms, end_ms)) in enumerate(zip(parsed, spans, strict=True)):
        report = redact(p.text)
        db.add(
            Segment(
                id=f"{transcript.id}_seg_{index:04d}",
                transcript_id=transcript.id,
                index=index,
                turn_index=p.turn_index,
                speaker=p.speaker,
                speaker_confidence=p.speaker_confidence,
                raw_text=p.text,
                redacted_text=report.text,
                start_ms=start_ms,
                end_ms=end_ms,
                timing_source=timing_source,
                redactions=report.findings,
            )
        )

    db.flush()
    return transcript
