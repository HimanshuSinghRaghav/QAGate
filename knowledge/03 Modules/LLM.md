---
type: module
status: current
module: llm
updated: 2026-09-19
tags: [backend]
---

# LLM Module

> Path: `backend/app/services/llm/`  
> Related: [[08 Decisions/ADR-002 Unavailable LLM cannot ship a sale]], [[09 AI Context/Concepts/Deterministic first]]

---

## Purpose

OpenRouter client used **only** where judgement is genuinely required. Strict JSON, temperature 0. Any failure returns `None` so the caller degrades to REVIEW, never PASS.

---

## Entry points

Not HTTP. `complete_json(system, user)` in `client.py`. Prompts in `prompts.py`.

Settings: `OPENROUTER_API_KEY`, `openrouter_model` (default `anthropic/claude-sonnet-4.5`), `llm_enabled`, 45s timeout.

`settings.llm_available` = enabled **and** key present. `/health` exposes this.

## Where it is consulted

1. Borderline verbatim `script_match`
2. Uncertain factual extraction (adjudication, not inventing expected)
3. `llm_behaviour` (objection handling, rapport)

## Anti-pattern

```
Transcript → GPT → "PASS"
```

Expected values come from Plan, CRM, and check `config`. The model may only move status among PASS / FAIL / REVIEW.
