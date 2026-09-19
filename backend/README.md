# QA Gate — score the sale before it ships

Automated QA scoring for sales calls. A transcript lands against a Lead, every check
in the retailer's versioned library runs against it, each result carries the
transcript line and timestamp that produced it, and a gate decides whether the sale
auto-submits, is held for the TL, or goes to QA.

**Stack:** Python 3.11+ · FastAPI · PostgreSQL · SQLAlchemy 2.0 · OpenRouter · Next.js (sibling `web/` UI).

**Layout** (this backend lives next to the frontend):

```
qt-gate/
  qa-gate/   # this repo — API, seed, scripts, demo audio
  web/       # Next.js UI (sibling folder, not inside this repo)
```

| Service | URL |
|---|---|
| API + Swagger | http://localhost:8000/docs |
| Web UI | http://localhost:3000 |
| Postgres | `localhost:5433` |

---

## Prerequisites

- **Docker** — Postgres via `docker compose`
- **Python 3.11+** (3.12/3.14 fine)
- **Node.js 20+** and npm — frontend
- Optional: **OpenRouter** API key for the LLM semantic layer (works without it; more calls go to QA)
- Optional: **ElevenLabs** API key only if you want to regenerate demo call audio

---

## Setup from scratch

Do this once on a clean machine. Two terminals after that: one for the API, one for the UI.

### 1. Enter the workspace

```bash
cd qt-gate/qa-gate          # backend
# frontend is the sibling: ../web
```

### 2. Backend (API + DB)

```bash
# Postgres on port 5433
docker compose up -d db

# Isolated Python env
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Env — defaults match docker-compose; LLM key is optional
cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY if you have one.
# Or set LLM_ENABLED=false to force deterministic-only scoring.

# Create tables, load fixtures, score every seeded lead
python -m app.seed.run

# API (keep this running)
uvicorn app.main:app --reload --port 8000
```

Check: http://localhost:8000/health and http://localhost:8000/docs

**Makefile shortcuts** (from repo root, with venv active):

```bash
make db        # docker compose up -d db
make install   # pip install -r requirements.txt
make seed      # python -m app.seed.run
make run       # uvicorn on :8000
make reset     # drop schema and re-seed
```

### 3. Frontend (Next.js) — sibling `../web`

In a **second** terminal:

```bash
cd ../web                   # from qa-gate/, or: cd qt-gate/web
npm install

cp .env.example .env.local
# NEXT_PUBLIC_API_URL=http://127.0.0.1:8000   # default; change only if API is elsewhere

npm run dev
```

Open http://localhost:3000 — the UI talks to the API at `NEXT_PUBLIC_API_URL`.
Demo mp3s are served from `../qa-gate/demo/audio/`.

### 4. Optional — demo call audio

