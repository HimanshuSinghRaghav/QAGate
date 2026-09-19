---
type: module
status: current
module: transcript
updated: 2026-09-19
tags: [backend]
---

# Transcript Module

> Path: `backend/app/services/transcript/`  
> Related: [[03 Modules/Ingestion]], [[09 AI Context/Concepts/Card redaction]], [[09 AI Context/Concepts/Timing sources]]

---

## Purpose

Turn raw call text into the artefact evidence can point at: speaker-labelled, redacted, timed **segments**. `raw_text` is kept for extraction; `redacted_text` is the only text the API/UI ever sees.

Overview/2.md: the supplied transcript is messy on purpose (MBBS, CF40 → "p s forty", no timestamps in the PDF). Normalization happens **after** storage, in extraction — we do not clean the fixture.

---

## Entry points

- Called from ingest and from seed (`app/seed/run.py`).
- HTTP read: `GET /api/v1/leads/{id}/transcript`.

## Services

| File | Role |
|------|------|
| `parser.py` | Split speaker turns; flag whether diarization looks reliable |
| `redaction.py` | Luhn card numbers, spoken-digit runs; return safe text **and** findings |
| `timing.py` | `apply_asr_timings` or `estimate_timings` (word-count, labelled `estimated`) |
| `service.py` | Orchestrate the three |

## Flow

```
raw_text
  → parse(speakers, turns)
  → timings? ASR spans : estimated spans
  → redact each segment
  → Transcript + Segment rows
```

`timing_source` is stamped on the transcript **and** every evidence blob. Nothing presents an estimate as an ASR measurement.

## Related

- Dead air / interruptions return `NOT_APPLICABLE` when timings are estimated or diarization is unreliable. See [[08 Decisions/ADR-004 Missing input is NOT_APPLICABLE]].
