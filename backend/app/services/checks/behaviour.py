"""Type C - behaviour and compliance read from the transcript alone.

Two rules govern this file:
  * behaviour findings are non-critical and must never hold a sale on their own
  * a check whose input is missing returns NOT_APPLICABLE, not FAIL

The second rule is the whole of the 'guardrails and judgment' criterion. Dead air
and interruptions genuinely cannot be measured from estimated timings and broken
diarization, so this system says so instead of inventing a finding.
"""
from app.core.enums import CheckStatus, Speaker, TimingSource
from app.services.checks.base import (
    CheckContext, CheckOutcome, evidence_from, evidence_from_segment, handler,
)
from app.services.extraction.state_tracker import resolve
from app.services.llm import prompts
from app.services.llm.client import complete_json


@handler("no_card_data")
def no_card_data(ctx: CheckContext) -> CheckOutcome:
    """Compliance: a spoken card number is a violation, and the number is never shown.

    The finding comes from the redaction report, so the check can flag the violation
    without any handler, API response or UI ever touching the digits.
    """
    offenders = [
        s for s in ctx.segments
        if any(f.get("kind") == "card_number" for f in (s.redactions or []))
    ]
    if offenders:
        return CheckOutcome(
            status=CheckStatus.FAIL, confidence=0.99, method="deterministic",
            reason=f"Card data was spoken on the call in {len(offenders)} place(s). "
                   f"The transcript is redacted; the number is not surfaced anywhere.",
            expected={"card_data_present": False},
            observed={"card_data_present": True, "occurrences": len(offenders)},
            evidence=[evidence_from_segment(s, note="redacted before storage")
                      for s in offenders[:3]])
    return CheckOutcome(
        status=CheckStatus.PASS, confidence=0.97, method="deterministic",
        reason="No card data present in the transcript.",
        expected={"card_data_present": False}, observed={"card_data_present": False},
        evidence=[])


@handler("mute_before_payment")
def mute_before_payment(ctx: CheckContext) -> CheckOutcome:
    """The recording must be muted before card details are collected."""
    muted = resolve(ctx.facts, "recording_muted")
    resumed = resolve(ctx.facts, "recording_resumed")
    collection = resolve(ctx.facts, "payment_collection_started")

    if not collection.found:
        return CheckOutcome.not_applicable("No payment collection took place on this call.")

    if not muted.found:
        return CheckOutcome(
            status=CheckStatus.FAIL, confidence=0.85, method="deterministic",
            reason="Payment details were collected but no recording mute was evidenced.",
            expected={"mute_before_collection": True},
            observed={"muted": False, "collection_started": True},
            evidence=[evidence_from(collection.winner)])

    card_spoken_after_mute = any(
        s.index > muted.winner.segment_index
        and any(f.get("kind") == "card_number" for f in (s.redactions or []))
        for s in ctx.segments
    )
    status = CheckStatus.FAIL if card_spoken_after_mute else CheckStatus.PASS
    return CheckOutcome(
        status=status, confidence=0.93, method="deterministic",
        reason=("Recording was muted before payment collection"
                + (" but card data still appears in the transcript."
                   if card_spoken_after_mute
                   else f" and resumed afterwards." if resumed.found else ".")),
        expected={"mute_before_collection": True},
        observed={"muted": True, "resumed": resumed.found,
                  "mute_at": muted.winner.timestamp},
        evidence=[evidence_from(muted.winner)]
        + ([evidence_from(resumed.winner)] if resumed.found else []))


@handler("dead_air")
def dead_air(ctx: CheckContext) -> CheckOutcome:
    """Requires real audio timings. Estimated timings cannot evidence silence."""
    if ctx.transcript.timing_source != TimingSource.ASR:
        return CheckOutcome.not_applicable(
            "Dead air cannot be measured from estimated timestamps. Enable ASR word-level "
            "timings and this check becomes deterministic. Reported as un-scorable rather "
            "than scored from an assumption."
        )
    threshold_ms = int(ctx.config.get("threshold_seconds", 30)) * 1000
    gaps = []
    for prev, nxt in zip(ctx.segments, ctx.segments[1:], strict=False):
        gap = nxt.start_ms - prev.end_ms
        if gap >= threshold_ms:
            gaps.append(evidence_from_segment(prev, note=f"{gap // 1000}s of silence follows"))
    return CheckOutcome(
        status=CheckStatus.FAIL if gaps else CheckStatus.PASS,
        confidence=0.95, method="deterministic",
        reason=f"{len(gaps)} silence(s) over {threshold_ms // 1000}s." if gaps
        else "No dead air over threshold.",
        expected={"max_silence_seconds": threshold_ms // 1000},
        observed={"occurrences": len(gaps)}, evidence=gaps[:3])


@handler("interruptions")
def interruptions(ctx: CheckContext) -> CheckOutcome:
    """Needs trustworthy speaker separation. The supplied transcript does not have it."""
    if not ctx.transcript.diarization_reliable:
        return CheckOutcome.not_applicable(
            "Speaker separation in this transcript is unreliable - customer replies are "
            "folded into agent turns - so interruption counting would manufacture "
            "findings. Requires diarized input."
        )
    switches = sum(
        1 for a, b in zip(ctx.segments, ctx.segments[1:], strict=False)
        if a.speaker != b.speaker and a.speaker != Speaker.UNKNOWN
    )
    limit = int(ctx.config.get("max_interruptions", 5))
    return CheckOutcome(
        status=CheckStatus.PASS if switches <= limit else CheckStatus.FAIL,
        confidence=0.75, method="deterministic",
        reason=f"{switches} speaker overlaps detected (limit {limit}).",
        expected={"max_interruptions": limit}, observed={"count": switches}, evidence=[])


@handler("llm_behaviour")
def llm_behaviour(ctx: CheckContext) -> CheckOutcome:
    """Rapport, objection handling - the only checks where judgement is the whole task."""
    transcript = "\n".join(
        f"{s.id} | {s.speaker} | {s.timestamp_label} | {s.redacted_text}"
        for s in ctx.segments
    )
    verdict = complete_json(
        prompts.BEHAVIOUR_SYSTEM,
        prompts.BEHAVIOUR_USER.format(
            check_name=ctx.definition.name,
            description=ctx.definition.description or "",
            transcript=transcript,
        ),
        max_tokens=600,
    )
    if not verdict:
        return CheckOutcome(
            status=CheckStatus.REVIEW, confidence=0.30, method="llm",
            reason="Behaviour model unavailable; coaching note routed to QA.",
            expected=None, observed=None, evidence=[])

    ids = verdict.get("evidence_segment_ids") or []
    evidence = [evidence_from_segment(seg) for sid in ids[:3]
                if (seg := ctx.segment_by_id(str(sid)))]
    mapped = {"PASS": CheckStatus.PASS, "FAIL": CheckStatus.FAIL}.get(
        str(verdict.get("verdict", "")).upper(), CheckStatus.REVIEW)
    return CheckOutcome(
        status=mapped,
        confidence=round(float(verdict.get("confidence", 0.5)), 3),
        method="llm",
        reason=str(verdict.get("reason", "")),
        expected={"criterion": ctx.definition.name},
        observed={"verdict": verdict.get("verdict")},
        evidence=evidence)
