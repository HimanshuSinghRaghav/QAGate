---
type: adr
status: current
updated: 2026-09-19
tags: [backend, adr]
---

# ADR-001 — Deterministic first, model last

## Context

The gate is a business-critical decision. Prices, speeds, emails, dates, and CRM fields can be compared with arithmetic and strings. Sending the whole transcript to an LLM for "PASS" is hard to trust and hard to explain.

## Decision

Deterministic extraction + handlers are the default. OpenRouter is consulted in exactly three places: borderline script match, uncertain extraction, behaviour checks. The model can move a result among PASS / FAIL / REVIEW. It can never supply the expected value (that comes from Plan, CRM, or check `config`).

## Consequences

- Factual misses (e.g. $35.90 vs $42.90) are explainable without a model.
- Behaviour and messy ASR still have a semantic path.
- Scoring still works with `LLM_ENABLED=false` (more calls go to QA).

## Related

- [[09 AI Context/Concepts/Deterministic first]]
- [[03 Modules/Extraction]]
- [[03 Modules/LLM]]
