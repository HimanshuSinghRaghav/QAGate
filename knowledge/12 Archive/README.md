---
type: archive
status: current
updated: 2026-09-19
tags: [archive]
---

# Archive (move, don’t delete)

This lane is for content that is **no longer active** but you might want later:

- Finished experiments
- Superseded ADRs
- Resolved one-off bugs
- Old prompt versions

## Rule

Prefer **moving** notes into `12 Archive/` over deleting them.

## How to archive a note

1. Set frontmatter `status: archived` (optional `archivedAt: YYYY-MM-DD`).
2. Move to `12 Archive/YYYY/Your Note Title.md`.

## What not to archive

Anything still referenced as current in `Home.md` or `09 AI Context/START-HERE.md`.
