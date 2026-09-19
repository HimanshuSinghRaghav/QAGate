---
type: adr
status: current
updated: 2026-09-19
tags: [backend, adr]
---

# ADR-004 — Missing input is NOT_APPLICABLE, not FAIL

## Context

Dead air cannot be measured from estimated timestamps. Interruptions cannot be counted when customer replies are folded into agent turns. Inventing a FAIL would be a false critical.

## Decision

`CheckOutcome.not_applicable(reason)` when inputs cannot support a judgement. On a **critical** check, the gate treats NOT_APPLICABLE as uncertainty → `QA_REVIEW`, not as a pass.

## Consequences

- Guardrails criterion: do not invent findings.
- Coaching checks (dead air, interruptions) stay unscorable until ASR timings / diarization are real.
- UI has an Unscorable tab instead of hiding these.

## Related

- [[03 Modules/Gate]]
- [[03 Modules/Transcript]]
