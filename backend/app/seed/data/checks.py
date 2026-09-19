"""Check-library export, expressed as data.

Every entry is declarative: name, type, criticality, weight, effective window, and a
`config` that names the handler and the fields it compares. Adding a check is a row,
not a code change - which is what makes swapping in the real retailer export cheap.

`recording_disclaimer` is deliberately present in two versions with different
effective windows, so version resolution is observable rather than claimed.
"""
from datetime import UTC, datetime

from app.core.enums import CheckType

RETAILER_ID = "retailer_1"

FOREVER_FROM = datetime(2020, 1, 1, tzinfo=UTC)
DISCLAIMER_V2_FROM = datetime(2026, 9, 16, tzinfo=UTC)


def _c(check_id, name, type_, critical, weight, config, description="",
       version=1, effective_from=FOREVER_FROM, effective_to=None) -> dict:
    return dict(
        check_id=check_id, version=version, retailer_id=RETAILER_ID, name=name,
        description=description, type=type_, critical=critical, weight=weight,
        effective_from=effective_from, effective_to=effective_to, config=config,
    )


CHECKS: list[dict] = [
    # ---------------------------------------------------------------- A · verbatim
    _c("recording_disclaimer", "Recording disclaimer read", CheckType.VERBATIM, True, 3.0,
       {
           "handler": "script_match",
           "expected": "please be advised that this call will be recorded for "
                       "quality assurance and training purposes",
           "required_elements": ["this call will be recorded", "quality assurance",
                                 "training purposes"],
           "pass_ratio": 0.82, "review_ratio": 0.60,
       },
       description="Consent is verified, never assumed from the existence of a recording.",
       version=1, effective_from=FOREVER_FROM, effective_to=DISCLAIMER_V2_FROM),

    _c("recording_disclaimer", "Recording disclaimer read (v2 wording)",
       CheckType.VERBATIM, True, 3.0,
       {
           "handler": "script_match",
           "expected": "please be advised that this call is being recorded and may be "
                       "monitored for quality assurance and training purposes",
           "required_elements": ["this call is being recorded", "may be monitored",
                                 "quality assurance", "training purposes"],
           "pass_ratio": 0.82, "review_ratio": 0.60,
       },
       description="Wording tightened from 16 Sep 2026. Calls before that date are "
                   "scored against v1.",
       version=2, effective_from=DISCLAIMER_V2_FROM, effective_to=None),

    # ----------------------------------------------------------------- B · factual
    _c("plan_intro_price", "Introductory price quoted", CheckType.FACTUAL, True, 3.0,
       {"handler": "money_match", "fact": "intro_price", "plan_field": "intro_price",
        "tolerance": 0.0},
       description="Price quoted on the call must equal the rate card."),

    _c("plan_regular_price", "Ongoing price disclosed", CheckType.FACTUAL, True, 2.5,
       {"handler": "money_match", "fact": "regular_price", "plan_field": "regular_price",
        "tolerance": 0.0}),

    _c("plan_intro_term", "Introductory term disclosed", CheckType.FACTUAL, True, 2.0,
       {"handler": "numeric_match", "fact": "intro_term_months",
        "plan_field": "intro_term_months", "unit": "months", "tolerance": 0.0}),

    _c("plan_download_speed", "Download speed quoted", CheckType.FACTUAL, True, 2.0,
       {"handler": "numeric_match", "fact": "download_mbps", "plan_field": "download_mbps",
        "unit": "Mbps", "tolerance": 0.0}),

    _c("plan_upload_speed", "Upload speed quoted", CheckType.FACTUAL, False, 1.0,
       {"handler": "numeric_match", "fact": "upload_mbps", "plan_field": "upload_mbps",
        "unit": "Mbps", "tolerance": 0.0}),

    _c("contract_term_disclosed", "Contract term disclosed", CheckType.FACTUAL, True, 2.0,
       {"handler": "enum_match", "fact": "contract_term", "plan_field": "contract_term",
        "also_accept": ["no_lock_in"]},
       description="Month-to-month must be stated. ASR frequently mangles this phrase, "
                   "so an uncertain extraction is adjudicated, not assumed."),

    _c("modem_model_stated", "Modem model stated correctly", CheckType.FACTUAL, False, 1.0,
       {"handler": "enum_match", "fact": "modem_model", "plan_field": "modem_model"}),

    _c("modem_upfront_cost", "Modem upfront cost stated", CheckType.FACTUAL, True, 2.0,
       {"handler": "money_match", "fact": "modem_upfront_cost",
        "plan_field": "modem_upfront_cost", "tolerance": 0.0}),

    _c("delivery_timeframe", "Modem delivery timeframe stated", CheckType.FACTUAL, False, 1.0,
       {"handler": "range_match", "fact": "delivery_days",
        "plan_field_min": "delivery_days_min", "plan_field_max": "delivery_days_max"}),

    _c("total_minimum_cost", "Total minimum cost stated correctly", CheckType.FACTUAL,
       True, 2.5,
       {"handler": "money_match", "fact": "total_minimum_cost",
        "plan_field": "total_minimum_cost", "tolerance": 0.0}),

    _c("development_fee_explained", "New development fee explained correctly",
       CheckType.FACTUAL, True, 2.5,
       {"handler": "fee_applicability", "crm_field": "development_fee_applicable"},
       description="If the fee applies to the address, telling the customer it will not "
                   "be charged is a misrepresentation."),

    _c("account_holder_name", "Account holder name verified", CheckType.FACTUAL, True, 3.0,
       {"handler": "crm_match", "fact": "customer_full_name",
        "crm_field": "customer_full_name"}),

    _c("email_captured", "Email captured and read back", CheckType.FACTUAL, True, 3.0,
       {"handler": "crm_match", "fact": "email", "crm_field": "email"}),

    _c("mobile_captured", "Mobile number verified", CheckType.FACTUAL, True, 2.0,
       {"handler": "crm_match", "fact": "phone", "crm_field": "phone"}),

    _c("dob_verified", "Date of birth verified", CheckType.FACTUAL, True, 2.0,
       {"handler": "crm_match", "fact": "dob", "crm_field": "dob"}),

    _c("service_address_confirmed", "Connection address confirmed", CheckType.FACTUAL,
       True, 2.5,
       {"handler": "crm_match", "fact": "service_address", "crm_field": "service_address"}),

    _c("delivery_address_confirmed", "Modem delivery address confirmed",
       CheckType.FACTUAL, True, 2.0,
       {"handler": "stateful_match", "fact": "delivery_address",
        "crm_field": "delivery_address"},
       description="Resolved from conversation state: the customer's latest asserted "
                   "address wins, and a mid-call change is surfaced."),

    _c("current_provider_confirmed", "Current provider confirmed", CheckType.FACTUAL,
       False, 1.0,
       {"handler": "crm_match", "fact": "current_provider", "crm_field": "current_provider",
        "require_verification": False}),

    _c("otp_completed", "OTP received by customer", CheckType.FACTUAL, False, 1.0,
       {"handler": "fact_present", "fact": "otp_code", "fail_if_absent": False,
        "present_reason": "Customer confirmed receipt of the one-time code."}),

    _c("reference_number_captured", "Application reference captured", CheckType.FACTUAL,
       False, 1.0,
       {"handler": "fact_present", "fact": "reference_number", "fail_if_absent": False,
        "present_reason": "Application reference read back by the customer."}),

    # --------------------------------------------------------------- C · behaviour
    _c("no_card_data_spoken", "No card data spoken on the recording",
       CheckType.BEHAVIOUR, True, 3.0,
       {"handler": "no_card_data"},
       description="Compliance guardrail. The violation is flagged; the number is "
                   "redacted before storage and never surfaced."),

    _c("payment_mute_compliance", "Recording muted before payment collection",
       CheckType.BEHAVIOUR, True, 2.5,
       {"handler": "mute_before_payment"}),

    _c("dead_air", "Dead air", CheckType.BEHAVIOUR, False, 1.0,
       {"handler": "dead_air", "threshold_seconds": 30},
       description="Coaching note only. Requires real ASR word timings."),

    _c("interruptions", "Interruptions / talk-over", CheckType.BEHAVIOUR, False, 1.0,
       {"handler": "interruptions", "max_interruptions": 5},
       description="Coaching note only. Requires reliable speaker separation."),

    _c("objection_handling", "Objection handling", CheckType.BEHAVIOUR, False, 1.5,
       {"handler": "llm_behaviour"},
       description="Did the agent acknowledge the customer's hesitation about savings "
                   "and respond with relevant information rather than pressure?"),

    _c("rapport", "Rapport and professionalism", CheckType.BEHAVIOUR, False, 1.0,
       {"handler": "llm_behaviour"},
       description="Was the agent courteous, did they let the customer finish, and did "
                   "they answer the questions actually asked?"),
]
