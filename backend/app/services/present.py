"""Human-readable labels for the QA console.

IDs stay in the database. Reviewers should never have to decode agent_a or $35.9 AUD.
"""
from __future__ import annotations

from app.core.enums import CheckStatus, GateDecision
from app.models import CheckResult, Lead, Plan, Retailer, ScoringRun

AGENTS = {
    "agent_a": "Marco Santos",
    "agent_b": "Aisha Rahman",
}
TEAM_LEADS = {
    "tl_01": "Priya Nair",
}
SITES = {
    "site_01": "Parramatta · Floor 1",
    "site_02": "Parramatta · Floor 2",
}
CAMPAIGNS = {
    "inbound": "Inbound",
    "paid_search": "Paid search",
    "affiliate": "Affiliate",
    "owned_site": "Owned site",
}
RETAILERS = {
    "retailer_1": "FibreLink",
}

GATE_HEADLINE = {
    GateDecision.AUTO_APPROVED: "This sale can ship",
    GateDecision.HELD: "This sale is stopped",
    GateDecision.QA_REVIEW: "A person must decide",
    GateDecision.HUMAN_SAMPLE: "Clean call, sampled for QA",
}

GATE_NEXT = {
    GateDecision.AUTO_APPROVED:
        "Every critical check passed with enough confidence. The sale auto-submits.",
    GateDecision.HELD:
        "A critical check failed. A team lead reviews the evidence, then keeps the hold or overrides with a reason.",
    GateDecision.QA_REVIEW:
        "The engine is not sure. Uncertainty never auto-passes — a QA auditor must resolve the open checks.",
    GateDecision.HUMAN_SAMPLE:
        "The sale looks clean. It was sampled so humans can measure whether the model agrees with auditors.",
}

STATUS_LABEL = {
    CheckStatus.PASS: "Passed",
    CheckStatus.FAIL: "Failed",
    CheckStatus.REVIEW: "Needs a person",
    CheckStatus.NOT_APPLICABLE: "Cannot score",
    CheckStatus.ERROR: "Checker error",
}

TYPE_LABEL = {
    "VERBATIM": "Script",
    "FACTUAL": "Fact",
    "BEHAVIOUR": "Behaviour",
}

ENUM_LABELS = {
    "month_to_month": "Month to month",
    "one_to_one": "One-to-one (likely ASR for month-to-month)",
    "no_lock_in": "No lock-in",
}


def agent_name(agent_id: str | None) -> str:
    if not agent_id:
        return "—"
    return AGENTS.get(agent_id, agent_id.replace("_", " ").title())


def tl_name(tl_id: str | None) -> str:
    if not tl_id:
        return "—"
    return TEAM_LEADS.get(tl_id, tl_id.replace("_", " ").title())


def site_label(site: str | None) -> str:
    if not site:
        return "—"
    return SITES.get(site, site.replace("_", " ").title())


def campaign_label(campaign: str | None) -> str:
    if not campaign:
        return "—"
    return CAMPAIGNS.get(campaign, campaign.replace("_", " ").title())


def retailer_name(retailer: Retailer | None, retailer_id: str | None = None) -> str:
    if retailer and retailer.name and retailer.name.lower() not in {"retailer 1", "retailer1"}:
        return retailer.name
    rid = (retailer.id if retailer else retailer_id) or ""
    return RETAILERS.get(rid, retailer.name if retailer else rid or "—")


def money(value) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def humanize(value) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if abs(float(value) - round(float(value), 2)) < 1e-9 and float(value) >= 1:
            # prices and costs
            if float(value) >= 10:
                return money(value)
        return str(value)
    text = str(value)
    return ENUM_LABELS.get(text, text.replace("_", " "))


