"""Type B - transcript vs CRM fields vs the retailer's plan and rate card.

Every handler here is deterministic first. A model is consulted in exactly one
situation: the value was extracted but the extraction itself is uncertain (an ASR
mangling such as "Netcom p s forty"). Even then the model can only move the result
between PASS, FAIL and REVIEW - it never supplies the expected value.
"""
from decimal import Decimal

from app.core.enums import CheckStatus
from app.services.checks.base import CheckContext, CheckOutcome, evidence_from, handler
from app.services.extraction.state_tracker import ResolvedFact, resolve
from app.services.llm import prompts
from app.services.llm.client import complete_json


# --------------------------------------------------------------------------- utils

def _expected_value(ctx: CheckContext):
    cfg = ctx.config
    if "plan_field" in cfg:
        return getattr(ctx.plan, cfg["plan_field"], None) if ctx.plan else None
    if "crm_field" in cfg:
        return ctx.crm.get(cfg["crm_field"])
    if "literal" in cfg:
        return cfg["literal"]
    return None


def _as_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _trail(fact: ResolvedFact) -> list[dict]:
    return [dict(evidence_from(o), value=o.value, confidence=o.confidence) for o in fact.trail]


def _missing(ctx: CheckContext, fact: ResolvedFact, expected) -> CheckOutcome | None:
    """Guardrail: distinguish 'the agent got it wrong' from 'we could not hear it'."""
    if expected is None:
        return CheckOutcome.not_applicable(
            f"No expected value configured for '{ctx.definition.check_id}' "
            f"(plan or CRM field is empty)."
        )
    if not fact.found:
        return CheckOutcome(
            status=CheckStatus.REVIEW, confidence=0.30, method="deterministic",
            reason=f"No statement of this value was found in the transcript. "
                   f"Not scored as a failure - absence of evidence is routed to a human.",
            expected={"value": _jsonable(expected)}, observed=None, evidence=[],
        )
    return None


def _jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def _loose_equal(observed, expected) -> bool:
    """Ignore wrapping punctuation so 'helen.carter@gmail.com.' still matches."""
    def norm(value) -> str:
        return str(value).strip().strip(".,;:").strip().lower()
    return norm(observed) == norm(expected)


def _adjudicate(ctx: CheckContext, fact: ResolvedFact, expected) -> CheckOutcome:
    """Low-confidence extraction -> ask for semantic equivalence, else REVIEW."""
    candidates = "\n".join(f"[{o.timestamp}] {o.text}" for o in fact.trail[-3:])
    verdict = complete_json(
        prompts.AMBIGUITY_SYSTEM,
        prompts.AMBIGUITY_USER.format(
            check_name=ctx.definition.name,
            expected=_jsonable(expected),
            observed=fact.value,
            candidates=candidates,
        ),
    )
    evidence = [evidence_from(fact.winner)] if fact.winner else []
    base = dict(expected={"value": _jsonable(expected)},
                observed={"value": fact.value, "extraction_confidence": fact.confidence},
                evidence=evidence, observation_trail=_trail(fact))
    if not verdict:
        return CheckOutcome(
            status=CheckStatus.REVIEW, confidence=round(fact.confidence, 3), method="hybrid",
            reason=f"Value extracted with low confidence ({fact.confidence:.0%}) "
                   f"and no semantic adjudication available. {fact.reason}",
            **base)
    mapped = {"PASS": CheckStatus.PASS, "FAIL": CheckStatus.FAIL}.get(
        str(verdict.get("verdict", "")).upper(), CheckStatus.REVIEW)
    return CheckOutcome(
        status=mapped,
        confidence=round(min(float(verdict.get("confidence", 0.5)), 0.90), 3),
        method="hybrid",
        reason=str(verdict.get("reason", "Semantic adjudication of an uncertain extraction.")),
        **base)


def _decide_numeric(ctx: CheckContext, fact: ResolvedFact, expected, tolerance: float,
                    unit: str | None) -> CheckOutcome:
    observed = _as_float(fact.value)
    expected_f = _as_float(expected)
    evidence = [evidence_from(fact.winner)] if fact.winner else []
    payload = dict(
        expected={"value": expected_f, "unit": unit},
        observed={"value": observed, "unit": unit, "extraction_confidence": fact.confidence},
        evidence=evidence, observation_trail=_trail(fact),
    )

    if observed is None:
        return _adjudicate(ctx, fact, expected)

    matches = abs(observed - expected_f) <= tolerance
    if not matches and fact.confidence < 0.6:
        return _adjudicate(ctx, fact, expected)

    status = CheckStatus.PASS if matches else CheckStatus.FAIL
    if fact.conflicted:
        status = CheckStatus.REVIEW if matches else status
    confidence = round(min(0.99, fact.confidence), 3)
    reason = (
        f"Quoted {observed}{' ' + unit if unit else ''}, plan says "
        f"{expected_f}{' ' + unit if unit else ''}. {fact.reason}"
    )
    return CheckOutcome(status=status, confidence=confidence, method="deterministic",
                        reason=reason, **payload)


