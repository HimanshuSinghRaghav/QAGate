---
type: adr
status: current
updated: 2026-09-19
tags: [backend, adr]
---

# ADR-002 — Unavailable LLM cannot ship a sale

## Context

OpenRouter can timeout, return non-JSON, or be turned off. If that path defaulted to PASS, a missing model would auto-submit unsafe sales.

## Decision

`complete_json` returns `None` on any failure (no key, timeout, bad JSON). Callers degrade to **REVIEW**, never PASS. `/health` exposes `llm_enabled`.

## Consequences

- Fail-closed on the AI path.
- Demo and CI can run without a key.
- More volume hits the QA queue when the model is down — that is the correct direction.

## Related

- [[03 Modules/LLM]]
- [[03 Modules/Gate]]
