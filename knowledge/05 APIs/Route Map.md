---
type: apis
status: current
updated: 2026-09-19
tags: [qa-gate, api]
---

# APIs — Route Map

Single surface: FastAPI under `/api/v1`. No JWT. CORS `*`. Swagger at http://localhost:8000/docs.

Frontend client: `web/lib/api.ts` → `NEXT_PUBLIC_API_URL` (default `http://127.0.0.1:8000`).

For endpoint details, follow wikilinks into module docs.

---

## Meta

| Method | Path | Role |
|--------|------|------|
| `GET` | `/health` | `status`, `llm_enabled`, model, confidence threshold, sample rate |

---

## Ingestion

See [[03 Modules/Ingestion]], [[03 Modules/Transcript]].

| Method | Path | Role |
|--------|------|------|
| `POST` | `/api/v1/calls/ingest` | Create Call; optional `transcript_text` |
| `GET` | `/api/v1/leads/{lead_id}/transcript` | **Redacted** segments only |

`POST /calls/ingest` body (`IngestRequest`): `lead_id`, `retailer_id`, `plan_id?`, `recording_url?`, `call_started_at`, `duration_seconds?`, `transcript_text?`. Lead must already exist (seed or prior insert).

---

## Scoring + leads

See [[03 Modules/Scoring]].

| Method | Path | Role |
|--------|------|------|
| `POST` | `/api/v1/leads/{lead_id}/score` | Run engine + gate |
| `GET` | `/api/v1/leads/{lead_id}/results` | Latest `ScoredLeadOut` |
| `GET` | `/api/v1/leads/{lead_id}` | Lead card (CRM, plan rows, open issues, gate headline) |
| `GET` | `/api/v1/leads` | All leads as cards |
| `GET` | `/api/v1/leads/{lead_id}/audit` | Audit events with `event_label` |

`ScoredLeadOut` splits results into `critical` / `non_critical` / `unscorable` plus `run` and `case`.

---

## Check library

See [[03 Modules/Check Library]].

| Method | Path | Role |
|--------|------|------|
| `GET` | `/api/v1/checks` | All definitions (`?retailer_id=`) |
| `GET` | `/api/v1/checks/effective?retailer_id=&at=` | Version live on that datetime |
| `GET` | `/api/v1/checks/handlers` | Registered handler names |

Resolution is by **call date**, not today.

---

## Review

See [[03 Modules/Reviews]].

| Method | Path | Role |
|--------|------|------|
| `GET` | `/api/v1/reviews/queue?decision=&limit=` | Scoring runs (filter by gate) |
| `POST` | `/api/v1/reviews/results/{result_id}/override` | `{ new_status, actor, reason, reason_code? }` |

Override response includes `previous_gate` and `new_gate`.

---

## Dashboard

See [[03 Modules/Dashboard]].

| Method | Path | Role |
|--------|------|------|
| `GET` | `/api/v1/dashboard` | Totals, FPY, critical fail rate, top fails, agreement, repeat offences |
| `GET` | `/api/v1/dashboard/agents` | Per-agent rollup |
| `GET` | `/api/v1/dashboard/repeat-offences` | Same agent + check, ≥3 fails in 7 days |

---

## Next.js (not FastAPI)

| Method | Path | Role |
|--------|------|------|
| `GET`/`HEAD` | `/api/audio/{leadId}` | Stream `../qa-gate/demo/audio/{id}.mp3` with Range support |

Known mismatch: disk folder is `backend/demo/audio`. See [[07 Bugs/Audio proxy still points at qa-gate]].

---

## Guardrail at the HTTP edge

`GET .../transcript` maps `Segment.redacted_text` → `text`. `raw_text` never leaves the database.
