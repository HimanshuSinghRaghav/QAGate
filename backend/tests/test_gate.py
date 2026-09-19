"""Gate precedence. These assertions are the brief's gate logic, verbatim."""
from app.core.enums import CheckStatus, GateDecision
from app.models import CheckResult
from app.services.gate.gate import decide


def _r(status, critical=True, confidence=0.95, name="Check", weight=1.0):
    return CheckResult(id="x", run_id="r", lead_id="l", check_id="c", check_version=1,
                       check_name=name, type="FACTUAL", critical=critical, weight=weight,
                       status=status, confidence=confidence, method="deterministic",
                       reason="", expected=None, observed=None, evidence=[],
                       observation_trail=[])


def test_all_criticals_pass_auto_approves():
    assert decide("lead_clean", [_r(CheckStatus.PASS)]).decision in (
        GateDecision.AUTO_APPROVED, GateDecision.HUMAN_SAMPLE)


def test_critical_fail_holds():
    out = decide("lead_1", [_r(CheckStatus.PASS), _r(CheckStatus.FAIL)])
    assert out.decision == GateDecision.HELD


def test_low_confidence_critical_never_auto_passes():
    out = decide("lead_1", [_r(CheckStatus.PASS, confidence=0.51)])
    assert out.decision == GateDecision.QA_REVIEW


def test_non_critical_failure_does_not_hold_the_sale():
    out = decide("lead_1", [_r(CheckStatus.PASS), _r(CheckStatus.FAIL, critical=False)])
    assert out.decision != GateDecision.HELD


def test_unscorable_critical_routes_to_a_human():
    out = decide("lead_1", [_r(CheckStatus.NOT_APPLICABLE)])
    assert out.decision == GateDecision.QA_REVIEW


def test_fail_outranks_review():
    out = decide("lead_1", [_r(CheckStatus.REVIEW), _r(CheckStatus.FAIL)])
    assert out.decision == GateDecision.HELD


def test_scores_are_reported_with_and_without_fatals():
    out = decide("lead_1", [_r(CheckStatus.FAIL, critical=True),
                            _r(CheckStatus.PASS, critical=False)])
    assert out.score_with_fatals < out.score_without_fatals