def format_fact(data: dict | None) -> str:
    """Turn a check expected/observed blob into a short reviewer phrase."""
    if not data:
        return "—"
    if data.get("final_value") not in (None, ""):
        label = data["final_value"] if isinstance(data["final_value"], str) else humanize(data["final_value"])
        if data.get("conflicted"):
            return f"{label} (changed on the call)"
        return str(label)
    unit = str(data.get("unit") or "")
    if "value" in data and data["value"] not in (None, ""):
        if unit.upper() in {"AUD", "AUD/MONTH", "$"}:
            return money(data["value"])
        if unit:
            return f"{humanize(data['value'])} {unit}"
        return humanize(data["value"])
    if data.get("best_match"):
        return clip(str(data["best_match"]))
    if data.get("script"):
        return clip(str(data["script"]))
    if data.get("missing_elements"):
        missing = data["missing_elements"]
        if isinstance(missing, list) and missing:
            return "Missing: " + ", ".join(str(x) for x in missing)
    skip = {"unit", "extraction_confidence", "pass_ratio", "required_elements",
            "match_ratio", "assertions", "conflicted"}
    parts = [f"{k.replace('_', ' ')}: {humanize(v)}" for k, v in data.items()
             if k not in skip and v not in (None, "", [], {})]
    return " · ".join(parts) if parts else "—"


def expected_caption(check_type: str) -> str:
    if check_type == "VERBATIM":
        return "Required script"
    if check_type == "BEHAVIOUR":
        return "Policy"
    return "CRM / rate card"


def observed_caption(check_type: str) -> str:
    if check_type == "VERBATIM":
        return "Closest line on the call"
    if check_type == "BEHAVIOUR":
        return "What happened on the call"
    return "Said on the call"


def clip(text: str, limit: int = 180) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def issue_line(result: CheckResult) -> str:
    expected = format_fact(result.expected)
    observed = format_fact(result.observed)
    changed = " (changed on the call)"
    if observed.endswith(changed) and expected == observed[: -len(changed)]:
        return f"{result.check_name}: changed on the call; final {expected}"
    if expected not in {"—", ""} and observed not in {"—", ""} and expected != observed:
        return f"{result.check_name}: said {observed}, expected {expected}"
    if result.reason:
        return f"{result.check_name}: {clip(result.reason.split('.')[0], 140)}"
    return result.check_name


def _cue(result: CheckResult) -> dict:
    evidence = result.evidence or []
    first = next((e for e in evidence if isinstance(e, dict) and (e.get("start_ms") is not None or e.get("text"))), None)
    first = first or (evidence[0] if evidence and isinstance(evidence[0], dict) else {})
    return {
        "timestamp": first.get("timestamp"),
        "start_ms": first.get("start_ms"),
        "speaker": first.get("speaker"),
        "text": first.get("text"),
    }


def open_issue(result: CheckResult) -> dict:
    view = result_view(result)
    return {
        "result_id": result.id,
        "check_id": result.check_id,
        "check_name": result.check_name,
        "status": result.status,
        "critical": result.critical,
        "reason": result.reason,
        **view,
        **_cue(result),
    }


CRM_ROWS = [
    ("customer_full_name", "Customer"),
    ("email", "Email"),
    ("phone", "Phone"),
    ("dob", "Date of birth"),
    ("service_address", "Service address"),
    ("delivery_address", "Delivery address"),
    ("current_provider", "Current provider"),
    ("account_number", "Account number"),
    ("reference_number", "Reference"),
]

EVENT_LABELS = {
    "call_ingested": "Call landed in CRM",
    "scoring_run_completed": "Sale scored",
    "check_result_overridden": "Check overridden",
}


def crm_rows(crm: dict | None) -> list[dict]:
    crm = crm or {}
    rows = []
    for key, label in CRM_ROWS:
        value = crm.get(key)
        if value in (None, ""):
            continue
        rows.append({"label": label, "value": humanize(value) if not isinstance(value, str) else value})
    return rows


def plan_rows(plan: Plan | None) -> list[dict]:
    snap = plan_snapshot(plan)
    if not snap:
        return []
    labels = [
        ("name", "Plan"),
        ("intro_price", "Intro price"),
        ("intro_term_months", "Intro term"),
        ("regular_price", "Then pays"),
        ("download_mbps", "Download"),
        ("upload_mbps", "Upload"),
        ("contract_term", "Contract"),
        ("modem_model", "Modem"),
        ("modem_upfront_cost", "Modem upfront"),
        ("delivery", "Delivery"),
        ("total_minimum_cost", "Total minimum cost"),
        ("development_fee", "Development fee"),
    ]
    rows = []
    for key, label in labels:
        value = snap.get(key)
        if value in (None, "", "—"):
            continue
        if key == "intro_term_months":
            value = f"{value} months"
        rows.append({"label": label, "value": str(value)})
    return rows


