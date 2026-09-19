---
type: concept
status: current
updated: 2026-09-19
tags: [backend, concept]
---

# Timing sources

## Definition

Every segment and evidence blob is either `asr` (real provider timings) or `estimated` (word-count spans). Estimates must be labelled as such.

## Why it matters

The supplied PDF had no timestamps, but traceability requires them. Lying about the source would fail the audit story.

## Where it appears in the code

- [[03 Modules/Transcript]] — `timing.py`
- Seed stamps ASR timings when `demo/audio/<lead>.timings.json` exists
- Dead air is NOT_APPLICABLE on estimated timings

## Anti-patterns

- UI copy that says "ASR at 14:02" when `timing_source` is `estimated`.
- Building a custom STT model in the hackathon.

## Quick tests

- Without timings.json, every evidence row says `estimated`.
- After ElevenLabs generate + re-seed, source becomes `asr`.
