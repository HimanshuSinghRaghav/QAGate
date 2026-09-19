---
type: prompt
status: current
updated: 2026-09-19
tags: [prompt, maintenance]
---

# Prompt — Update vault after code change

Pre-read:

- [[09 AI Context/START-HERE]]

Use this after you merge a code change so the vault stays agent-readable.

## Copy/paste prompt

```text
Given the code change summary, update the qt-gate knowledge vault.

Steps:
1. Read [[01 Project/Overview]], [[02 Architecture/Architecture]], and the relevant module note(s) from [[03 Modules]].
2. Identify what changed:
   - new/updated HTTP route(s)
   - new/updated service or handler behavior
   - new/updated model/relationship/enum
   - scoring / gate / LLM changes
   - frontend route or workspace behavior
3. Update docs in this order:
   - [[05 APIs/Route Map]] (if routes changed)
   - relevant [[03 Modules]] note(s)
   - [[04 Database/Schema]] (if relationships/enums changed)
   - [[06 Features]] (if user journey changed)
   - add an ADR in [[08 Decisions]] if it is a deliberate tradeoff
4. If README vs code drifted, add/update a bug note in [[07 Bugs]].
5. Add one [[00 Inbox]] session-handoff summarizing what you updated.

Rules:
- Follow [[09 AI Context/Rules]] exactly.
- Do not invent APIs or schemas; verify in backend/app and web/.
```
