---
type: module
status: current
module: check-library
updated: 2026-09-19
tags: [backend]
---

# Check Library Module

> Path: `backend/app/models/check_library.py`, `backend/app/seed/data/checks.py`, `backend/app/services/checks/`  
> Related: [[06 Features/Check Versioning]], [[08 Decisions/ADR-005 Call date picks check version]]

---

## Purpose

The heart of the business rules. A check is never scored by id alone — it is scored by the **version live on the call date**. Adding a retailer check is a declarative row (`config.handler`), not a new service.

Three families from the brief:

| Type | Meaning | Typical method |
|------|---------|----------------|
| `VERBATIM` | Transcript vs approved script | Fuzzy `script_match` |
| `FACTUAL` | Transcript vs CRM / plan / rate card | Deterministic match |
| `BEHAVIOUR` | Transcript only | Timestamps or LLM |

---

## Entry points

| Method | Path |
|--------|------|
| `GET` | `/api/v1/checks` |
| `GET` | `/api/v1/checks/effective?retailer_id=&at=` |
| `GET` | `/api/v1/checks/handlers` |

UI: `/checks` (Playbooks).

## Handlers registered

**Verbatim:** `script_match`

**Factual:** `money_match`, `numeric_match`, `enum_match`, `range_match`, `crm_match`, `stateful_match`, `fact_present`, `fee_applicability`

**Behaviour:** `no_card_data`, `mute_before_payment`, `dead_air`, `interruptions`, `llm_behaviour`

## Seeded versioning demo

`recording_disclaimer` v1 effective until 16 Sep 2026, v2 wording after. Lead `3613790` (15 Sep) scores v1; lead `3613792` (17 Sep) scores v2. Same words, different answer.

## Contract

Handlers receive `CheckContext` (lead, plan, transcript, segments, `FactStore`, definition) and return `CheckOutcome`. They never touch the DB and never decide the gate. See `services/checks/base.py`.
