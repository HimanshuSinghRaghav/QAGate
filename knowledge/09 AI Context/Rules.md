---
type: rules
status: current
updated: 2026-09-19
tags: [qa-gate]
---

# Architecture

FastAPI route

↓

Service (orchestration / scoring / review)

↓

Check handler OR extractor OR gate (pure functions)

↓

SQLAlchemy models → PostgreSQL

# Rules (agent + human checklist)

- **Layering:** Routes load/save. Services orchestrate. Check handlers never touch the database and never decide the gate. The gate never re-reads the transcript.
- **Deterministic first:** Prices, speeds, dates, emails, CRM comparisons live in `services/extraction/normalizer.py` and factual handlers. The LLM is consulted only for borderline script matches, uncertain extractions, and behaviour checks. It can move PASS / FAIL / REVIEW. It can never supply the expected value.
- **Unavailable model cannot ship a sale:** Every LLM path returns `None` on failure. The caller degrades to REVIEW, never to PASS. `LLM_ENABLED=false` is a valid production-like mode (more calls go to QA).
- **Conversation state, not first occurrence:** `state_tracker.resolve()` takes the latest assertion, flags conflicts, drops confidence. Do not score the first mention of delivery address / price.
- **Missing input is `NOT_APPLICABLE`, not `FAIL`:** Dead air cannot be measured from estimated timestamps. Interruptions cannot be counted when diarization is unreliable. Do not invent a finding.
- **Call date picks the check version:** `checks_effective_on(db, retailer_id, call.started_at)` — not today's library. Results store the resolved version.
- **Evidence is mandatory:** Every `CheckOutcome` carries transcript line, timestamp, `timing_source`, and check version (persisted on `CheckResult`).
- **Do not rewrite the sale:** Identify the problem. No auto-correction, no coaching copy, no contacting the customer.
- **Overrides re-run the gate:** Require a reason. Record before/after status and gate. Never set `gate_decision` by hand.
- **API never returns `raw_text`:** Only `redacted_text` leaves the database (`SegmentOut.text` aliases `redacted_text`).
- **Reuse conventions:** Prefer existing handlers, `FactStore`, and `present.py` labels. Adding a check is a row in `app/seed/data/checks.py` plus a registered handler — not a new module.
- Do not invent APIs or schemas; verify in code under `backend/app/` and `web/`.
