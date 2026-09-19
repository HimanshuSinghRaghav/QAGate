---
type: architecture
status: current
updated: 2026-09-19
tags: [qa-gate]
---

# QA Gate — Architecture

> System architecture for the FastAPI scoring API + Next.js workspace.
> Companion to [[01 Project/Overview]].

---

## 1. High Level Diagram

```mermaid
flowchart TB
  subgraph Clients
    UI["Next.js dashboard<br/>Home · Inbox · Leads · Playbooks"]
    Dialler["Dialler / ingest client"]
  end

  subgraph API["FastAPI (app.main)"]
    Routes["/api/v1<br/>ingest · score · checks · reviews · dashboard"]
    Engine["Scoring engine"]
    Handlers["Check handlers<br/>verbatim · factual · behaviour"]
    Gate["Gate (pure)"]
  end

  subgraph Data
    PG[("PostgreSQL :5433")]
    Audio["demo/audio/*.mp3"]
  end

  subgraph External
    OR[OpenRouter LLM]
    EL[ElevenLabs TTS<br/>demo generation only]
  end

  Dialler -->|POST /calls/ingest| Routes
  UI -->|NEXT_PUBLIC_API_URL| Routes
  UI -->|/api/audio/:leadId| Audio
  Routes --> Engine
  Engine --> Handlers
  Engine --> Gate
  Engine --> PG
  Handlers -.->|borderline / behaviour| OR
  EL -.->|scripts only| Audio
```

### Layered view

```mermaid
flowchart LR
  L1["Transport<br/>HTTP"]
  L2["Routes<br/>FastAPI + Pydantic"]
  L3["Services<br/>ingest · extract · score · review · present"]
  L4["Pure core<br/>handlers · gate · normalizer"]
  L5["Postgres + optional OpenRouter"]

  L1 --> L2 --> L3 --> L4 --> L5
```

The overview (`backend/overview/1.md`) drew six product modules. We kept that split in code:

```
1. Ingestion
2. Transcript
3. Check Library
4. Scoring Engine
5. Gate / Review Workflow
6. Dashboard
```

Plus extraction (the piece overview/2.md added after reading the messy transcript): **state tracker + normalizer**.

---

## 2. Module Dependency Graph

Arrows mean **imports** (A → B = A depends on B).

```mermaid
flowchart TB
  Main[app.main] --> Router[api/v1/router]
  Router --> Ingest[ingestion]
  Router --> ScoreAPI[scoring API]
  Router --> ChecksAPI[checks API]
  Router --> ReviewAPI[reviews API]
  Router --> DashAPI[dashboard API]

  ScoreAPI --> Engine[scoring.engine]
  ReviewAPI --> Review[scoring.review]
  DashAPI --> Dash[scoring.dashboard]
  ChecksAPI --> Resolver[version_resolver]

  Engine --> Facts[extraction.facts]
  Engine --> Resolver
  Engine --> Registry[checks.registry]
  Engine --> Gate[gate.decide]
  Facts --> Normalizer[extraction.normalizer]
  Facts --> State[extraction.state_tracker]
  Registry --> Verbatim
  Registry --> Factual
  Registry --> Behaviour
  Verbatim -.-> LLM[llm.client]
  Behaviour -.-> LLM
  Review --> Gate
  Ingest --> Transcript[transcript.service]
  Transcript --> Redact[transcript.redaction]
  Transcript --> Timing[transcript.timing]
```

### Dependency notes

| Pattern | Why |
|---------|-----|
| Handlers are a registry, not a class hierarchy | Adding a check is a `config.handler` string |
| Extraction runs once per scoring run | Two checks cannot disagree about what the call said |
| Gate is a pure function of `(lead_id, results)` | Overrides re-run the same function |
| LLM is a leaf | Returns `None`; callers degrade to REVIEW |
| `present.py` sits at the API edge | Human labels without polluting handlers |

### Hot path (runtime critical)

```mermaid
flowchart LR
  Score[POST /leads/:id/score] --> Engine
  Engine --> Extract[facts.extract]
  Engine --> Each[handler per check]
  Each --> Outcome[CheckOutcome]
  Engine --> Gate
  Gate --> Persist[ScoringRun + CheckResult + AuditEvent]
```

---

## 3. Mermaid — Domain Model

```mermaid
erDiagram
  RETAILER ||--o{ PLAN : sells
  RETAILER ||--o{ CHECK_DEFINITION : library
  LEAD }o--|| RETAILER : belongs
  LEAD }o--o| PLAN : quoted
  LEAD ||--o{ CALL : has
  CALL ||--o{ TRANSCRIPT : transcribed
  TRANSCRIPT ||--o{ SEGMENT : lines
  LEAD ||--o{ SCORING_RUN : scored
  SCORING_RUN ||--o{ CHECK_RESULT : results
  CHECK_RESULT ||--o{ OVERRIDE : overturned
  LEAD ||--o{ AUDIT_EVENT : trail
```

---

## 4. Data Flow

### 4.1 Score (end-to-end)

