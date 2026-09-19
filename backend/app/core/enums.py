"""Vocabulary shared by every module. Keep this small and stable."""
from enum import StrEnum


class CheckType(StrEnum):
    VERBATIM = "VERBATIM"      # transcript vs approved script
    FACTUAL = "FACTUAL"        # transcript vs CRM / plan / rate card
    BEHAVIOUR = "BEHAVIOUR"    # transcript only


class CheckStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"                  # evaluated, but not safe to decide automatically
    NOT_APPLICABLE = "NOT_APPLICABLE"  # cannot be judged from available inputs
    ERROR = "ERROR"                    # the checker itself broke


class GateDecision(StrEnum):
    AUTO_APPROVED = "AUTO_APPROVED"
    HELD = "HELD"
    QA_REVIEW = "QA_REVIEW"
    HUMAN_SAMPLE = "HUMAN_SAMPLE"


class Speaker(StrEnum):
    AGENT = "agent"
    CUSTOMER = "customer"
    UNKNOWN = "unknown"


class TimingSource(StrEnum):
    ASR = "asr"              # real word-level timings from the transcription provider
    ESTIMATED = "estimated"  # derived from word counts; flagged as such in evidence