# ------------------------------------------------------------------------ handlers

@handler("money_match")
def money_match(ctx: CheckContext) -> CheckOutcome:
    expected = _expected_value(ctx)
    fact = resolve(ctx.facts, ctx.config["fact"])
    if (early := _missing(ctx, fact, expected)) is not None:
        return early
    return _decide_numeric(ctx, fact, expected, float(ctx.config.get("tolerance", 0.0)), "AUD")


@handler("numeric_match")
def numeric_match(ctx: CheckContext) -> CheckOutcome:
    expected = _expected_value(ctx)
    fact = resolve(ctx.facts, ctx.config["fact"])
    if (early := _missing(ctx, fact, expected)) is not None:
        return early
    return _decide_numeric(ctx, fact, expected, float(ctx.config.get("tolerance", 0.0)),
                           ctx.config.get("unit"))


@handler("enum_match")
def enum_match(ctx: CheckContext) -> CheckOutcome:
    expected = _expected_value(ctx)
    fact = resolve(ctx.facts, ctx.config["fact"])
    if (early := _missing(ctx, fact, expected)) is not None:
        return early

    observed = str(fact.value)
    accepted = {str(expected).lower(), *[str(a).lower() for a in ctx.config.get("also_accept", [])]}
    if observed.lower() in accepted:
        return CheckOutcome(
            status=CheckStatus.PASS, confidence=round(fact.confidence, 3),
            method="deterministic",
            reason=f"Stated as '{observed}', which matches the plan. {fact.reason}",
            expected={"value": _jsonable(expected)},
            observed={"value": observed, "extraction_confidence": fact.confidence},
            evidence=[evidence_from(fact.winner)], observation_trail=_trail(fact))
    return _adjudicate(ctx, fact, expected)


@handler("range_match")
def range_match(ctx: CheckContext) -> CheckOutcome:
    lo = getattr(ctx.plan, ctx.config["plan_field_min"], None) if ctx.plan else None
    hi = getattr(ctx.plan, ctx.config["plan_field_max"], None) if ctx.plan else None
    fact = resolve(ctx.facts, ctx.config["fact"])
    expected = [lo, hi] if lo is not None else None
    if (early := _missing(ctx, fact, expected)) is not None:
        return early

    observed = fact.value if isinstance(fact.value, list) else [fact.value, fact.value]
    matches = int(observed[0]) == int(lo) and int(observed[-1]) == int(hi)
    return CheckOutcome(
        status=CheckStatus.PASS if matches else CheckStatus.FAIL,
        confidence=round(fact.confidence, 3), method="deterministic",
        reason=f"Quoted {observed[0]}-{observed[-1]} days; plan states {lo}-{hi}. {fact.reason}",
        expected={"min": lo, "max": hi},
        observed={"min": observed[0], "max": observed[-1]},
        evidence=[evidence_from(fact.winner)], observation_trail=_trail(fact))


@handler("crm_match")
def crm_match(ctx: CheckContext) -> CheckOutcome:
    """Transcript read-back vs the CRM field.

    On sanitised data both sides are placeholder tags, so this compares tags. On real
    traffic the comparison is identical - only the values change - which is how the
    brief's 'j.smith@gmail.com vs j.smith@gmial.com' case is caught.
    """
    expected = ctx.crm.get(ctx.config["crm_field"])
    fact = resolve(ctx.facts, ctx.config["fact"])
    if (early := _missing(ctx, fact, expected)) is not None:
        return early

    observed = str(fact.value)
    matches = _loose_equal(observed, expected)
    verified_in_exchange = any("verification exchange" in (o.note or "") for o in fact.trail)
    confidence = round(min(0.99, fact.confidence + (0.05 if verified_in_exchange else -0.10)), 3)

    if not matches:
        return CheckOutcome(
            status=CheckStatus.FAIL, confidence=confidence, method="deterministic",
            reason=f"Read back on the call as '{observed}' but CRM holds '{expected}'.",
            expected={"value": expected}, observed={"value": observed},
            evidence=[evidence_from(fact.winner)], observation_trail=_trail(fact))

    if not verified_in_exchange and ctx.config.get("require_verification", True):
        return CheckOutcome(
            status=CheckStatus.REVIEW, confidence=round(min(confidence, 0.6), 3),
            method="deterministic",
            reason="Value matches CRM but was not clearly read back in a verification "
                   "exchange; routed to QA rather than auto-passed.",
            expected={"value": expected}, observed={"value": observed},
            evidence=[evidence_from(fact.winner)], observation_trail=_trail(fact))

    return CheckOutcome(
        status=CheckStatus.PASS, confidence=confidence, method="deterministic",
        reason=f"Verified on call and matches CRM. {fact.reason}",
        expected={"value": expected}, observed={"value": observed},
        evidence=[evidence_from(fact.winner)], observation_trail=_trail(fact))


