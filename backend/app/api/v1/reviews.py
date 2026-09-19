from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.scoring import _out_result, _results_for
from app.core.db import get_db
from app.models import Lead, Plan, Retailer
from app.schemas.common import OverrideRequest, OverrideResponse
from app.services.present import lead_card
from app.services.scoring.review import ReviewError, apply_override, queue

router = APIRouter(tags=["review"])


@router.get("/reviews/queue")
def review_queue(decision: str | None = None, limit: int = 50,
                 db: Session = Depends(get_db)) -> list[dict]:
    retailers = {r.id: r for r in db.execute(select(Retailer)).scalars().all()}
    plans = {p.id: p for p in db.execute(select(Plan)).scalars().all()}
    rows = []
    for run in queue(db, decision, limit):
        lead = db.get(Lead, run.lead_id)
        results = _results_for(db, run.id)
        card = lead_card(
            lead, retailers.get(lead.retailer_id) if lead else None,
            plans.get(lead.plan_id) if lead and lead.plan_id else None,
            run, results,
        ) if lead else {}
        rows.append({
            "run_id": run.id,
            "lead_id": run.lead_id,
            "gate_decision": run.gate_decision,
            "gate_reason": run.gate_reason,
            "gate_headline": card.get("gate_headline"),
            "criticals_failed": run.criticals_failed,
            "lowest_confidence": float(run.lowest_confidence),
            "scored_at": run.created_at,
            "customer_name": card.get("customer_name"),
            "agent_name": card.get("agent_name"),
            "plan_name": card.get("plan_name"),
            "retailer_name": card.get("retailer_name"),
            "issue": card.get("issue"),
            "campaign_label": card.get("campaign_label"),
            "site_label": card.get("site_label"),
        })
    return rows


@router.post("/reviews/results/{result_id}/override", response_model=OverrideResponse)
def override_result(result_id: str, payload: OverrideRequest,
                    db: Session = Depends(get_db)) -> OverrideResponse:
    try:
        result, run, override = apply_override(
            db, result_id=result_id, new_status=payload.new_status,
            actor=payload.actor, reason=payload.reason, reason_code=payload.reason_code)
    except ReviewError as exc:
        raise HTTPException(400, str(exc)) from exc
    return OverrideResponse(
        result=_out_result(result), run=run,
        previous_gate=override.previous_gate,
        new_gate=override.new_gate,
    )
