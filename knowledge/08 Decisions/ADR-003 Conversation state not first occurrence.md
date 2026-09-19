---
type: adr
status: current
updated: 2026-09-19
tags: [backend, adr]
---

# ADR-003 — Conversation state, not first occurrence

## Context

In the supplied FibreLink call the delivery address is asserted several times and changes (same-as-service → different entrance). First-mention matching produces a confident false PASS.

## Decision

`state_tracker.resolve()` takes the **latest** assertion, flags conflicts, and drops confidence so the gate can route to QA. Stateful checks (`stateful_match`) store the full `observation_trail`.

## Consequences

- Lead `3613790` is a QA_REVIEW demo, not a silent pass.
- Reviewers see the correction history in the workspace.
- Never average conflicting values away.

## Related

- [[09 AI Context/Concepts/State tracker]]
- [[03 Modules/Extraction]]
- `backend/overview/2.md`
