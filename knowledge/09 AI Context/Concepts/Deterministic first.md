---
type: concept
status: current
updated: 2026-09-19
tags: [backend, concept]
---

# Deterministic first

## Definition

Prices, speeds, dates, emails, and CRM comparisons are arithmetic and string work. The LLM is a last resort for borderline script, uncertain extraction, and behaviour.

## Why it matters

The gate is auditable. "GPT said PASS" is not an answer a mentor will accept.

## Where it appears in the code

- [[03 Modules/Extraction]] — `normalizer.py`, `facts.py`
- [[03 Modules/Check Library]] — factual handlers
- [[03 Modules/LLM]] — three call sites only
- [[08 Decisions/ADR-001 Deterministic first model last]]

## Anti-patterns

- Sending the raw transcript to the model to decide a rate match.
- Letting the model invent the expected plan price.

## Quick tests

- `scripts/dry_run.py` with LLM off still produces a gate decision.
- A $35.90 vs $42.90 fail does not require OpenRouter.
