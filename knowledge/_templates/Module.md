---
type: module
status: current
module: <% tp.system.prompt('module key (e.g., scoring, gate, ingestion)') %>
updated: <% tp.date.now("YYYY-MM-DD") %>
tags: [backend]
---

# <% tp.system.prompt('Module display name (e.g., Scoring)') %> Module

> Path: <% tp.system.prompt('Path in repo (e.g., backend/app/services/scoring)') %>
> Related: <% tp.system.prompt('Related vault pages (wikilinks), comma-separated') %>

---

## Purpose

One paragraph: what this module does and why it exists.

## Entry points

Describe HTTP routes (method + path) and any scripts/CLI if present.

## Services

List service(s) and their main responsibilities and key methods.

## Dependencies

Imports, external APIs, and key models.

## Schemas

List request/response schema files and what they validate/shape.

## Flow

Step-by-step happy path for the main journey of this module.

## Related Modules

Use a small table: imported by / imports.

## Mermaid Diagram

Add one Mermaid diagram that matches the module’s main flow.

## Future Improvements

3-5 concrete improvements (tests, security hardening, cleanup, performance, missing APIs).
