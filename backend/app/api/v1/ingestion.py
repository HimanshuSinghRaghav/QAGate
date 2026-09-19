"""Ingestion: the pipeline everything else depends on."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import AuditEvent, Call, Lead, Segment, Transcript
from app.schemas.common import IngestRequest, IngestResponse, TranscriptOut
from app.services.transcript.service import ingest_transcript

router = APIRouter(tags=["ingestion"])


@router.post("/calls/ingest", response_model=IngestResponse, status_code=201)
def ingest_call(payload: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:
    lead = db.get(Lead, payload.lead_id)
    if not lead:
        raise HTTPException(404, f"Lead {payload.lead_id} not found. Load the lead first.")

    call = Call(
        id=f"call_{uuid.uuid4().hex[:12]}",
        lead_id=lead.id,
        recording_url=payload.recording_url,
        started_at=payload.call_started_at,
        duration_seconds=payload.duration_seconds,
        status="ingested",
    )
    db.add(call)
    db.flush()

    transcript = None
    if payload.transcript_text:
        transcript = ingest_transcript(
            db, lead_id=lead.id, call_id=call.id, raw_text=payload.transcript_text
        )
        call.status = "transcribed"

    db.add(AuditEvent(
        id=f"aud_{uuid.uuid4().hex[:12]}", lead_id=lead.id, actor="dialler",
        event="call_ingested",
        payload={"call_id": call.id, "recording_url": payload.recording_url,
                 "transcript_id": transcript.id if transcript else None},
    ))
    db.commit()

    segment_count = db.execute(
        select(Segment).where(Segment.transcript_id == transcript.id)
    ).scalars().all() if transcript else []

    return IngestResponse(
        lead_id=lead.id, call_id=call.id,
        transcript_id=transcript.id if transcript else None,
        segments=len(segment_count),
        diarization_reliable=transcript.diarization_reliable if transcript else False,
        timing_source=transcript.timing_source if transcript else "none",
    )


@router.get("/leads/{lead_id}/transcript", response_model=TranscriptOut)
def get_transcript(lead_id: str, db: Session = Depends(get_db)) -> TranscriptOut:
    """Returns redacted text only. `raw_text` is never exposed through the API."""
    transcript = db.execute(
        select(Transcript).where(Transcript.lead_id == lead_id)
        .order_by(Transcript.created_at.desc())
    ).scalars().first()
    if not transcript:
        raise HTTPException(404, f"No transcript for lead {lead_id}.")
    segments = db.execute(
        select(Segment).where(Segment.transcript_id == transcript.id)
        .order_by(Segment.index)
    ).scalars().all()
    return TranscriptOut(
        transcript_id=transcript.id, lead_id=transcript.lead_id,
        timing_source=transcript.timing_source,
        diarization_reliable=transcript.diarization_reliable,
        segments=segments,
    )
