---
type: prompt
status: current
updated: 2026-09-19
tags: [prompt]
---

# Prompt — Score a lead

## Copy/paste prompt

```text
Walk the scoring path for lead {id} in this repo.

1. Confirm Lead, Call, Transcript, Segments exist (ingestion before scoring).
2. Resolve checks_effective_on(retailer_id, call.started_at).
3. Extract FactStore once.
4. Run each handler; collect evidence.
5. Run gate.decide — quote which rule fired (critical FAIL vs REVIEW vs low conf vs sample).
6. Point at the UI: /leads/{id} expected vs said and timestamp.

Do not invent results. Read the latest ScoringRun from the API or seed output.
```
