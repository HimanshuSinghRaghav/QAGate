---
type: feature
status: current
updated: 2026-09-19
tags: [feature]
---

# Feature: Check Versioning

Every result uses the check-library version that was live on the call date.

## Purpose

Regulatory / audit: today's tighter disclaimer must not rewrite yesterday's score.

## User story

As a mentor, I call `GET /api/v1/checks/effective?retailer_id=retailer_1&at=2026-09-15` vs `at=2026-09-17` and see disclaimer v1 then v2.

## Modules involved

- [[03 Modules/Check Library]]
- [[08 Decisions/ADR-005 Call date picks check version]]

## Entry points / APIs

- `GET /api/v1/checks`
- `GET /api/v1/checks/effective`
- Playbooks UI `/checks`

## Scoring / gate touchpoints

`version_resolver.checks_effective_on` inside `run_scoring`. `CheckResult.check_version` persisted.

## Security / guardrails

Do not score by `check_id` alone.

## Future improvements

1. Replace `seed/data/checks.py` with the retailer's real export.
2. Overlap warning when two versions of the same check both match a date.
