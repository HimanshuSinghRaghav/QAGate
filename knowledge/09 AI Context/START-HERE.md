---
type: start
status: current
updated: 2026-09-19
tags: [qa-gate]
---

# START HERE

Read this at the **start of every Cursor/Claude coding session** so the agent uses the vault as persistent truth (not memory).

## Read order (always)

1. [[Home]]
2. [[01 Project/Overview]]
3. [[02 Architecture/Architecture]]
4. Pick the relevant module from `03 Modules/` (example: [[03 Modules/Scoring]], [[03 Modules/Gate]], [[03 Modules/Frontend]])
5. If the session touches scoring/LLM/guardrails: skim [[09 AI Context/Concepts]] (e.g. [[09 AI Context/Concepts/Deterministic first]], [[09 AI Context/Concepts/Gate order]], [[09 AI Context/Concepts/Evidence contract]])
6. [[09 AI Context/Rules]]
7. Check active work:
   - [[00 Inbox/README]] (session notes + triage)
   - [[07 Bugs/README]] (open incidents)
   - [[08 Decisions/ADR-001 Deterministic first model last]] (ADRs; browse other ADRs in `08 Decisions/`)

## Session handoff (end of session)

Create/update one note under `00 Inbox/` named like:

- `Session-Handoff-YYYY-MM-DD.md`

Minimum contents:

- What changed (brief)
- What needs human review in Obsidian
- What was deferred
- What to do next (single next action)

Use `[[_templates/Session Handoff]]` as the skeleton for the note.
