"""Seed the database and score every synthetic lead.

    python -m app.seed.run          # create tables, load fixtures, score
    python -m app.seed.run --drop   # start from an empty schema
    python -m app.seed.run --no-score

Idempotent: re-running replaces fixture rows rather than duplicating them.
"""
import argparse
import logging
import uuid

from sqlalchemy import delete

from app.core.db import SessionLocal, engine
from app.models import (
    AuditEvent, Base, Call, CheckDefinition, CheckResult, Lead, Override, Plan,
    Retailer, ScoringRun, Segment, Transcript,
)
from app.seed.data.audio import recording_for
from app.seed.data.checks import CHECKS
from app.seed.data.leads import LEADS, PLAN, RETAILER
from app.services.scoring.engine import run_scoring
from app.services.transcript.service import ingest_transcript

log = logging.getLogger("seed")


def reset(db) -> None:
    for model in (Override, AuditEvent, CheckResult, ScoringRun, Segment, Transcript,
                  Call, Lead, CheckDefinition, Plan, Retailer):
        db.execute(delete(model))
    db.commit()


def load(db) -> None:
    db.merge(Retailer(**RETAILER))
    db.merge(Plan(**PLAN))
    for row in CHECKS:
        db.merge(CheckDefinition(**row))
    db.commit()
    log.info("Loaded retailer, plan and %d check definitions.", len(CHECKS))

    for spec in LEADS:
        lead = Lead(
            id=spec["id"], retailer_id=spec["retailer_id"], plan_id=spec["plan_id"],
            agent_id=spec["agent_id"], tl_id=spec["tl_id"], campaign=spec["campaign"],
            site=spec["site"], last_completed_step=spec["last_completed_step"],
            crm_fields=spec["crm_fields"],
        )
        db.merge(lead)
        db.flush()

        # A generated demo recording carries real character timings. Without one the
        # transcript falls back to estimated spans, and says so in every evidence row.
        recording = recording_for(spec["id"])

        call = Call(
            id=f"call_{spec['id']}", lead_id=spec["id"],
            recording_url=recording.url if recording else spec["call"]["recording_url"],
            started_at=spec["call"]["started_at"],
            duration_seconds=(recording.duration_seconds if recording
                              else spec["call"]["duration_seconds"]),
            status="transcribed",
        )
        db.merge(call)
        db.flush()

        transcript = ingest_transcript(
            db, lead_id=spec["id"], call_id=call.id, raw_text=spec["transcript"],
            provider="elevenlabs" if recording else "supplied",
            timings=recording.tokens if recording else None,
        )
        db.add(AuditEvent(
            id=f"aud_{uuid.uuid4().hex[:12]}", lead_id=spec["id"], actor="seed",
            event="call_ingested",
            payload={"call_id": call.id, "transcript_id": transcript.id},
        ))
        db.commit()
        log.info("Lead %s ingested (%s).", spec["id"], transcript.id)


def score_all(db) -> None:
    for spec in LEADS:
        run = run_scoring(db, spec["id"])
        log.info("Lead %s -> %s | %s", spec["id"], run.gate_decision, run.gate_reason)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s | %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop", action="store_true", help="drop and recreate all tables")
    parser.add_argument("--no-score", action="store_true", help="load fixtures only")
    args = parser.parse_args()

    if args.drop:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        reset(db)
        load(db)
        if not args.no_score:
            score_all(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
