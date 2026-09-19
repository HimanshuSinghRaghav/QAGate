---
type: prompt
status: current
updated: 2026-09-19
tags: [prompt]
---

# Prompt — Add check handler

Pre-read: [[03 Modules/Check Library]], [[09 AI Context/Rules]].

## Copy/paste prompt

```text
Add a new QA check to qt-gate.

1. Register a handler with @handler("name") in verbatim.py, factual.py, or behaviour.py.
2. Add a declarative row in backend/app/seed/data/checks.py (handler, critical, weight, effective window).
3. Handler must return CheckOutcome with evidence (segment, timestamp, timing_source). Never write to the DB. Never set the gate.
4. If the fact can change mid-call, use state_tracker.resolve and store observation_trail.
5. If inputs cannot support a judgement, return NOT_APPLICABLE, not FAIL.
6. LLM only if the check is semantic/behaviour; expected value still comes from Plan/CRM/config.
7. Re-seed, add a test, update [[03 Modules/Check Library]] and [[05 APIs/Route Map]] if handlers() list changed.
```
