"""The scoring engine. Orchestration only - no business rules live here.

  load lead -> load transcript -> resolve check versions for the call date ->
  extract facts once -> run every check -> persist results with evidence ->
  apply the gate -> write an audit event

Extraction runs once per run, not once per check. Checks read the same FactStore, so
two checks can never disagree about what the call said.
"""
import logging
import uuid
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import CheckStatus
from app.models import (
    AuditEvent, Call, CheckResult, Lead, Plan, ScoringRun, Segment, Transcript,
)
from app.services.checks.base import CheckContext, CheckOutcome
from app.services.checks.registry import get_handler
from app.services.extraction import facts as facts_module
from app.services.gate.gate import decide
from app.services.scoring.version_resolver import checks_effective_on

log = logging.getLogger(__name__)
ENGINE_VERSION = "1.0.0"


class ScoringError(Exception):
    pass


def _latest_call(db: Session, lead_id: str) -> Call:
    call = db.execute(
        select(Call).where(Call.lead_id == lead_id).order_by(Call.started_at.desc())
    ).scalars().first()
    if not call:
        raise ScoringError(f"Lead {lead_id} has no call attached.")
    return call


def _transcript_for(db: Session, call_id: str) -> Transcript:
    transcript = db.execute(
        select(Transcript).where(Transcript.call_id == call_id)
        .order_by(Transcript.created_at.desc())
    ).scalars().first()
    if not transcript:
        raise ScoringError(
            f"Call {call_id} has no transcript. Ingestion comes before scoring."
        )
    return transcript


def run_scoring(db: Session, lead_id: str) -> ScoringRun:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise ScoringError(f"Lead {lead_id} not found.")

    call = _latest_call(db, lead_id)
    transcript = _transcript_for(db, call.id)
    segments = db.execute(
        select(Segment).where(Segment.transcript_id == transcript.id)
        .order_by(Segment.index)
    ).scalars().all()
    if not segments:
        raise ScoringError(f"Transcript {transcript.id} has no segments.")

    plan = db.get(Plan, lead.plan_id) if lead.plan_id else None
    definitions = checks_effective_on(db, lead.retailer_id, call.started_at)
    if not definitions:
        raise ScoringError(
            f"No check-library version is effective for retailer {lead.retailer_id} "
            f"on {call.started_at.isoformat()}."
        )

    store = facts_module.extract(segments, crm=lead.crm_fields)

    run = ScoringRun(
        id=f"run_{uuid.uuid4().hex[:12]}",
        lead_id=lead.id,
        call_id=call.id,
        transcript_id=transcript.id,
        call_date=call.started_at,
        engine_version=ENGINE_VERSION,
        gate_decision="PENDING",
        gate_reason="",
    )
    db.add(run)
    db.flush()

    results: list[CheckResult] = []
    for definition in definitions:
        outcome = _run_one(definition, lead, plan, transcript, segments, store)
        result = CheckResult(
            id=f"res_{uuid.uuid4().hex[:12]}",
            run_id=run.id,
            lead_id=lead.id,
            check_id=definition.check_id,
            check_version=definition.version,
            check_name=definition.name,
            type=definition.type,
            critical=definition.critical,
            weight=float(definition.weight),
            status=outcome.status,
            confidence=outcome.confidence,
            method=outcome.method,
            reason=outcome.reason,
            expected=outcome.expected,
            observed=outcome.observed,
            evidence=outcome.evidence,
            observation_trail=outcome.observation_trail,
        )
        db.add(result)
        results.append(result)

    gate = decide(lead.id, results)
    run.gate_decision = gate.decision
    run.gate_reason = gate.reason
    run.criticals_failed = gate.criticals_failed
    run.lowest_confidence = gate.lowest_confidence
    run.sampled_for_human = gate.sampled_for_human
    run.score_with_fatals = gate.score_with_fatals
    run.score_without_fatals = gate.score_without_fatals
    run.checks_total = len(results)

    call.status = "scored"
    db.add(AuditEvent(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        lead_id=lead.id,
        actor="system",
        event="scoring_run_completed",
        payload={
            "run_id": run.id,
            "engine_version": ENGINE_VERSION,
            "gate_decision": gate.decision,
            "criticals_failed": gate.criticals_failed,
            "checks": [{"check_id": r.check_id, "version": r.check_version,
                        "status": r.status, "confidence": float(r.confidence)}
                       for r in results],
        },
    ))
    db.commit()
    db.refresh(run)
    return run


def _run_one(definition, lead, plan, transcript, segments, store) -> CheckOutcome:
    handler_name = (definition.config or {}).get("handler")
    fn = get_handler(handler_name) if handler_name else None
    if fn is None:
        return CheckOutcome.error(
            f"No handler registered for '{handler_name}' "
            f"(check {definition.check_id} v{definition.version})."
        )
    ctx = CheckContext(lead=lead, plan=plan, transcript=transcript,
                       segments=segments, facts=store, definition=definition)
    try:
        return fn(ctx)
    except Exception as exc:  # noqa: BLE001
        log.exception("Check %s failed", definition.check_id)
        # A crashing checker must never look like a passing checker.
        return CheckOutcome.error(f"Checker raised {type(exc).__name__}: {exc}")


def latest_run(db: Session, lead_id: str) -> ScoringRun | None:
    return db.execute(
        select(ScoringRun).where(ScoringRun.lead_id == lead_id)
        .order_by(ScoringRun.created_at.desc())
    ).scalars().first()