@handler("stateful_match")
def stateful_match(ctx: CheckContext) -> CheckOutcome:
    """A value that changed during the call. Latest assertion wins; conflict is surfaced.

    This is the delivery-address case: 'same address' early, a different address later.
    First-occurrence matching would return a confident PASS on a wrong address.
    """
    expected = ctx.crm.get(ctx.config["crm_field"])
    fact = resolve(ctx.facts, ctx.config["fact"])
    if (early := _missing(ctx, fact, expected)) is not None:
        return early

    observed = str(fact.value)
    matches = _loose_equal(observed, expected)
    payload = dict(
        expected={"value": expected},
        observed={"final_value": observed, "conflicted": fact.conflicted,
                  "assertions": len(fact.trail)},
        evidence=[evidence_from(o) for o in fact.trail[-3:]],
        observation_trail=_trail(fact),
    )

    if fact.conflicted:
        status = CheckStatus.REVIEW if matches else CheckStatus.FAIL
        return CheckOutcome(
            status=status, confidence=round(fact.confidence, 3), method="deterministic",
            reason=f"Value changed during the call. {fact.reason} "
                   f"Final asserted value {'matches' if matches else 'does not match'} CRM "
                   f"('{expected}').",
            **payload)

    return CheckOutcome(
        status=CheckStatus.PASS if matches else CheckStatus.FAIL,
        confidence=round(fact.confidence, 3), method="deterministic",
        reason=f"Single consistent value '{observed}'; CRM holds '{expected}'.",
        **payload)


@handler("fact_present")
def fact_present(ctx: CheckContext) -> CheckOutcome:
    fact = resolve(ctx.facts, ctx.config["fact"])
    if not fact.found:
        return CheckOutcome(
            status=CheckStatus.FAIL if ctx.config.get("fail_if_absent", True)
            else CheckStatus.REVIEW,
            confidence=0.70, method="deterministic",
            reason=ctx.config.get("absent_reason", "Required step not evidenced in transcript."),
            expected={"present": True}, observed={"present": False}, evidence=[])
    return CheckOutcome(
        status=CheckStatus.PASS, confidence=round(fact.confidence, 3),
        method="deterministic",
        reason=ctx.config.get("present_reason", "Step evidenced in transcript."),
        expected={"present": True}, observed={"present": True, "value": fact.value},
        evidence=[evidence_from(fact.winner)], observation_trail=_trail(fact))


@handler("fee_applicability")
def fee_applicability(ctx: CheckContext) -> CheckOutcome:
    """The development-fee case: a fee is displayed, the agent says it will not apply.

    PASS requires the plan/CRM to agree that the fee is not applicable AND the agent to
    have explained why. If the record says the fee DOES apply, the agent's reassurance
    is a misrepresentation and the sale is held.
    """
    fee_applicable = bool(ctx.crm.get(ctx.config.get("crm_field", "development_fee_applicable")))
    claim = resolve(ctx.facts, "development_fee_waived_claim")
    fee_mention = resolve(ctx.facts, "development_fee")

    evidence = [evidence_from(o) for o in (claim.trail[:1] + fee_mention.trail[:1]) if o]
    expected = {"development_fee_applicable": fee_applicable,
                "development_fee": _jsonable(getattr(ctx.plan, "development_fee", None))}

    if not claim.found and not fee_mention.found:
        return CheckOutcome.not_applicable("Development fee was never raised on the call.")

    if claim.found and fee_applicable:
        return CheckOutcome(
            status=CheckStatus.FAIL, confidence=0.90, method="deterministic",
            reason="Agent told the customer the development fee would not be charged, but "
                   "the record marks it as applicable to this address.",
            expected=expected, observed={"agent_claimed_waived": True}, evidence=evidence)

    if claim.found and not fee_applicable:
        return CheckOutcome(
            status=CheckStatus.PASS, confidence=round(min(0.92, claim.confidence), 3),
            method="deterministic",
            reason="Agent explained the development fee is not applicable, consistent with "
                   "the address record.",
            expected=expected, observed={"agent_claimed_waived": True}, evidence=evidence)

    return CheckOutcome(
        status=CheckStatus.REVIEW, confidence=0.45, method="deterministic",
        reason="Development fee appeared on the call but no clear explanation of its "
               "applicability was found.",
        expected=expected, observed={"agent_claimed_waived": False}, evidence=evidence)
