---
type: overview
status: current
updated: 2026-09-19
tags: [qa-gate]
---

# QA Gate — Project Overview

> Automated QA scoring for sales calls. A transcript lands against a Lead, every check in the retailer's versioned library runs against it, each result carries the transcript line and timestamp that produced it, and a gate decides whether the sale auto-submits, is held for the TL, or goes to QA.
> Stack: Python 3.11+ · FastAPI · PostgreSQL · SQLAlchemy 2.0 · OpenRouter · Next.js 16 (sibling `web/` UI).

**Mental model:** Dialler → Lead ID + recording + transcript → parse / redact / time → extract facts once → run versioned checks (verbatim / factual / behaviour) → evidence → gate → AUTO_APPROVED | HELD | QA_REVIEW | HUMAN_SAMPLE.

The title line of the brief is **"Score the sale before it ships."** This is a quality-control gate, not a chatbot. Every decision must answer **"Why?"**

Source briefs: `backend/overview/1.md` (product + judging) and `backend/overview/2.md` (the messy FibreLink transcript). This note describes **what we actually built**.

---

## 1. Overall Architecture

### Stack & runtime

| Layer | Technology |
|-------|------------|
| API | FastAPI (`backend/app/main.py`), title **CIMET QA Gate** |
| Language | Python 3.11+ |
| ORM / DB | SQLAlchemy 2.0 + PostgreSQL (`localhost:5433`) |
| AI | OpenRouter (`anthropic/claude-sonnet-4.5` default) — optional |
| Web | Next.js 16 + React 19 + Tailwind 4 (`web/`) |
| Demo audio | Optional ElevenLabs mp3 + timings under `backend/demo/audio/` |

The overview recommended Node/Express/Mongo for a 12-hour solo build. We shipped **FastAPI + Postgres** so evidence, versions, and audit rows are relational and queryable.

### Entry points

| Path | Role |
|------|------|
| `backend/app/main.py` | FastAPI app, CORS `*`, `/health`, `/api/v1` |
| `backend/app/api/v1/router.py` | Ingestion, scoring, checks, reviews, dashboard |
| `web/app/layout.tsx` | App shell: Home / Inbox / Leads / Playbooks |
| `backend/app/seed/run.py` | Create tables, load fixtures, score every seeded lead |

### Layering (hard rule)

```
HTTP
  → FastAPI routes (load / save only)
  → Services (orchestration)
  → Check handlers / extractors / gate (pure)
  → SQLAlchemy models → PostgreSQL
```

Each layer only knows about the one below it. Check handlers never touch the database and never decide the gate; the gate never re-reads the transcript.

### Folder structure

```
qt-gate/
  backend/                 # FastAPI scoring API (docs still say qa-gate/)
    app/
      core/                # config, db, enums
      models/              # Retailer, Plan, Lead, Call, Transcript, Segment,
                           # CheckDefinition, ScoringRun, CheckResult, Override, AuditEvent
      schemas/             # request/response contracts
      api/v1/              # ingestion · scoring · checks · reviews · dashboard
      services/
        transcript/        # parser · redaction · timing · ingestion
        extraction/        # normalizer · facts · state_tracker
        checks/            # base (contract + registry) · verbatim · factual · behaviour
        llm/               # OpenRouter client · prompts
        scoring/           # engine · version_resolver · review · dashboard
        gate/              # gate
        present.py         # human labels for UI
      seed/                # fixtures derived from the supplied call
    overview/              # hackathon briefs (1.md product, 2.md transcript)
    scripts/               # dry_run · generate_demo_audio · verify_audio_sync
    demo/audio/            # optional <leadId>.mp3 + .timings.json
  web/                     # Next.js dashboard + lead workspace
    app/                   # routes + audio proxy
    components/            # shell, lead-workspace, badges
    lib/                   # API client → NEXT_PUBLIC_API_URL
  knowledge/               # this Obsidian vault (docs only — not runtime)
```

### High-level product graph

```
Retailer → Plan (rate card)
        → CheckDefinition (versioned library)
Lead → Call → Transcript → Segment
    → ScoringRun → CheckResult → Override
    → AuditEvent
```

