---
type: feature
status: current
updated: 2026-09-19
tags: [feature]
---

# Feature: Human Override

A human auditor can overturn a check. The decision is logged and the gate is re-run — never set by hand.

## Purpose

The machine is not unquestionable truth. Overrides measure auditor agreement and can release a held sale through the same rules.

## User story

As an auditor, I set a FAIL to PASS with a reason ("customer confirmed delivery address at 16:24") and see `previous_gate` → `new_gate`.

## Modules involved

- [[03 Modules/Reviews]]
- [[03 Modules/Gate]]

## Entry points / APIs

- `POST /api/v1/reviews/results/{result_id}/override`
- Body: `{ new_status, actor, reason, reason_code? }`

## Scoring / gate touchpoints

`apply_override` updates the result (`method=human_override`, confidence 1.0), calls `decide()` on siblings, writes `Override` + `AuditEvent`.

## Security / guardrails

Empty reason → `ReviewError`. No silent overrides.

## Future improvements

1. Reason-code enum from the retailer, not free text only.
2. Role-gated actor instead of a string field.
