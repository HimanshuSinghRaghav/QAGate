"""The gate. One function, no side effects, fully explainable.

Order matters and is deliberate:
  1. any critical FAIL            -> HELD          (a known problem outranks doubt)
  2. any critical REVIEW          -> QA_REVIEW
  3. any critical below threshold -> QA_REVIEW     (nothing uncertain auto-passes)
  4. otherwise                    -> AUTO_APPROVED, of which a sample goes to a human

NOT_APPLICABLE on a critical check is treated as uncertainty, not as a pass. A check
that could not be evaluated is precisely the case that must reach a person.
"""
import hashlib
from dataclasses import dataclass

from app.core.config import settings
from app.core.enums import CheckStatus, GateDecision
from app.models import CheckResult


@dataclass
class GateOutcome:
    decision: GateDecision
    reason: str
    criticals_failed: int
    lowest_confidence: float
    sampled_for_human: bool
    score_with_fatals: float
    score_without_fatals: float


def _is_sampled(lead_id: str) -> bool:
    if settings.human_sample_rate <= 0:
        return False
    if settings.deterministic_sampling:
        digest = hashlib.sha256(lead_id.encode()).hexdigest()
        bucket = int(digest[:8], 16) / 0xFFFFFFFF
        return bucket < settings.human_sample_rate
    import random
    return random.random() < settings.human_sample_rate


def _weighted_score(results: list[CheckResult], include_criticals: bool) -> float:
    pool = [r for r in results
            if r.status != CheckStatus.NOT_APPLICABLE
            and (include_criticals or not r.critical)]
    total = sum(float(r.weight) for r in pool)
    if total == 0:
        return 0.0
    earned = sum(float(r.weight) for r in pool if r.status == CheckStatus.PASS)
    return round((earned / total) * 100, 2)


def decide(lead_id: str, results: list[CheckResult]) -> GateOutcome:
    threshold = settings.confidence_threshold
    criticals = [r for r in results if r.critical]

    failed = [r for r in criticals if r.status == CheckStatus.FAIL]
    review = [r for r in criticals if r.status in (CheckStatus.REVIEW, CheckStatus.ERROR)]
    unscorable = [r for r in criticals if r.status == CheckStatus.NOT_APPLICABLE]
    low_conf = [r for r in criticals
                if r.status == CheckStatus.PASS and float(r.confidence) < threshold]

    scored = [r for r in results if r.status != CheckStatus.NOT_APPLICABLE]
    lowest = round(min((float(r.confidence) for r in scored), default=1.0), 3)

    with_fatals = _weighted_score(results, include_criticals=True)
    without_fatals = _weighted_score(results, include_criticals=False)

    def build(decision: GateDecision, reason: str, sampled: bool = False) -> GateOutcome:
        return GateOutcome(decision, reason, len(failed), lowest, sampled,
                           with_fatals, without_fatals)

    if failed:
        names = ", ".join(f"{r.check_name} ({r.check_id})" for r in failed[:3])
        more = f" and {len(failed) - 3} more" if len(failed) > 3 else ""
        return build(GateDecision.HELD,
                     f"{len(failed)} critical check(s) failed: {names}{more}. "
                     f"Routed to the TL queue.")

    if review:
        names = ", ".join(r.check_name for r in review[:3])
        return build(GateDecision.QA_REVIEW,
                     f"{len(review)} critical check(s) could not be decided automatically "
                     f"({names}). Routed to QA rather than auto-passed.")

    if low_conf:
        worst = min(low_conf, key=lambda r: float(r.confidence))
        return build(GateDecision.QA_REVIEW,
                     f"Critical check '{worst.check_name}' passed at "
                     f"{float(worst.confidence):.0%} confidence, below the "
                     f"{threshold:.0%} threshold. Routed to QA.")

    if unscorable:
        names = ", ".join(r.check_name for r in unscorable[:3])
        return build(GateDecision.QA_REVIEW,
                     f"{len(unscorable)} critical check(s) were not scorable from the "
                     f"available inputs ({names}). Routed to QA.")

    if _is_sampled(lead_id):
        return build(GateDecision.HUMAN_SAMPLE,
                     "All critical checks passed. Selected in the "
                     f"{settings.human_sample_rate:.0%} calibration sample, so a human "
                     "reviews it as well.", sampled=True)

    return build(GateDecision.AUTO_APPROVED,
                 "All critical checks passed above the confidence threshold. "
                 "Sale auto-submits with no human touch.")
