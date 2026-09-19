---
type: concept
status: current
updated: 2026-09-19
tags: [backend, concept]
---

# Card redaction

## Definition

Redact card data before anyone sees the transcript, but still flag the compliance violation. The API never returns `raw_text`.

## Why it matters

Required guardrail. Displaying PAN is a product failure even if the check FAILs correctly.

## Where it appears in the code

- `services/transcript/redaction.py` (Luhn + spoken digits)
- `SegmentOut.text` aliases `redacted_text`
- Handler `no_card_data`
- [[06 Features/Card Redaction]]

## Anti-patterns

- Scoring on display text then losing the finding.
- Sending `raw_text` to the frontend "just for debugging".

## Quick tests

- Transcript endpoint JSON has no 13–19 digit Luhn numbers.
- `no_card_data` can FAIL while UI shows `[REDACTED]`.
