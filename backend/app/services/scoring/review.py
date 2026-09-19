"""Human review and override.

An override does three things, all of them mandatory:
  * changes the result
  * writes an immutable Override row holding both the before and after gate state
  * re-runs the gate, because overturning one critical check can legitimately
    release the sale - but only through the same gate logic, never by hand
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import CheckStatus
from app.models import AuditEvent, CheckResult, Override, ScoringRun
from app.services.gate.gate import decide


class ReviewError(Exception):
    pass


def apply_override(
    db: Session,
    *,
    result_id: str,
    new_status: CheckStatus,
    actor: str,
    reason: str,
    reason_code: str = "auditor_judgement",
) -> tuple[CheckResult, ScoringRun, Override]:
    result = db.get(CheckResult, result_id)
    if not result:
        raise ReviewError(f"Check result {result_id} not found.")
    run = db.get(ScoringRun, result.run_id)
    if not run:
        raise ReviewError(f"Scoring run {result.run_id} not found.")
    if not reason or not reason.strip():
        raise ReviewError("An override requires a reason. Silent overrides are not allowed.")

    previous_status = result.status
    previous_gate = run.gate_decision

    result.status = new_status
    # A human decision is recorded as human-certain, but the method records who decided.
    result.confidence = 1.0
    result.method = "human_override"
    result.reason = f"Overridden by {actor}: {reason.strip()}"

    siblings = db.execute(
        select(CheckResult).where(CheckResult.run_id == run.id)
    ).scalars().all()
    gate = decide(run.lead_id, siblings)

    run.gate_decision = gate.decision
    run.gate_reason = gate.reason
    run.criticals_failed = gate.criticals_failed
    run.lowest_confidence = gate.lowest_confidence
    run.score_with_fatals = gate.score_with_fatals
    run.score_without_fatals = gate.score_without_fatals

    override = Override(
        id=f"ovr_{uuid.uuid4().hex[:12]}",
        result_id=result.id,
        lead_id=run.lead_id,
        previous_status=previous_status,
        new_status=new_status,
        previous_gate=previous_gate,
        new_gate=gate.decision,
        overridden_by=actor,
        reason_code=reason_code,
        reason=reason.strip(),
    )
    db.add(override)
    db.add(AuditEvent(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        lead_id=run.lead_id,
        actor=actor,
        event="check_result_overridden",
        payload={
            "result_id": result.id, "check_id": result.check_id,
            "check_version": result.check_version,
            "from_status": previous_status, "to_status": new_status,
            "from_gate": previous_gate, "to_gate": gate.decision,
            "reason_code": reason_code, "reason": reason.strip(),
        },
    ))
    db.commit()
    db.refresh(result)
    db.refresh(run)
    return result, run, override


def queue(db: Session, decision: str | None = None, limit: int = 50) -> list[ScoringRun]:
    stmt = select(ScoringRun).order_by(ScoringRun.created_at.desc()).limit(limit)
    if decision:
        stmt = stmt.where(ScoringRun.gate_decision == decision)
    return list(db.execute(stmt).scalars().all())