def open_results(results: list[CheckResult]) -> list[CheckResult]:
    return [r for r in results
            if r.status in {CheckStatus.FAIL, CheckStatus.REVIEW, CheckStatus.ERROR}]


def lead_card(lead: Lead, retailer: Retailer | None, plan: Plan | None,
              run: ScoringRun | None, results: list[CheckResult] | None = None) -> dict:
    crm = lead.crm_fields or {}
    results = results or []
    opened = open_results(results)
    critical_open = [r for r in opened if r.critical]
    decision = run.gate_decision if run else None
    return {
        "lead_id": lead.id,
        "customer_name": crm.get("customer_full_name") or crm.get("customer_name") or "Customer",
        "customer_first_name": crm.get("customer_name") or "Customer",
        "agent_id": lead.agent_id,
        "agent_name": agent_name(lead.agent_id),
        "tl_id": lead.tl_id,
        "tl_name": tl_name(lead.tl_id),
        "retailer_id": lead.retailer_id,
        "retailer_name": retailer_name(retailer, lead.retailer_id),
        "plan_id": lead.plan_id,
        "plan_name": plan.name if plan else "—",
        "campaign": lead.campaign,
        "campaign_label": campaign_label(lead.campaign),
        "site": lead.site,
        "site_label": site_label(lead.site),
        "email": crm.get("email"),
        "phone": crm.get("phone"),
        "service_address": crm.get("service_address"),
        "current_provider": crm.get("current_provider"),
        "gate_decision": decision,
        "gate_headline": GATE_HEADLINE.get(decision, "Not scored yet") if decision else "Not scored yet",
        "gate_next_step": GATE_NEXT.get(decision, "Score this call before it ships.") if decision else "Score this call before it ships.",
        "gate_reason": run.gate_reason if run else None,
        "criticals_failed": run.criticals_failed if run else None,
        "scored_at": run.created_at if run else None,
        "issue": issue_line(critical_open[0]) if critical_open else (
            "All critical checks passed" if decision == GateDecision.AUTO_APPROVED else (
                issue_line(opened[0]) if opened else None
            )
        ),
        "open_count": len(critical_open),
        "open_issues": [open_issue(r) for r in (critical_open or opened)],
        "crm": crm_rows(crm),
        "plan": plan_snapshot(plan),
        "plan_rows": plan_rows(plan),
        "purpose": (
            f"A {retailer_name(retailer, lead.retailer_id)} "
            f"{plan.name if plan else 'broadband'} sale for "
            f"{crm.get('customer_full_name') or crm.get('customer_name') or 'the customer'}. "
            "The gate decides whether it can auto-submit after the call."
        ),
    }


def plan_snapshot(plan: Plan | None) -> dict | None:
    if not plan:
        return None
    return {
        "name": plan.name,
        "intro_price": money(plan.intro_price) if plan.intro_price is not None else None,
        "intro_term_months": plan.intro_term_months,
        "regular_price": money(plan.regular_price) if plan.regular_price is not None else None,
        "download_mbps": f"{float(plan.download_mbps):g} Mbps" if plan.download_mbps is not None else None,
        "upload_mbps": f"{float(plan.upload_mbps):g} Mbps" if plan.upload_mbps is not None else None,
        "contract_term": humanize(plan.contract_term),
        "modem_model": plan.modem_model,
        "modem_upfront_cost": money(plan.modem_upfront_cost) if plan.modem_upfront_cost is not None else None,
        "delivery": (
            f"{plan.delivery_days_min}–{plan.delivery_days_max} business days"
            if plan.delivery_days_min is not None else None
        ),
        "total_minimum_cost": money(plan.total_minimum_cost) if plan.total_minimum_cost is not None else None,
        "development_fee": money(plan.development_fee) if plan.development_fee is not None else None,
    }


def result_view(result: CheckResult) -> dict:
    return {
        "expected_label": format_fact(result.expected),
        "observed_label": format_fact(result.observed),
        "expected_caption": expected_caption(result.type),
        "observed_caption": observed_caption(result.type),
        "status_label": STATUS_LABEL.get(result.status, result.status),
        "type_label": TYPE_LABEL.get(result.type, result.type),
        "issue": issue_line(result),
    }
