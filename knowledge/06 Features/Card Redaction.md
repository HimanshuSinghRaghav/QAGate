---
type: feature
status: current
updated: 2026-09-19
tags: [feature, guardrail]
---

# Feature: Card Redaction

If a card number is spoken, the transcript view is redacted and the compliance check still flags the violation. The number never reaches the UI.

## Purpose

Required guardrail from the brief. Identify the process failure; do not display PAN.

## User story

As a reviewer I see `[REDACTED]` and a FAIL on `no_card_data_spoken`, never `4111…`.

## Modules involved

- [[03 Modules/Transcript]]
- [[03 Modules/Check Library]] (`no_card_data` handler)

## Entry points / APIs

- Runs on ingest (`redact()`).
- `GET /api/v1/leads/{id}/transcript` maps `redacted_text` → `text`.
- Check `no_card_data_spoken` consumes redaction findings.

## Scoring / gate touchpoints

Critical behaviour check. Luhn-validated digit runs and spoken-digit runs.

## Security / guardrails

`raw_text` stays in the DB. API schema aliases `redacted_text` only.

## Future improvements

1. Extend to CVV / expiry spoken patterns if the retailer requires it.
2. Separate storage encryption for `raw_text` in production.
