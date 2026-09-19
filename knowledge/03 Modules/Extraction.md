---
type: module
status: current
module: extraction
updated: 2026-09-19
tags: [backend]
---

# Extraction Module

> Path: `backend/app/services/extraction/`  
> Related: [[09 AI Context/Concepts/State tracker]], [[09 AI Context/Concepts/Deterministic first]]

---

## Purpose

Turn messy ASR into a **FactStore**: candidate observations, each bound to a segment and timestamp. Nothing here decides PASS or FAIL. Checks compare observations to CRM and the rate card.

This is the module overview/2.md added after reading the FibreLink transcript: do not first-occurrence match; normalize "forty two dollars and ninety" and "twenty five MBBS"; track delivery-address corrections.

---

## Services

| File | Role |
|------|------|
| `normalizer.py` | Spoken money, Mbps, months, modem aliases, month-to-month |
| `facts.py` | Scan segments → `Observation`s keyed (`intro_price`, `email`, `delivery_address`, …) |
| `state_tracker.py` | `resolve(store, key)` → latest assertion, conflict flag, dropped confidence |

## Flow

```
segments + crm
  → extract CRM mentions, money (context window), speeds (after-the-number), enums
  → FactStore
  → resolve() per stateful key at check time
```

Extraction runs **once per scoring run** (`engine.py`). Two checks cannot disagree about what the call said.

## Anti-pattern

```js
if (text.includes("$42.90")) pass()
```

Use extract → normalize → compare instead. Keep the **raw** fixture messy.
