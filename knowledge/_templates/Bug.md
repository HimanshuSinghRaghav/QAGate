---
type: bug
status: open
severity: <% tp.system.suggester('severity', ['blocker', 'major', 'minor', 'low']) %>
updated: <% tp.date.now("YYYY-MM-DD") %>
tags: [bug]
---

# Bug: <% tp.system.prompt('Short title') %>

## Symptom

What you observed (error message, behavior, screenshots, logs).

## Repro

Steps to reproduce (inputs, endpoint, environment).

## Root cause (suspected)

What’s likely wrong, with links to the relevant code/docs.

## Fix / Workaround

What you changed or will change, plus mitigation steps if not fixed yet.

## Related

- [[03 Modules/<% tp.system.prompt('Related module name') %>]]
- Links, PRs, commit hashes (if any)

## Notes

Any additional context that helps future debugging.