---

## 2. What they are judging (why we built this shape)

From `backend/overview/1.md`:

| Area | Weight |
|------|-------:|
| Scoring accuracy | 30% |
| Coverage (all 3 check types) | 25% |
| Traceability | 20% |
| Gate & escalation logic | 15% |
| Guardrails & judgment | 10% |

95% of the score is correctness, coverage, evidence, and safe decisions — not UI polish. Priority we followed: scoring engine → traceability → gate → three check types → safety → dashboard → polish.

---

## 3. Main Modules

| Module | Path | Responsibility |
|--------|------|----------------|
| **Ingestion** | `api/v1/ingestion.py`, `services/transcript/` | `POST /calls/ingest` creates Call + optional Transcript |
| **Transcript** | `services/transcript/` | Parse speakers, redact card data, stamp timings |
| **Check Library** | `models/check_library.py`, `seed/data/checks.py` | Versioned checks; `config.handler` names a registry fn |
| **Extraction** | `services/extraction/` | One FactStore per run; state tracker for corrections |
| **Scoring** | `services/scoring/engine.py` | Load → extract once → run every check → persist → gate |
| **Gate** | `services/gate/gate.py` | Pure function: FAIL → HELD, uncertainty → QA_REVIEW |
| **Reviews** | `services/scoring/review.py` | Queue + override that re-runs the gate |
| **Dashboard** | `services/scoring/dashboard.py` | Totals, FPY, top fails, repeat offences, agreement |
| **LLM** | `services/llm/` | OpenRouter JSON; `None` on failure |
| **Frontend** | `web/` | Home, Inbox, Leads, Playbooks, lead workspace |

---

## 4. Request Flow

### Score a lead

```
POST /api/v1/leads/{id}/score
  → run_scoring
       load Lead, latest Call, Transcript, Segments, Plan
       checks_effective_on(retailer, call.started_at)
       facts.extract(segments, crm)          # once per run
       for each CheckDefinition: handler(CheckContext)
       decide(lead_id, results)              # gate
       persist ScoringRun + CheckResults + AuditEvent
```

### Ingest a call

```
POST /api/v1/calls/ingest
  → Lead must already exist
  → Call (status ingested)
  → optional transcript_text → ingest_transcript
       parse → redact → estimate or ASR timings
  → AuditEvent call_ingested
```

### Human override

```
POST /api/v1/reviews/results/{id}/override
  { new_status, actor, reason }
  → apply_override
       require reason
       change result (method=human_override, confidence=1.0)
       re-run decide() on sibling results
       Override row (previous_gate, new_gate)
       AuditEvent check_result_overridden
```

### UI

```
Next.js (force-dynamic)
  → fetch NEXT_PUBLIC_API_URL (default http://127.0.0.1:8000)
  → /api/v1/dashboard, /leads, /reviews/queue, /checks
  → /leads/[id] loads results + transcript + audit + lead card
  → LeadWorkspace: jump to timestamp, play audio, override
```

---

## 5. Database Relationships

See [[04 Database/Schema]]. Short graph:

```
Retailer 1──* Plan
Retailer 1──* CheckDefinition (PK check_id + version)
Lead → Retailer, Plan?
Lead 1──* Call 1──* Transcript 1──* Segment
Lead 1──* ScoringRun 1──* CheckResult
CheckResult 1──* Override
Lead 1──* AuditEvent
```

### Notable fields

| Model | Notes |
|-------|--------|
| **Lead.crm_fields** | JSONB mock identity; factual checks compare spoken vs CRM |
| **Plan** | Rate card: intro/regular price, speeds, modem, min cost, development fee |
| **Segment** | `raw_text` stored, `redacted_text` is what the API returns |
| **CheckDefinition.config** | `{"handler": "money_match", "fact": "intro_price", ...}` |
| **CheckResult.evidence** | `[{segment_id, text, timestamp, start_ms, timing_source, ...}]` |
| **CheckResult.observation_trail** | Full history for stateful checks (delivery address) |
| **ScoringRun.sampled_for_human** | 5% calibration sample (hash of lead id by default) |

