---
type: moc
status: current
updated: 2026-09-19
tags: [qa-gate]
---

# Home

Vault map for `qt-gate` codebase knowledge (second brain + AI context).

Open this folder as an Obsidian vault: `qt-gate/knowledge/`. Docs only — not part of the FastAPI or Next.js runtime.

## Quick start (for Cursor / Claude coding sessions)

- [[09 AI Context/START-HERE]]

## Core context

- [[01 Project/Overview]]
- [[02 Architecture/Architecture]]

## Module index

```dataview
TABLE status, updated
FROM "03 Modules"
WHERE type = "module"
SORT updated DESC
```

## Atomic concepts

```dataview
TABLE updated
FROM "09 AI Context/Concepts"
WHERE type = "concept"
SORT updated DESC
```

## Database / API / Features

- [[04 Database/Schema]]
- [[05 APIs/Route Map]]
- [[06 Features/Score the Sale]]
- [[06 Features/Lead Workspace]]
- [[06 Features/Human Override]]
- [[06 Features/Check Versioning]]
- [[06 Features/Card Redaction]]

## Ongoing work (quick dashboards)

### Open incidents (bugs)

```dataview
TABLE updated, severity
FROM "07 Bugs"
WHERE type = "bug" AND status = "open"
SORT updated DESC
```

### Current architecture decisions (ADRs)

```dataview
TABLE updated
FROM "08 Decisions"
WHERE type = "adr" AND status = "current"
SORT updated DESC
```

### Active prompts

```dataview
TABLE updated
FROM "10 Prompts"
WHERE type = "prompt" AND status = "current"
SORT updated DESC
```

## Ongoing work (manual links)

- [[12 Archive/README]]
- [[00 Inbox/README]]
- [[07 Bugs/README]]
- [[08 Decisions/ADR-001 Deterministic first model last]]
- [[10 Prompts/Update vault after code change]]
- [[11 Meetings/README]]
