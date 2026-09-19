"""Run the whole pipeline in memory - no Postgres, no network, no LLM.

    python scripts/dry_run.py            # the real supplied call
    python scripts/dry_run.py --lead 3613792

Useful during the build because it exercises parsing, redaction, extraction, state
tracking, every check handler and the gate in about a second. The LLM is disabled
here on purpose, so what you see is the deterministic floor of the system.
"""
import argparse
import os
import sys

os.environ.setdefault("LLM_ENABLED", "false")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.enums import CheckStatus, TimingSource  # noqa: E402
from app.models import (  # noqa: E402
    Call, CheckDefinition, CheckResult, Lead, Plan, Segment, Transcript,
)
from app.seed.data.audio import recording_for  # noqa: E402
from app.seed.data.checks import CHECKS  # noqa: E402
from app.seed.data.leads import LEADS, PLAN  # noqa: E402
from app.services.checks.base import CheckContext  # noqa: E402
from app.services.checks.registry import get_handler  # noqa: E402
from app.services.extraction import facts as facts_module  # noqa: E402
from app.services.gate.gate import decide  # noqa: E402
from app.services.transcript import parser, timing  # noqa: E402
from app.services.transcript.redaction import redact  # noqa: E402
from app.services.scoring.version_resolver import CheckDefinition as _CD  # noqa: E402,F401

ICON = {CheckStatus.PASS: "PASS", CheckStatus.FAIL: "FAIL", CheckStatus.REVIEW: "RVW",
        CheckStatus.NOT_APPLICABLE: " -- ", CheckStatus.ERROR: "ERR"}


def build_segments(raw: str, recording=None) -> tuple[list[Segment], bool, str]:
    parsed, reliable = parser.parse(raw)
    texts = [p.text for p in parsed]
    if recording:
        spans = timing.apply_asr_timings(recording.tokens, texts)
        source = TimingSource.ASR
    else:
        spans = timing.estimate_timings(texts)
        source = TimingSource.ESTIMATED
    segments = []
    for i, (p, (start, end)) in enumerate(zip(parsed, spans, strict=True)):
        report = redact(p.text)
        segments.append(Segment(
            id=f"seg_{i:04d}", transcript_id="tr_dry", index=i, turn_index=p.turn_index,
            speaker=p.speaker, speaker_confidence=p.speaker_confidence,
            raw_text=p.text, redacted_text=report.text,
            start_ms=start, end_ms=end, timing_source=source,
            redactions=report.findings,
        ))
    return segments, reliable, source


def resolve_versions(call_date):
    live = [c for c in CHECKS
            if c["effective_from"] <= call_date
            and (c["effective_to"] is None or c["effective_to"] > call_date)]
    best: dict[str, dict] = {}
    for c in live:
        if c["check_id"] not in best or c["version"] > best[c["check_id"]]["version"]:
            best[c["check_id"]] = c
    return list(best.values())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lead", default="3613790")
    ap.add_argument("--facts", action="store_true", help="dump the extracted fact store")
    args = ap.parse_args()

    spec = next((s for s in LEADS if s["id"] == args.lead), None)
    if not spec:
        sys.exit(f"Unknown lead {args.lead}. Try: {[s['id'] for s in LEADS]}")

    recording = recording_for(spec["id"])
    segments, reliable, source = build_segments(spec["transcript"], recording)
    store = facts_module.extract(segments, crm=spec["crm_fields"])

    lead = Lead(id=spec["id"], retailer_id=spec["retailer_id"], plan_id=spec["plan_id"],
                agent_id=spec["agent_id"], crm_fields=spec["crm_fields"])
    plan = Plan(**PLAN)
    transcript = Transcript(id="tr_dry", lead_id=lead.id, call_id="call_dry",
                            timing_source=source,
                            diarization_reliable=reliable)
    call_date = spec["call"]["started_at"]

    audio = (f" | audio {recording.duration_seconds // 60}:"
             f"{recording.duration_seconds % 60:02d}" if recording else "")
    print(f"\nLead {lead.id} | call {call_date:%Y-%m-%d %H:%M} | agent {lead.agent_id}")
    print(f"{len(segments)} segments | diarization_reliable={reliable} "
          f"| timing_source={source}{audio}\n")

    if args.facts:
        for key in store.keys():
            values = [(o.value, round(o.confidence, 2), o.timestamp) for o in store.get(key)]
            print(f"  {key:32} {values}")
        print()

    results = []
    for definition in sorted(resolve_versions(call_date), key=lambda d: (d["type"], d["check_id"])):
        cd = CheckDefinition(**definition)
        fn = get_handler(cd.config.get("handler"))
        outcome = fn(CheckContext(lead, plan, transcript, segments, store, cd))
        results.append(CheckResult(
            id=f"res_{cd.check_id}", run_id="run_dry", lead_id=lead.id,
            check_id=cd.check_id, check_version=cd.version, check_name=cd.name,
            type=cd.type, critical=cd.critical, weight=cd.weight,
            status=outcome.status, confidence=outcome.confidence, method=outcome.method,
            reason=outcome.reason, expected=outcome.expected, observed=outcome.observed,
            evidence=outcome.evidence, observation_trail=outcome.observation_trail,
        ))

    for scope, critical in (("CRITICAL", True), ("NON-CRITICAL", False)):
        print(f"--- {scope} " + "-" * (58 - len(scope)))
        for r in [x for x in results if x.critical is critical]:
            ts = r.evidence[0]["timestamp"] if r.evidence else "  -  "
            conf = f"{float(r.confidence):.0%}".rjust(5)
            print(f" [{ICON[r.status]}] {r.check_name[:38]:38} v{r.check_version} "
                  f"{conf} {ts}")
            print(f"        {r.reason}")
        print()

    gate = decide(lead.id, results)
    print("=" * 66)
    print(f" GATE: {gate.decision}")
    print(f" {gate.reason}")
    print(f" score with fatals {gate.score_with_fatals}% | without "
          f"{gate.score_without_fatals}% | lowest confidence "
          f"{gate.lowest_confidence:.0%}")
    print("=" * 66 + "\n")


if __name__ == "__main__":
    main()
