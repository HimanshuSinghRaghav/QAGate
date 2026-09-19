---
type: concept
status: current
updated: 2026-09-19
tags: [backend, concept]
---

# Gate order

## Definition

Known critical FAIL outranks doubt. Uncertainty (REVIEW, ERROR, low confidence, unscorable critical) goes to QA. Only then can a sale auto-submit, with a 5% human sample.

## Why it matters

Nothing uncertain auto-passes. That is the brief's gate logic.

## Where it appears in the code

- [[03 Modules/Gate]] — `decide()`
- [[08 Decisions/ADR-004 Missing input is NOT_APPLICABLE]]
- Default threshold 0.80, sample rate 0.05, deterministic hash of lead id

## Anti-patterns

- Averaging scores to decide the gate.
- Setting `gate_decision` in an override without re-running `decide()`.
- Treating NOT_APPLICABLE on a critical as PASS.

## Quick tests

- One critical FAIL → HELD even if ten other checks PASS.
- All critical PASS at 0.79 → QA_REVIEW.
