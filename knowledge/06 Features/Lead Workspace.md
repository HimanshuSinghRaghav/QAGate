---
type: feature
status: current
updated: 2026-09-19
tags: [feature, frontend]
---

# Feature: Lead Workspace

The killer UI from the brief: why this sale failed, with expected vs said, timestamp, and jump-to-audio.

## Purpose

A reviewer should not listen to 30 minutes. They should click Rates → 14:02 → hear 20 seconds.

## User story

As Priya (TL), I open `/leads/3613790`, filter to open issues, jump the player to the evidence segment, and override with a reason if the machine was wrong.

## Modules involved

- [[03 Modules/Frontend]]
- [[03 Modules/Scoring]]
- [[03 Modules/Reviews]]

## Entry points / APIs

- Page: `/leads/[id]`
- `GET /api/v1/leads/{id}/results`, `/transcript`, `/audit`, `/leads/{id}`
- `POST /api/v1/reviews/results/{id}/override`
- `GET /api/audio/{leadId}` (Next.js)

## Scoring / gate touchpoints

Workspace shows `gate_headline`, critical / coaching / unscorable tabs, observation trail for stateful checks.

## Security / guardrails

Transcript `text` is redacted. Override requires a reason.

## Future improvements

1. Fix audio path (`qa-gate` vs `backend`) — [[07 Bugs/Audio proxy still points at qa-gate]].
2. Word-level highlight when ASR timings exist.
