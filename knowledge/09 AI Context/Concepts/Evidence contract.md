---
type: concept
status: current
updated: 2026-09-19
tags: [backend, concept]
---

# Evidence contract

## Definition

Every check result must resolve to a transcript line, an audio timestamp, a `timing_source`, and the check version live on the call date.

## Why it matters

Traceability is 20% of judging. The UI is just a view of this contract.

## Where it appears in the code

- `CheckOutcome.evidence` / `observation_trail` in `services/checks/base.py`
- `CheckResult` JSONB columns
- `SegmentOut.text` is redacted; timestamp from `timestamp_label`

## Anti-patterns

- Returning PASS/FAIL with an empty evidence list.
- Presenting estimated timings as ASR measurements.

## Quick tests

- Open lead 3613790: every open issue has a timestamp you can seek to.
- `timing_source` is `estimated` or `asr`, never missing.
