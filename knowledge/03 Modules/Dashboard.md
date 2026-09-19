---
type: module
status: current
module: dashboard
updated: 2026-09-19
tags: [backend]
---

# Dashboard Module

> Path: `backend/app/services/scoring/dashboard.py`, `backend/app/api/v1/dashboard.py`  
> Related: [[03 Modules/Frontend]], [[06 Features/Score the Sale]]

---

## Purpose

Read-only rollups computed from stored results so the numbers are auditable. Built **after** the pipeline, matching overview/1.md priority.

---

## Entry points

| Method | Path |
|--------|------|
| `GET` | `/api/v1/dashboard` |
| `GET` | `/api/v1/dashboard/agents` |
| `GET` | `/api/v1/dashboard/repeat-offences` |

UI Home (`web/app/page.tsx`) fetches dashboard + agents + queue.

## Metrics

- Totals: sales scored, auto_approved, held, qa_review, human_sample
- First-pass yield = AUTO_APPROVED / runs
- Critical fail rate = runs with `criticals_failed > 0`
- Avg scores with/without fatals
- Top failing critical checks
- Auditor agreement (only over results a human actually reviewed)
- Repeat offences: same `agent_id` + `check_id`, ≥3 FAILs in 7 days → TL warning
- Unscorable check counts

Repeat-offence demo: leads `3613792`, `3613793`, `3613794` (agent_a, rate misquote).
