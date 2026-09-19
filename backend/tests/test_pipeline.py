"""End-to-end over the real supplied transcript, without a database or a model."""
import os

os.environ["LLM_ENABLED"] = "false"

from app.core.enums import CheckStatus, TimingSource  # noqa: E402
from app.models import CheckDefinition, Lead, Plan, Segment, Transcript  # noqa: E402
from app.seed.data.checks import CHECKS  # noqa: E402
from app.seed.data.leads import LEADS, PLAN  # noqa: E402
from app.services.checks.base import CheckContext  # noqa: E402
from app.services.checks.registry import get_handler  # noqa: E402
from app.services.extraction import facts as facts_module  # noqa: E402
from app.services.transcript import parser, timing  # noqa: E402
from app.services.transcript.redaction import redact  # noqa: E402

SPEC = LEADS[0]


def _segments(raw):
    parsed, reliable = parser.parse(raw)
    spans = timing.estimate_timings([p.text for p in parsed])
    segs = []
    for i, (p, (a, b)) in enumerate(zip(parsed, spans, strict=True)):
        rep = redact(p.text)
        segs.append(Segment(id=f"seg_{i:04d}", transcript_id="tr", index=i,
                            turn_index=p.turn_index, speaker=p.speaker,
                            speaker_confidence=p.speaker_confidence, raw_text=p.text,
                            redacted_text=rep.text, start_ms=a, end_ms=b,
                            timing_source=TimingSource.ESTIMATED,
                            redactions=rep.findings))
    return segs, reliable


def _run(check_id, version=1):
    segs, reliable = _segments(SPEC["transcript"])
    store = facts_module.extract(segs, crm=SPEC["crm_fields"])
    definition = next(c for c in CHECKS
                      if c["check_id"] == check_id and c["version"] == version)
    cd = CheckDefinition(**definition)
    ctx = CheckContext(
        Lead(id=SPEC["id"], retailer_id=SPEC["retailer_id"], plan_id=SPEC["plan_id"],
             agent_id=SPEC["agent_id"], crm_fields=SPEC["crm_fields"]),
        Plan(**PLAN),
        Transcript(id="tr", lead_id=SPEC["id"], call_id="c",
                   timing_source=TimingSource.ESTIMATED, diarization_reliable=reliable),
        segs, store, cd)
    return get_handler(cd.config["handler"])(ctx)


def test_diarization_is_flagged_unreliable():
    _, reliable = _segments(SPEC["transcript"])
    assert reliable is False


def test_disclaimer_passes_despite_run_together_words():
    out = _run("recording_disclaimer", version=1)
    assert out.status == CheckStatus.PASS


def test_intro_price_matches_the_rate_card():
    out = _run("plan_intro_price")
    assert out.status == CheckStatus.PASS
    assert out.observed["value"] == 42.90


def test_delivery_address_change_is_surfaced_not_passed():
    out = _run("delivery_address_confirmed")
    assert out.status == CheckStatus.REVIEW
    assert out.observed["conflicted"] is True
    assert len(out.observation_trail) > 1


def test_every_result_carries_evidence_with_a_timestamp():
    out = _run("plan_intro_price")
    assert out.evidence and out.evidence[0]["timestamp"]
    assert out.evidence[0]["segment_id"]
    assert out.evidence[0]["timing_source"] == TimingSource.ESTIMATED


def test_dead_air_is_unscorable_rather_than_failed():
    out = _run("dead_air")
    assert out.status == CheckStatus.NOT_APPLICABLE


def test_behaviour_check_degrades_to_review_without_a_model():
    out = _run("objection_handling")
    assert out.status == CheckStatus.REVIEW


def test_mock_identity_is_extracted_and_matches_crm():
    segs, _ = _segments(SPEC["transcript"])
    store = facts_module.extract(segs, crm=SPEC["crm_fields"])
    email = next(o for o in store.get("email"))
    assert email.value == SPEC["crm_fields"]["email"]
    assert "Helen Carter" in " ".join(
        o.value for o in store.get("customer_full_name") if isinstance(o.value, str)
    )
    assert any("River Road" in str(o.value) for o in store.get("delivery_address"))
