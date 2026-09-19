from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.enums import CheckStatus
from app.models import AuditEvent, CheckResult, Lead, Plan, Retailer
from app.schemas.common import CheckResultOut, ScoredLeadOut
from app.services.present import EVENT_LABELS, lead_card, result_view
from app.services.scoring.engine import ScoringError, latest_run, run_scoring

router = APIRouter(tags=["scoring"])

_STATUS_RANK = {
    CheckStatus.FAIL: 0,
    CheckStatus.ERROR: 1,
    CheckStatus.REVIEW: 2,
    CheckStatus.PASS: 3,
    CheckStatus.NOT_APPLICABLE: 4,
}


def _results_for(db: Session, run_id: str) -> list[CheckResult]:
    rows = db.execute(
        select(CheckResult).where(CheckResult.run_id == run_id)
    ).scalars().all()
    return sorted(
        rows,
        key=lambda r: (_STATUS_RANK.get(r.status, 9), 0 if r.critical else 1, r.check_id),
    )


def _out_result(result: CheckResult) -> CheckResultOut:
    return CheckResultOut.model_validate(result).model_copy(update=result_view(result))


def _case(db: Session, lead: Lead, run=None, results: list[CheckResult] | None = None) -> dict:
    retailer = db.get(Retailer, lead.retailer_id)
    plan = db.get(Plan, lead.plan_id) if lead.plan_id else None
    if run is None:
        run = latest_run(db, lead.id)
    if results is None and run:
        results = _results_for(db, run.id)
    return lead_card(lead, retailer, plan, run, results or [])


def _bundle(db: Session, run) -> ScoredLeadOut:
    results = _results_for(db, run.id)
    lead = db.get(Lead, run.lead_id)
    return ScoredLeadOut(
        run=run,
        critical=[_out_result(r) for r in results
                  if r.critical and r.status != CheckStatus.NOT_APPLICABLE],
        non_critical=[_out_result(r) for r in results
                      if not r.critical and r.status != CheckStatus.NOT_APPLICABLE],
        unscorable=[_out_result(r) for r in results if r.status == CheckStatus.NOT_APPLICABLE],
        case=_case(db, lead, run, results) if lead else None,
    )


@router.post("/leads/{lead_id}/score", response_model=ScoredLeadOut)
def score_lead(lead_id: str, db: Session = Depends(get_db)) -> ScoredLeadOut:
    try:
        run = run_scoring(db, lead_id)
    except ScoringError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _bundle(db, run)


@router.get("/leads/{lead_id}/results", response_model=ScoredLeadOut)
def get_results(lead_id: str, db: Session = Depends(get_db)) -> ScoredLeadOut:
    run = latest_run(db, lead_id)
    if not run:
        raise HTTPException(404, f"Lead {lead_id} has not been scored yet.")
    return _bundle(db, run)


@router.get("/leads/{lead_id}")
def get_lead(lead_id: str, db: Session = Depends(get_db)) -> dict:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, f"Lead {lead_id} not found.")
    return _case(db, lead)


@router.get("/leads")
def list_leads(db: Session = Depends(get_db)) -> list[dict]:
    leads = db.execute(select(Lead).order_by(Lead.id)).scalars().all()
    retailers = {r.id: r for r in db.execute(select(Retailer)).scalars().all()}
    plans = {p.id: p for p in db.execute(select(Plan)).scalars().all()}
    out = []
    for lead in leads:
        run = latest_run(db, lead.id)
        results = _results_for(db, run.id) if run else []
        out.append(lead_card(
            lead, retailers.get(lead.retailer_id),
            plans.get(lead.plan_id) if lead.plan_id else None,
            run, results,
        ))
    return out


@router.get("/leads/{lead_id}/audit")
def audit_trail(lead_id: str, db: Session = Depends(get_db)) -> list[dict]:
    events = db.execute(
        select(AuditEvent).where(AuditEvent.lead_id == lead_id)
        .order_by(AuditEvent.created_at)
    ).scalars().all()
    return [{
        "id": e.id, "at": e.created_at, "actor": e.actor,
        "event": e.event, "event_label": EVENT_LABELS.get(e.event, e.event.replace("_", " ")),
        "payload": e.payload,
    } for e in events]
