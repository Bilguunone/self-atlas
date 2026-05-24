---
id: note:examples-demo-vault-readme
schema_version: 1
type: index
status: active
sensitivity: normal
confidence: confirmed
created: 2026-05-21
updated: 2026-05-21
aliases: []
tags:
  - self-atlas/demo
links:
  - "[[00 System/Home]]"
sources:
  - "90 Sources/Captures/2026-05-21-demo-answer"
---

# Demo Vault

This is a tiny fictional Self Atlas vault. It exists so contributors can test Pulse, Thread Walk, graph export, timeline export, question refresh, capture review, and privacy behavior without touching anyone's real life.

Names, projects, relationships, and events here are invented. Mira, Ari, River, and Lumen Sketch are fixtures, not secret lore.

Useful demos:

- `python3 scripts/self_atlas.py pulse --vault examples/demo-vault --include-sensitive`
- `python3 scripts/self_atlas.py thread-walk --vault examples/demo-vault --query "export motion" --include-sensitive`
- `python3 scripts/self_atlas.py answer-context --vault examples/demo-vault --query "what is Lumen Sketch proof moment" --include-sensitive`
- `python3 scripts/self_atlas.py capture-review --vault examples/demo-vault --source "90 Sources/Captures/2026-05-21-demo-answer"`
- `python3 scripts/self_atlas.py apply-review --vault examples/demo-vault --source "90 Sources/Captures/2026-05-21-demo-answer"`
- `python3 scripts/self_atlas.py export-preview --vault examples/demo-vault`

`exports/` contains fixture JSON for app/UI development.
