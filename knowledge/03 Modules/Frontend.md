---
type: module
status: current
module: frontend
updated: 2026-09-19
tags: [frontend]
---

# Frontend Module

> Path: `web/`  
> Related: [[06 Features/Lead Workspace]], [[05 APIs/Route Map]]

---

## Purpose

Next.js dashboard for a FibreLink team lead. Answers "why did this sale fail?" in seconds: expected vs said, timestamp, jump-to-audio, override.

Tagline in metadata: **Score the sale before it ships.**

---

## Routes

| Path | File | Role |
|------|------|------|
| `/` | `app/page.tsx` | KPIs, inbox slice, agents, top fails, repeat offences |
| `/queue` | `app/queue/page.tsx` | Inbox tabs: needs a person / stopped / QA / can ship / sampled |
| `/leads` | `app/leads/page.tsx` | All scored sales; `?q=` search |
| `/leads/[id]` | `app/leads/[id]/page.tsx` | [[06 Features/Lead Workspace]] |
| `/checks` | `app/checks/page.tsx` | Playbooks — versioned check library |
| `/api/audio/[leadId]` | `app/api/audio/.../route.ts` | mp3 Range streaming |

All pages `dynamic = "force-dynamic"`. API errors render `EmptyState` ("API offline — start the backend on :8000").

## Shell

`components/shell.tsx`: nav Home / Inbox / Leads / Playbooks. Persona "Priya Nair · Team lead · FibreLink". Global search posts to `/leads?q=`.

## Client

`lib/api.ts` — typed fetch, no cache. `lib/types.ts` mirrors backend enums and cards.

## Components

- `lead-workspace.tsx` — check tabs, evidence, transcript search, audio seek, override
- `gate-badge.tsx` — gate / status / type chips
- `ui.tsx` — PageHeader, Panel, buttons

## Future Improvements

1. Point audio proxy at `../backend/demo/audio` (see [[07 Bugs/Audio proxy still points at qa-gate]]).
2. Ignore leftover `DESIGN.md` (Miro tokens).
3. Auth when this leaves the hackathon demo.
