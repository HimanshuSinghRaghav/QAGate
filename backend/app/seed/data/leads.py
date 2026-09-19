"""Retailer, rate card and synthetic leads.

Every value in the plan is taken from what the retailer's own offer should be. The
transcript is then measured against it. CRM fields are the same mock identity that
was filled into the transcript, so a factual comparison is still a real comparison
without any real customer data touching the system.
"""
from datetime import UTC, datetime

from app.seed.data.identity import CRM_FIELDS, DELIVERY_ADDRESS, SERVICE_ADDRESS
from app.seed.data.transcript import (
    CALL_TRANSCRIPT_RAW, clean_variant, misquoted_rate_variant,
)

RETAILER = {
    "id": "retailer_1",
    "name": "FibreLink",
    "vertical": "broadband",
}

PLAN = {
    "id": "plan_value_25",
    "retailer_id": "retailer_1",
    "name": "Value 25 - NBN",
    "intro_price": 42.90,
    "intro_term_months": 6,
    "regular_price": 72.90,
    "download_mbps": 25.0,
    "upload_mbps": 8.5,
    "contract_term": "month_to_month",
    "modem_model": "CF40",
    "modem_upfront_cost": 0.0,
    "delivery_days_min": 3,
    "delivery_days_max": 5,
    "total_minimum_cost": 317.00,
    "development_fee": 275.00,
    "attributes": {
        "upload_peak_window": "19:00-23:00",
        "modem_description": "Netcom CF40 Wi-Fi 6",
    },
}

_CRM_BASE = dict(CRM_FIELDS)

LEADS = [
    {
        # The real supplied call. Expected outcome: QA_REVIEW - the delivery address
        # changes mid-call and the total minimum cost is stated two different ways.
        "id": "3613790",
        "retailer_id": "retailer_1",
        "plan_id": "plan_value_25",
        "agent_id": "agent_a",
        "tl_id": "tl_01",
        "campaign": "inbound",
        "site": "site_01",
        "last_completed_step": "application_submitted",
        "crm_fields": {**_CRM_BASE, "delivery_address": DELIVERY_ADDRESS},
        "call": {
            "started_at": datetime(2026, 9, 15, 10, 0, tzinfo=UTC),
            "duration_seconds": 1800,
            "recording_url": "s3://cimet-recordings/3613790.wav",
        },
        "transcript": CALL_TRANSCRIPT_RAW,
    },
    {
        # Same call, cleaned of the two ambiguities. Expected outcome: AUTO_APPROVED.
        "id": "3613791",
        "retailer_id": "retailer_1",
        "plan_id": "plan_value_25",
        "agent_id": "agent_b",
        "tl_id": "tl_01",
        "campaign": "paid_search",
        "site": "site_01",
        "last_completed_step": "application_submitted",
        "crm_fields": {**_CRM_BASE, "delivery_address": SERVICE_ADDRESS},
        "call": {
            "started_at": datetime(2026, 9, 15, 13, 30, tzinfo=UTC),
            "duration_seconds": 1620,
            "recording_url": "s3://cimet-recordings/3613791.wav",
        },
        "transcript": clean_variant(),
    },
    {
        # Agent quotes $35.90 against a $42.90 rate card, and the call falls after the
        # disclaimer wording changed. Expected outcome: HELD.
        "id": "3613792",
        "retailer_id": "retailer_1",
        "plan_id": "plan_value_25",
        "agent_id": "agent_a",
        "tl_id": "tl_01",
        "campaign": "affiliate",
        "site": "site_02",
        "last_completed_step": "application_submitted",
        "crm_fields": {**_CRM_BASE, "delivery_address": SERVICE_ADDRESS},
        "call": {
            "started_at": datetime(2026, 9, 17, 9, 15, tzinfo=UTC),
            "duration_seconds": 1740,
            "recording_url": "s3://cimet-recordings/3613792.wav",
        },
        "transcript": misquoted_rate_variant(),
    },
    {
        # Same agent, same failing check, inside the rolling seven days. Together with
        # 3613792 this is what trips the repeat-offence flag.
        "id": "3613793",
        "retailer_id": "retailer_1",
        "plan_id": "plan_value_25",
        "agent_id": "agent_a",
        "tl_id": "tl_01",
        "campaign": "affiliate",
        "site": "site_02",
        "last_completed_step": "application_submitted",
        "crm_fields": {**_CRM_BASE, "delivery_address": SERVICE_ADDRESS},
        "call": {
            "started_at": datetime(2026, 9, 18, 11, 5, tzinfo=UTC),
            "duration_seconds": 1500,
            "recording_url": "s3://cimet-recordings/3613793.wav",
        },
        "transcript": misquoted_rate_variant(),
    },
    {
        # Third failure of the same critical check by the same agent inside seven days.
        # This is the row that trips the repeat-offence flag and the TL warning.
        "id": "3613794",
        "retailer_id": "retailer_1",
        "plan_id": "plan_value_25",
        "agent_id": "agent_a",
        "tl_id": "tl_01",
        "campaign": "owned_site",
        "site": "site_02",
        "last_completed_step": "application_submitted",
        "crm_fields": {**_CRM_BASE, "delivery_address": SERVICE_ADDRESS},
        "call": {
            "started_at": datetime(2026, 9, 18, 15, 40, tzinfo=UTC),
            "duration_seconds": 1680,
            "recording_url": "s3://cimet-recordings/3613794.wav",
        },
        "transcript": misquoted_rate_variant(),
    },
]
