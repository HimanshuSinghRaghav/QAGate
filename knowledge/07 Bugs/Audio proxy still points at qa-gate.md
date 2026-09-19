---
type: bug
status: open
severity: minor
updated: 2026-09-19
tags: [frontend, bug]
---

# Bug: Audio proxy still points at qa-gate

## Symptom

Lead workspace player 404s even when mp3s exist under the backend demo folder. Next.js route resolves `../qa-gate/demo/audio/{leadId}.mp3`.

## Repro

1. Put `backend/demo/audio/3613790.mp3` on disk.
2. Open `/leads/3613790` and press play.
3. Network: `GET /api/audio/3613790` → 404 No recording.

## Root cause (suspected)

`web/app/api/audio/[leadId]/route.ts` still uses the old sibling folder name `qa-gate`. On disk the API is `backend/`. Root README was updated; this path was not.

## Fix / Workaround

Change both `path.resolve` roots from `qa-gate` to `backend`. Until then, symlink `qt-gate/qa-gate` → `backend` or copy mp3s to a `qa-gate/demo/audio` folder.

## Related

- [[03 Modules/Frontend]]
- [[06 Features/Lead Workspace]]
