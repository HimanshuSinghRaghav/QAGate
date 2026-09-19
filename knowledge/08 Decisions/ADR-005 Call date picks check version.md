---
type: adr
status: current
updated: 2026-09-19
tags: [backend, adr]
---

# ADR-005 — Call date picks the check version

## Context

The brief requires every score to use the check-library version live on the **call date**, not today's wording. Disclaimer script changed on 16 Sep 2026.

## Decision

`checks_effective_on(db, retailer_id, call.started_at)` filters `effective_from` / `effective_to` and picks the highest overlapping version. Every `CheckResult` stores `check_version`.

## Consequences

- Lead `3613790` (15 Sep) scores disclaimer v1 and can pass that check.
- Lead `3613792` (17 Sep) scores v2 with tighter wording.
- Swapping in a real retailer export is more rows, not a code change.

## Related

- [[06 Features/Check Versioning]]
- [[03 Modules/Check Library]]