Playback in the lead workspace reads `demo/audio/<leadId>.mp3` (gitignored). Without audio the rest of the product still works; only the player is empty. See [Scripts](#scripts) below to generate and verify recordings.

---

## Day-to-day

```bash
# terminal 1 — API
source venv/bin/activate
docker compose up -d db          # if not already up
uvicorn app.main:app --reload --port 8000

# terminal 2 — UI (sibling folder)
cd ../web && npm run dev
```

---

## Seed

Loads retailer, plan, check library, every synthetic lead + call + transcript, then scores them. Idempotent: re-running replaces fixture rows instead of duplicating them.

If `demo/audio/<lead>.timings.json` exists, seed stamps the transcript with real ElevenLabs timings; otherwise it falls back to estimated word-count spans.

```bash
source venv/bin/activate

python -m app.seed.run              # create tables, load fixtures, score every lead
python -m app.seed.run --drop       # drop schema first, then full re-seed
python -m app.seed.run --no-score   # fixtures only (skip scoring engine)
make reset                          # same as --drop
```

Fixture sources under `app/seed/data/`:

| File | What it holds |
|---|---|
| `leads.py` | retailers, plan, lead specs + CRM fields + call metadata |
| `transcript.py` | raw call scripts per lead |
| `checks.py` | versioned check library (handlers + effective windows) |
| `audio.py` | loads `demo/audio/*.timings.json` when present |
| `identity.py` | agent / TL ids used by the fixtures |

---

## Scripts

All run from the **repo root** with the venv active (`source venv/bin/activate`).

### `scripts/dry_run.py` — no Postgres, no LLM

Full pipeline in memory: parse → redact → extract → every check handler → gate. LLM forced off so you see the deterministic floor.

```bash
python scripts/dry_run.py                  # lead 3613790 (supplied call)
python scripts/dry_run.py --lead 3613792   # held sale
python scripts/dry_run.py --facts          # dump extracted fact store
```

### `scripts/generate_demo_audio.py` — ElevenLabs TTS + timings

Needs `ELEVENLABS_API_KEY` in `.env`. Writes `demo/audio/{lead}.mp3` and `demo/audio/{lead}.timings.json`. After generating, **re-seed** so the DB picks up the real timings.

```bash
python scripts/generate_demo_audio.py --list-voices   # pick voice ids
python scripts/generate_demo_audio.py                 # all unique calls
python scripts/generate_demo_audio.py --lead 3613790  # one lead
python scripts/generate_demo_audio.py --force         # overwrite existing mp3/timings
python -m app.seed.run --drop                         # reload DB with new timings
```

Optional voice overrides in `.env`: `ELEVENLABS_HELEN_VOICE_ID`, `ELEVENLABS_MARCO_VOICE_ID`.

### `scripts/verify_audio_sync.py` — prove timestamps match the mp3

Checks duration drift, segment→audio mapping, and that sampled segments open on speech (not silence / mid-word). Run after generating audio.

```bash
python scripts/verify_audio_sync.py
python scripts/verify_audio_sync.py --lead 3613790 --sample 40
```

### Tests

```bash
pytest -q
```

---

## The four seeded leads

| Lead | What it is | Gate |
|---|---|---|
| `3613790` | the real supplied call, untouched | **QA_REVIEW** — delivery address changed mid-call, contract term mangled by ASR, minimum cost stated two ways |
| `3613791` | same call with those ambiguities resolved | **AUTO_APPROVED** |
| `3613792` | agent quotes $35.90 against a $42.90 rate card, called after the disclaimer wording changed | **HELD** |
| `3613793` / `3613794` | same failure, same agent, inside seven days | **HELD** + repeat-offence flag |

---

## Module map

```
app/                 FastAPI backend
  core/              config, db session, shared enums
  models/            Retailer, Plan, Lead, Call, Transcript, Segment,
                     CheckDefinition, ScoringRun, CheckResult, Override, AuditEvent
  schemas/           request/response contracts
  api/v1/            ingestion · scoring · checks · reviews · dashboard
  services/
    transcript/      parser · redaction · timing · ingestion
    extraction/      normalizer · facts · state_tracker
    checks/          base (contract + registry) · verbatim · factual · behaviour
    llm/             OpenRouter client · prompts
    scoring/         engine · version_resolver · review · dashboard
    gate/            gate
  seed/              fixtures derived from the supplied call
    data/            leads · transcripts · checks · audio timings loader
    run.py           CLI: --drop · --no-score
scripts/
  dry_run.py             in-memory pipeline (no DB / no LLM)
  generate_demo_audio.py ElevenLabs mp3 + timings.json
  verify_audio_sync.py   assert transcript timestamps match audio
demo/audio/          optional call recordings (<leadId>.mp3 + .timings.json)

../web/              Next.js UI (sibling of this backend)
  app/               routes (audio proxy → ../qa-gate/demo/audio)
  components/        lead workspace, review UI
  lib/               API client → NEXT_PUBLIC_API_URL
```

Each layer only knows about the one below it. Check handlers never touch the
database and never decide the gate; the gate never re-reads the transcript.

---

## Five decisions worth defending

**1. Deterministic first, model last.** Prices, speeds, dates, emails and CRM
comparisons are arithmetic and string work — `services/extraction/normalizer.py`.
The model is consulted in exactly three places: a borderline script match, an
extraction that came out uncertain, and behaviour checks. It can move a result
between PASS, FAIL and REVIEW; it can never supply the expected value.

**2. An unavailable model cannot ship a sale.** Every LLM path returns `None` on
failure and the caller degrades to REVIEW, never to PASS. Run with
`LLM_ENABLED=false` and the system still scores — with more calls routed to QA,
which is the correct direction to fail.

**3. Conversation state, not first occurrence.** The delivery address in the
supplied call is asserted four times and changes. `state_tracker.resolve()` takes
the latest assertion, flags the conflict, drops confidence, and hands the reviewer
the full trail of what was said when.

**4. Missing input is `NOT_APPLICABLE`, not `FAIL`.** Dead air cannot be measured
from estimated timestamps. Interruptions cannot be counted when the customer's
replies are folded into the agent's turns. Both say so instead of inventing a
finding. This is the guardrails criterion.

**5. The call date picks the check version.** `recording_disclaimer` is seeded at
v1 and v2 with different effective windows. Lead 3613790 (15 Sep) scores against v1
and passes; lead 3613792 (17 Sep) scores against v2 and does not. Same words,
different answer, because the rules changed in between.

---

## Where the timestamps come from

The supplied transcript has no timings. Traceability needs them, so
`services/transcript/timing.py` estimates spans from word counts and stamps every
segment and every piece of evidence `timing_source: "estimated"`. Nothing in the
system presents an estimate as an ASR measurement. Swap `estimate_timings` for
`apply_asr_timings` when the real payload arrives and nothing downstream changes.

## Guardrails

- Card numbers are Luhn-validated, redacted before storage, and the violation is
  still flagged. The API only ever returns `redacted_text`; `raw_text` never leaves
  the database.
- The system reports what failed and where. It does not rewrite the sale, correct
  the agent, or suggest what to say.
- Overrides require a reason, record the before and after gate state, and re-run the
  gate rather than setting it by hand.
- 5% of clean calls are sampled to a human. Sampling is a hash of the Lead ID, so
  the demo is reproducible; set `DETERMINISTIC_SAMPLING=false` for real traffic.

---

## Demo path

```bash
curl -s -X POST localhost:8000/api/v1/leads/3613790/score | jq
curl -s localhost:8000/api/v1/leads/3613790/transcript | jq '.segments[0:5]'
curl -s "localhost:8000/api/v1/checks/effective?retailer_id=retailer_1&at=2026-09-15T10:00:00Z" | jq
curl -s "localhost:8000/api/v1/checks/effective?retailer_id=retailer_1&at=2026-09-17T09:15:00Z" | jq
curl -s -X POST localhost:8000/api/v1/reviews/results/<result_id>/override \
  -H 'content-type: application/json' \
  -d '{"new_status":"PASS","actor":"auditor_12","reason":"Customer confirmed the delivery address verbally at 16:24."}' | jq
curl -s localhost:8000/api/v1/dashboard | jq
curl -s localhost:8000/api/v1/leads/3613790/audit | jq
```

The override response returns `previous_gate` and `new_gate` so you can show the
sale moving from held to approved, with the reason recorded against it.

## Swapping in the real data

1. Replace `app/seed/data/checks.py` with the retailer's check-library export. Each
   row needs a `config.handler` naming one of `GET /api/v1/checks/handlers`.
2. Point `Plan` at the real rate card and `Lead.crm_fields` at the real CRM record.
3. Post real calls to `POST /api/v1/calls/ingest` with `transcript_text`, or wire the
   transcription callback to `services/transcript/service.ingest_transcript`.

Nothing else changes.
