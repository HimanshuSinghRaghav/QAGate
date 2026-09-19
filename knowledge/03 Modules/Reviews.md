---
type: module
status: current
module: reviews
updated: 2026-09-19
tags: [backend]
---

# Reviews Module

> Path: `backend/app/services/scoring/review.py`, `backend/app/api/v1/reviews.py`  
> Related: [[06 Features/Human Override]], [[03 Modules/Gate]]

---

## Purpose

Human review queue and the override path. An override does three mandatory things: change the result, write an immutable `Override` row (before **and** after gate), re-run the same gate. Silent overrides are rejected.

---

## Entry points

| Method | Path |
|--------|------|
| `GET` | `/api/v1/reviews/queue?decision=&limit=` |
| `POST` | `/api/v1/reviews/results/{result_id}/override` |

UI: `/queue` (Inbox) and override form in [[03 Modules/Frontend]] lead workspace.

## `apply_override`

- Require non-empty `reason`.
- `result.status = new_status`, `confidence = 1.0`, `method = human_override`.
- Recompute gate from sibling results.
- Persist `previous_gate` / `new_gate`.
- `AuditEvent` `check_result_overridden`.

Allowed `new_status`: PASS | FAIL | REVIEW (`OverrideRequest`).
