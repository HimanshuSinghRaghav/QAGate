---
type: module
status: current
module: gate
updated: 2026-09-19
tags: [backend]
---

# Gate Module

> Path: `backend/app/services/gate/gate.py`  
> Related: [[09 AI Context/Concepts/Gate order]], [[06 Features/Score the Sale]]

---

## Purpose

One function, no side effects, fully explainable: `decide(lead_id, results) -> GateOutcome`.

The brief: all critical pass → auto-submit; any critical fail → hold for TL; low confidence → QA; nothing uncertain auto-passes.

---

## Entry points

Not HTTP. Called from `run_scoring` and `apply_override`.

## Decision order (deliberate)

1. Critical **FAIL** → `HELD`
2. Critical **REVIEW** or **ERROR** → `QA_REVIEW`
3. Critical **PASS** with confidence `< settings.confidence_threshold` (0.80) → `QA_REVIEW`
4. Critical **NOT_APPLICABLE** → `QA_REVIEW`
5. Else `AUTO_APPROVED`, of which `_is_sampled(lead_id)` → `HUMAN_SAMPLE`

Sampling: SHA-256 of lead id vs `human_sample_rate` (0.05) when `deterministic_sampling=true` so the demo is reproducible.

## Scores

Weighted % of PASS over applicable results, with and without criticals (`score_with_fatals` / `score_without_fatals`). These are rollups, not the gate.

## Anti-pattern

Setting `ScoringRun.gate_decision` in an override handler. Overrides must re-run `decide()`.
