---
type: concept
status: current
updated: 2026-09-19
tags: [backend, concept]
---

# State tracker

## Definition

For facts that change mid-call (especially delivery address), take the latest asserted value, flag the conflict, drop confidence, and keep the full trail.

## Why it matters

First-occurrence matching is a confident false PASS on the supplied call.

## Where it appears in the code

- [[03 Modules/Extraction]] — `state_tracker.resolve()`
- Handler `stateful_match`
- [[08 Decisions/ADR-003 Conversation state not first occurrence]]

## Anti-patterns

- `transcript.includes("same address")` → PASS.
- Averaging conflicting values.

## Quick tests

- Lead 3613790 delivery address is REVIEW/conflicted, not a clean PASS.
- `observation_trail` has more than one value.
