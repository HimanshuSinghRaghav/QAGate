"""Type A - transcript vs approved script.

Matching runs on the squashed form (letters and digits only) because the source
contains glued words like "quality assuranceand, training purposes". Exact string
equality would fail a compliant call; squashed fuzzy matching does not.

Three bands:
  ratio >= pass_ratio      -> PASS deterministically
  ratio <  review_ratio    -> FAIL (the script item genuinely is not there)
  in between               -> the only place a model is asked for an opinion
"""
from difflib import SequenceMatcher

from app.core.enums import CheckStatus, Speaker
from app.services.checks.base import CheckContext, CheckOutcome, evidence_from_segment, handler
from app.services.extraction.normalizer import squash
from app.services.llm import prompts
from app.services.llm.client import complete_json

MAX_WINDOW = 4


def _best_window(ctx: CheckContext, expected: str) -> tuple[float, list]:
    target = squash(expected)
    best_ratio, best_window = 0.0, []
    segments = ctx.segments

    for start in range(len(segments)):
        # Prefer agent speech, but never exclude a segment purely on a low-confidence
        # speaker label - that is exactly where the diarization is unreliable.
        if segments[start].speaker == Speaker.CUSTOMER and \
                float(segments[start].speaker_confidence) >= 0.75:
            continue
        for size in range(1, MAX_WINDOW + 1):
            window = segments[start:start + size]
            if not window:
                break
            candidate = squash(" ".join(s.raw_text for s in window))
            if not candidate:
                continue
            ratio = SequenceMatcher(None, target, candidate).ratio()
            # Reward containment: the script line may sit inside a longer turn.
            if target in candidate:
                ratio = max(ratio, 0.97)
            if ratio > best_ratio:
                best_ratio, best_window = ratio, window
    return best_ratio, best_window


def _missing_elements(ctx: CheckContext, elements: list[str], window: list) -> list[str]:
    haystack = squash(" ".join(s.raw_text for s in ctx.segments))
    missing = []
    for element in elements:
        needle = squash(element)
        if needle and needle not in haystack:
            if SequenceMatcher(None, needle, haystack).find_longest_match().size < len(needle) * 0.85:
                missing.append(element)
    return missing


@handler("script_match")
def script_match(ctx: CheckContext) -> CheckOutcome:
    cfg = ctx.config
    expected = cfg.get("expected", "")
    if not expected:
        return CheckOutcome.not_applicable("Check definition carries no expected script text.")

    pass_ratio = float(cfg.get("pass_ratio", 0.82))
    review_ratio = float(cfg.get("review_ratio", 0.60))
    elements = cfg.get("required_elements", [])

    ratio, window = _best_window(ctx, expected)
    evidence = [evidence_from_segment(s, note=f"fuzzy ratio {ratio:.2f}") for s in window]
    missing = _missing_elements(ctx, elements, window)
    expected_payload = {"script": expected, "required_elements": elements,
                        "pass_ratio": pass_ratio}
    observed_payload = {"best_match": " ".join(s.redacted_text for s in window),
                        "match_ratio": round(ratio, 3), "missing_elements": missing}

    if ratio >= pass_ratio and not missing:
        return CheckOutcome(
            status=CheckStatus.PASS,
            confidence=round(min(0.99, 0.75 + ratio * 0.24), 3),
            method="fuzzy",
            reason=f"Script item matched at {ratio:.0%} with all required elements present.",
            expected=expected_payload, observed=observed_payload, evidence=evidence,
        )

    if ratio < review_ratio and missing:
        return CheckOutcome(
            status=CheckStatus.FAIL,
            confidence=round(min(0.95, 0.70 + (review_ratio - ratio)), 3),
            method="fuzzy",
            reason=f"Script item not found (best match {ratio:.0%}); "
                   f"missing: {', '.join(missing) or 'whole item'}.",
            expected=expected_payload, observed=observed_payload, evidence=evidence,
        )

    # Borderline. Ask the model, and treat an unavailable model as uncertainty.
    verdict = complete_json(
        prompts.SCRIPT_EQUIVALENCE_SYSTEM,
        prompts.SCRIPT_EQUIVALENCE_USER.format(
            check_name=ctx.definition.name,
            expected=expected,
            required_elements=elements,
            candidates="\n".join(
                f"[{s.timestamp_label}] {s.redacted_text}" for s in window
            ) or "(no close candidate found)",
        ),
    )
    if not verdict:
        return CheckOutcome(
            status=CheckStatus.REVIEW, confidence=0.35, method="fuzzy",
            reason=f"Borderline script match ({ratio:.0%}) and no semantic adjudication "
                   f"available. Routed to QA rather than auto-passed.",
            expected=expected_payload, observed=observed_payload, evidence=evidence,
        )

    mapped = {"PASS": CheckStatus.PASS, "FAIL": CheckStatus.FAIL}.get(
        str(verdict.get("verdict", "")).upper(), CheckStatus.REVIEW)
    observed_payload["llm_missing_elements"] = verdict.get("missing_elements", [])
    return CheckOutcome(
        status=mapped,
        confidence=round(float(verdict.get("confidence", 0.5)), 3),
        method="llm",
        reason=str(verdict.get("reason", "Semantic adjudication of a borderline match.")),
        expected=expected_payload, observed=observed_payload, evidence=evidence,
    )