---

## 6. External Integrations

| Integration | Config | Used in |
|-------------|--------|---------|
| **PostgreSQL** | `DATABASE_URL` | SQLAlchemy session |
| **OpenRouter** | `OPENROUTER_API_KEY`, model | `services/llm/client.py` |
| **ElevenLabs** | `ELEVENLABS_API_KEY` | optional `scripts/generate_demo_audio.py` only |

No Stripe, Redis, S3, or auth system. CORS is open. Demo recordings are local files.

Env: `backend/.env.example` · Settings: `app/core/config.py`

---

## 7. AI Pipeline

Deterministic first, model last. See [[09 AI Context/Concepts/Deterministic first]].

```
Transcript segments
  → FactStore (normalizer: "forty two dollars and ninety" → 42.90, "MBBS" → Mbps)
  → state_tracker.resolve() for keys that change mid-call
  → Handlers
       script_match        (fuzzy + optional LLM on borderline)
       money/numeric/crm   (arithmetic / string)
       stateful_match      (latest assertion)
       no_card_data        (redaction findings)
       dead_air / interruptions  (NOT_APPLICABLE if timings/diarization weak)
       llm_behaviour       (objection handling, rapport)
  → CheckOutcome (status, confidence, evidence)
  → Gate
```

The model is consulted in **exactly three places**: borderline script match, uncertain extraction, behaviour checks. It never supplies the expected value (that comes from Plan / CRM / check config).

---

## 8. Gate Pipeline

See [[09 AI Context/Concepts/Gate order]]. Order is deliberate:

1. Any critical **FAIL** → `HELD` (known problem outranks doubt)
2. Any critical **REVIEW** or **ERROR** → `QA_REVIEW`
3. Any critical **PASS** below `confidence_threshold` (default 0.80) → `QA_REVIEW`
4. Any critical **NOT_APPLICABLE** → `QA_REVIEW` (unscorable is uncertainty, not a pass)
5. Else `AUTO_APPROVED`, of which ~5% become `HUMAN_SAMPLE` (hash of lead id)

Nothing uncertain auto-passes.

---

## 9. Seeded demo path

Retailer **FibreLink**, plan **Value 25 - NBN** ($42.90 intro / $72.90 regular / 25 Mbps / CF40 modem).

| Lead | What it is | Expected gate |
|------|------------|---------------|
| `3613790` | Real supplied call, messy ASR, delivery address changes, min cost stated two ways | **QA_REVIEW** |
| `3613791` | Same call with ambiguities resolved | **AUTO_APPROVED** |
| `3613792` | Quotes $35.90 vs $42.90 rate card; call date after disclaimer v2 | **HELD** |
| `3613793` / `3613794` | Same failure, same agent, inside seven days | **HELD** + repeat-offence flag |

---

## Gaps & Notes

1. **README vs disk:** Root README still says `qa-gate/`; the API folder is `backend/`.
2. **Audio proxy:** `web/app/api/audio/[leadId]/route.ts` still resolves `../qa-gate/demo/audio`. See [[07 Bugs/Audio proxy still points at qa-gate]].
3. **`web/DESIGN.md`:** Unrelated Miro brand tokens — not product design.
4. **No auth:** Dashboard is a single TL persona in the shell ("Priya Nair").
5. **`knowledge/`** is this Obsidian vault — not part of the FastAPI/Next runtime.

---

## Related knowledge folders

| Folder | Intended content |
|--------|------------------|
| `02 Architecture` | Diagrams, layering, data flow |
| `03 Modules` | Per-module deep dives |
| `04 Database` | Schema / enums |
| `05 APIs` | Endpoint reference |
| `06 Features` | Feature specs |
| `07 Bugs` | Known issues |
| `08 Decisions` | ADRs (the five decisions worth defending) |
| `09 AI Context` | AI-facing context packs |
| `10 Prompts` | Prompt library |
| `11 Meetings` | Meeting notes |
