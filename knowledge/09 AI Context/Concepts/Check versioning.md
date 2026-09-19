---
type: concept
status: current
updated: 2026-09-19
tags: [backend, concept]
---

# Check versioning

## Definition

Score against the library version whose `effective_from`/`effective_to` window contains `call.started_at`, not today's row.

## Why it matters

Same spoken disclaimer can pass on 15 Sep (v1) and fail on 17 Sep (v2).

## Where it appears in the code

- `services/scoring/version_resolver.py`
- [[06 Features/Check Versioning]]
- [[08 Decisions/ADR-005 Call date picks check version]]

## Anti-patterns

- `SELECT * FROM check_definitions WHERE check_id = ?` without a date.
- Mutating a live row instead of inserting version N+1.

## Quick tests

- `GET /api/v1/checks/effective?retailer_id=retailer_1&at=2026-09-15T10:00:00Z`
- Same URL with `2026-09-17T09:15:00Z`
