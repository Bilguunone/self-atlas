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

This is a tiny fictional Self Atlas vault. It exists so contributors can test Pulse, Thread Walk, insight expansion commands, graph export, timeline export, question refresh, capture review, and privacy behavior without touching anyone's real life.

Names, projects, relationships, and events here are invented. Mira, Ari, River, and Lumen Sketch are fixtures, not secret lore.

Useful demos:

- `python3 scripts/self_atlas.py pulse --vault examples/demo-vault --include-sensitive`
- `python3 scripts/self_atlas.py thread-walk --vault examples/demo-vault --query "export motion" --include-sensitive`
- `python3 scripts/self_atlas.py answer-context --vault examples/demo-vault --query "what is Lumen Sketch proof moment" --include-sensitive`
- `python3 scripts/self_atlas.py life-lenses --vault examples/demo-vault`
- `python3 scripts/self_atlas.py open-loop-radar --vault examples/demo-vault --include-sensitive`
- `python3 scripts/self_atlas.py contradictions --vault examples/demo-vault --include-sensitive`
- `python3 scripts/self_atlas.py decision-council --vault examples/demo-vault --question "should Lumen Sketch focus on export motion or onboarding copy" --options "Export motion|Onboarding copy" --include-sensitive`
- `python3 scripts/self_atlas.py time-travel --vault examples/demo-vault --include-sensitive`
- `python3 scripts/self_atlas.py share-capsule --vault examples/demo-vault --query "export motion" --lens taste --json`
- `python3 scripts/self_atlas.py taste-genome --vault examples/demo-vault`
- `python3 scripts/self_atlas.py proof-engine --vault examples/demo-vault --claim "Lumen Sketch proof moment is export motion" --include-sensitive`
- `python3 scripts/self_atlas.py belief-versioning --vault examples/demo-vault --query "export motion" --include-sensitive`
- `python3 scripts/self_atlas.py taste-autopilot --vault examples/demo-vault --text "A generic productivity dashboard with onboarding copy and no export proof."`
- `python3 scripts/self_atlas.py decision-replay --vault examples/demo-vault --decision "export motion" --include-sensitive`
- `python3 scripts/self_atlas.py future-self --vault examples/demo-vault --query "Lumen Sketch" --include-sensitive`
- `python3 scripts/self_atlas.py artifact-import --vault examples/demo-vault --source https://example.com/lumen-sketch-reference --domain taste`
- `python3 scripts/self_atlas.py capture-review --vault examples/demo-vault --source "90 Sources/Captures/2026-05-21-demo-answer"`
- `python3 scripts/self_atlas.py apply-review --vault examples/demo-vault --source "90 Sources/Captures/2026-05-21-demo-answer"`
- `python3 scripts/self_atlas.py export-preview --vault examples/demo-vault`

`exports/` contains fixture JSON for app/UI development.
