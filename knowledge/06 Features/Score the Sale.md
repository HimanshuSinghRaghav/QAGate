---
type: feature
status: current
updated: 2026-09-19
tags: [feature]
---

# Feature: Score the Sale

The core product: a finished call is scored against the retailer's versioned library and a gate decides whether it ships.

## Purpose

No sale ships unscored. The system explains why in seconds rather than a 30-minute listen.

## User story

As a team lead, I open a lead and immediately see AUTO_APPROVED / HELD / QA_REVIEW, the failing criticals, and the timestamps to play.

## Modules involved

- [[03 Modules/Ingestion]]
- [[03 Modules/Scoring]]
- [[03 Modules/Gate]]
- [[03 Modules/Dashboard]]

## Entry points / APIs

- `POST /api/v1/leads/{id}/score`
- `GET /api/v1/leads/{id}/results`
- Home dashboard KPIs

## Scoring / gate touchpoints

Full pipeline in [[03 Modules/Scoring]]. Gate order in [[09 AI Context/Concepts/Gate order]].

## Security / guardrails

API returns redacted transcript only. LLM cannot auto-pass on failure. Identify, do not rewrite the sale.

## Future improvements

1. Wire a real transcription callback instead of posting `transcript_text`.
2. Replace seed `s3://` recording URLs with stored objects.
3. Auth when this leaves the demo.
