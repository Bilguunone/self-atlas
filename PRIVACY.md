# Privacy

Self Atlas is local-first. The repository contains the memory engine, templates, CLI, tests, and fake examples. It must not contain a real personal vault.

## What belongs in this repo

- plugin code and CLI helpers
- schemas, templates, migrations, exports, reports, and tests
- fictional demo vaults under `examples/`
- documentation for installing and developing the system

## What does not belong here

- real Markdown vaults
- raw captures from a real person
- generated graph or timeline exports from a real vault
- health, financial, relationship, immigration, family, or other private notes
- absolute local filesystem paths
- API keys, tokens, or environment files

## Before publishing

Run:

```bash
cp .privacy-patterns.example .privacy-patterns  # optional, local-only
python3 scripts/public_release_check.py
python3 tests/test_self_atlas.py
```

Put real denylist terms only in `.privacy-patterns`. That file is ignored by Git. The committed example file must stay synthetic.

Then do one last manual search for private names, project names, places, and source-capture text. Automation helps; it does not replace taste or paranoia.