```mermaid
sequenceDiagram
  participant UI as Next.js
  participant API as scoring.py
  participant E as engine.run_scoring
  participant F as facts.extract
  participant H as handler
  participant G as gate.decide
  participant DB as PostgreSQL

  UI->>API: POST /leads/{id}/score
  API->>E: run_scoring(db, lead_id)
  E->>DB: Lead, Call, Transcript, Segments, Plan
  E->>DB: checks_effective_on(call_date)
  E->>F: extract(segments, crm)
  loop each CheckDefinition
    E->>H: fn(CheckContext)
    H-->>E: CheckOutcome
  end
  E->>G: decide(lead_id, results)
  G-->>E: GateOutcome
  E->>DB: ScoringRun, CheckResults, AuditEvent
  API-->>UI: ScoredLeadOut (critical / non_critical / unscorable + case)
```

### 4.2 Ingest

```mermaid
sequenceDiagram
  participant C as Dialler
  participant I as ingestion.py
  participant T as ingest_transcript
  participant DB as PostgreSQL

  C->>I: POST /calls/ingest
  I->>DB: get Lead (404 if missing)
  I->>DB: insert Call
  opt transcript_text present
    I->>T: parse → redact → time
    T->>DB: Transcript + Segments
  end
  I->>DB: AuditEvent call_ingested
  I-->>C: call_id, transcript_id, timing_source
```

### 4.3 Override

```mermaid
sequenceDiagram
  participant R as Reviewer
  participant API as reviews.py
  participant O as apply_override
  participant G as gate.decide
  participant DB as PostgreSQL

  R->>API: POST /reviews/results/{id}/override
  API->>O: new_status, actor, reason
  O-->>API: ReviewError if reason empty
  O->>DB: update CheckResult
  O->>G: decide(siblings)
  O->>DB: ScoringRun gate fields, Override, AuditEvent
  API-->>R: previous_gate, new_gate
```

### 4.4 Lead workspace (UI)

```mermaid
flowchart LR
  Page["/leads/[id]"] --> Fetch["results + transcript + audit + lead"]
  Fetch --> WS[LeadWorkspace]
  WS --> Checks[Critical / coaching / unscorable]
  WS --> Evidence[Expected vs said + trail]
  WS --> Audio["Jump to start_ms · /api/audio/:leadId"]
  WS --> Override["POST override → refresh bundle"]
```

---

## 5. Folder Explanation

```
qt-gate/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI + CORS + /health
│   │   ├── core/                   # config, db session, enums
│   │   ├── models/                 # SQLAlchemy entities
│   │   ├── schemas/                # Pydantic contracts
│   │   ├── api/v1/                 # HTTP surface
│   │   ├── services/
│   │   │   ├── transcript/         # parser, redaction, timing, ingest
│   │   │   ├── extraction/         # normalizer, facts, state_tracker
│   │   │   ├── checks/             # registry + three families
│   │   │   ├── llm/                # OpenRouter JSON client
│   │   │   ├── scoring/            # engine, versions, review, dashboard
│   │   │   ├── gate/               # decide()
│   │   │   └── present.py          # UI labels
│   │   └── seed/                   # fixtures + CLI
│   ├── overview/                   # hackathon briefs (not runtime)
│   ├── scripts/                    # dry_run, demo audio, verify sync
│   └── tests/
├── web/
│   ├── app/                        # pages + audio proxy
│   ├── components/                 # shell, workspace, UI
│   └── lib/                        # api.ts, types.ts
└── knowledge/                      # this vault
```

---

## 6. Best Practices

### Architecture principles already in use

1. **Ingestion before scoring** — `ScoringError` if no call/transcript/segments.
2. **Extract once** — `FactStore` is shared; handlers do not re-parse the call.
3. **Handlers report, gate decides** — status/confidence/evidence in, decision out.
4. **Deterministic first, model last** — [[08 Decisions/ADR-001 Deterministic first model last]].
5. **Fail closed on LLM** — [[08 Decisions/ADR-002 Unavailable LLM cannot ship a sale]].
6. **Latest assertion wins** — [[08 Decisions/ADR-003 Conversation state not first occurrence]].
7. **Unscorable ≠ fail** — [[08 Decisions/ADR-004 Missing input is NOT_APPLICABLE]].
8. **Version by call date** — [[08 Decisions/ADR-005 Call date picks check version]].
9. **Identify, do not rewrite** — no auto-correction of the sale.
10. **Overrides are first-class** — reason required; gate re-run; audit written.

### Recommended practices when extending

| Area | Do | Avoid |
|------|----|-------|
| New check | Row in `seed/data/checks.py` + `@handler("name")` | Hardcoding expected values in the handler |
| New fact | Add extractor in `facts.py` + normalizer if ASR-noisy | Sending the raw transcript to the LLM for a price |
| New API | Pydantic schema in `schemas/common.py` | Returning `Segment.raw_text` |
| New UI page | Fetch via `web/lib/api.ts`, `force-dynamic` | Client-side caching of scores |
| Timings | Prefer ASR payload; always set `timing_source` | Presenting estimates as measurements |
| Docs | Update `knowledge/` when modules change | Trusting README paths (`qa-gate/` vs `backend/`) |

### Cross-cutting concerns checklist

- [ ] Handler never writes to DB
- [ ] Gate never reads transcript
- [ ] Evidence includes timestamp + `timing_source`
- [ ] LLM failure path returns REVIEW
- [ ] Override has a reason and re-runs `decide()`
- [ ] Env vars added to `Settings` + `.env.example`

---

## Related

- [[01 Project/Overview]] — product / judging / seed leads
- `backend/README.md` — setup
- Swagger — http://localhost:8000/docs
