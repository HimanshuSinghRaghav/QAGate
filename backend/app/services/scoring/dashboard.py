"""Rollups. Read-only, computed from stored results so the numbers are auditable."""
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import CheckStatus, GateDecision
from app.models import CheckResult, Lead, Override, ScoringRun
from app.services.present import agent_name

REPEAT_OFFENCE_WINDOW_DAYS = 7
REPEAT_OFFENCE_THRESHOLD = 3


def overview(db: Session, retailer_id: str | None = None) -> dict:
    runs = list(db.execute(select(ScoringRun)).scalars().all())
    leads = {l.id: l for l in db.execute(select(Lead)).scalars().all()}
    if retailer_id:
        runs = [r for r in runs if leads.get(r.lead_id)
                and leads[r.lead_id].retailer_id == retailer_id]

    run_ids = {r.id for r in runs}
    results = [r for r in db.execute(select(CheckResult)).scalars().all()
               if r.run_id in run_ids]

    decisions = Counter(r.gate_decision for r in runs)
    total = len(runs) or 1

    critical_fails = [r for r in results if r.critical and r.status == CheckStatus.FAIL]
    top_failing = Counter(r.check_name for r in critical_fails)

    overrides = list(db.execute(select(Override)).scalars().all())
    agreements = [o for o in overrides if o.lead_id in {r.lead_id for r in runs}]

    return {
        "totals": {
            "sales_scored": len(runs),
            "auto_approved": decisions.get(GateDecision.AUTO_APPROVED, 0),
            "held": decisions.get(GateDecision.HELD, 0),
            "qa_review": decisions.get(GateDecision.QA_REVIEW, 0),
            "human_sample": decisions.get(GateDecision.HUMAN_SAMPLE, 0),
        },
        "first_pass_yield_pct": round(
            100 * decisions.get(GateDecision.AUTO_APPROVED, 0) / total, 2),
        "critical_fail_rate_pct": round(
            100 * sum(1 for r in runs if r.criticals_failed > 0) / total, 2),
        "avg_score_with_fatals": round(
            sum(float(r.score_with_fatals) for r in runs) / total, 2),
        "avg_score_without_fatals": round(
            sum(float(r.score_without_fatals) for r in runs) / total, 2),
        "top_failing_checks": [
            {"check": name, "failures": count,
             "share_pct": round(100 * count / max(len(critical_fails), 1), 1)}
            for name, count in top_failing.most_common(8)
        ],
        "auditor_agreement": _agreement(results, agreements),
        "repeat_offences": repeat_offences(db),
        "unscorable_checks": [
            {"check": name, "count": count}
            for name, count in Counter(
                r.check_name for r in results
                if r.status == CheckStatus.NOT_APPLICABLE
            ).most_common(8)
        ],
    }


def _agreement(results: list[CheckResult], overrides: list[Override]) -> dict:
    """How often a human left the machine's call alone."""
    reviewed = {o.result_id for o in overrides}
    overturned = sum(1 for o in overrides if o.previous_status != o.new_status)
    sampled = len(reviewed)
    return {
        "human_reviewed_results": sampled,
        "overturned": overturned,
        "agreement_rate_pct": round(100 * (sampled - overturned) / sampled, 2)
        if sampled else None,
        "note": "Agreement is measured only over results a human actually reviewed.",
    }


def repeat_offences(db: Session) -> list[dict]:
    """Same critical check failing 3+ times for one agent in a rolling 7 days."""
    cutoff = datetime.now(UTC) - timedelta(days=REPEAT_OFFENCE_WINDOW_DAYS)
    leads = {l.id: l for l in db.execute(select(Lead)).scalars().all()}
    runs = {r.id: r for r in db.execute(select(ScoringRun)).scalars().all()}

    buckets: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"lead_ids": [], "check_name": ""})
    for result in db.execute(select(CheckResult)).scalars().all():
        if not (result.critical and result.status == CheckStatus.FAIL):
            continue
        run = runs.get(result.run_id)
        lead = leads.get(result.lead_id)
        if not run or not lead or run.call_date < cutoff:
            continue
        bucket = buckets[(lead.agent_id, result.check_id)]
        bucket["lead_ids"].append(lead.id)
        bucket["check_name"] = result.check_name

    return [
        {
            "agent_id": agent_id,
            "agent_name": agent_name(agent_id),
            "check_id": check_id,
            "check_name": data["check_name"] or check_id,
            "failures": len(list(dict.fromkeys(data["lead_ids"]))),
            "lead_ids": list(dict.fromkeys(data["lead_ids"])),
            "window_days": REPEAT_OFFENCE_WINDOW_DAYS,
            "action": "Team lead flagged. Same critical fail three times in seven days.",
        }
        for (agent_id, check_id), data in sorted(buckets.items())
        if len(data["lead_ids"]) >= REPEAT_OFFENCE_THRESHOLD
    ]


def by_agent(db: Session) -> list[dict]:
    leads = {l.id: l for l in db.execute(select(Lead)).scalars().all()}
    rows: dict[str, dict] = defaultdict(
        lambda: {"scored": 0, "auto_approved": 0, "held": 0, "qa_review": 0})
    for run in db.execute(select(ScoringRun)).scalars().all():
        lead = leads.get(run.lead_id)
        if not lead:
            continue
        row = rows[lead.agent_id]
        row["scored"] += 1
        if run.gate_decision == GateDecision.HELD:
            row["held"] += 1
        elif run.gate_decision == GateDecision.QA_REVIEW:
            row["qa_review"] += 1
        else:
            row["auto_approved"] += 1
    return [
        {"agent_id": agent, "agent_name": agent_name(agent), **row,
         "first_pass_yield_pct": round(100 * row["auto_approved"] / row["scored"], 2)}
        for agent, row in sorted(rows.items())
    ]
