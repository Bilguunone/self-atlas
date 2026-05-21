# Self Atlas

Self Atlas is a Codex plugin for building a private Markdown life graph about a person: identity, family, work, taste, health context, mindset, hobbies, obsessions, values, projects, desires, and the weird little patterns that actually make someone legible.

The point is not to make a giant questionnaire. That would be spiritually punishable. The point is a small-loop memory system:

- ask useful question batches without turning into a fifty-question hostage situation
- include compact example answers so questions are easy to answer fast
- turn one answer into multiple connected notes
- start with a minimal vault and grow folders only when answers need them
- use wiki-style links, tags, aliases, maps of content, and backlinks
- search by breadcrumbs before answering
- keep sensitive context local, explicit, and marked

## Layout

- `skills/self-atlas/SKILL.md` teaches Codex how to use the vault.
- `scripts/self_atlas.py` is the thin CLI entrypoint.
- `scripts/self_atlas_lib/` contains the real implementation modules: vault IO, templates, questions, extraction, reports, migrations, export, and CLI wiring.
- `scripts/install_local_plugin.py` can copy the repo into a local `~/plugins/self-atlas` folder and generate local-only plugin metadata for private Codex setups.
- `assets/templates/` contains the starter Markdown template library.
- `examples/demo-vault/` contains fictional fixture content for demos and tests.

## Public Boundary

This repo is the system, not the diary. It should contain code, templates, tests, docs, and fictional examples only. A real vault belongs outside Git.

Good:

- `scripts/`
- `assets/templates/`
- `skills/self-atlas/SKILL.md`
- `examples/demo-vault/`
- fake fixture data

Bad:

- real source captures
- real relationship, health, money, family, or identity notes
- generated graph/timeline exports from a private vault
- absolute local paths
- API keys or environment files

## Quick Start

From a fresh clone:

```bash
git clone https://github.com/Bilguunone/self-atlas.git
cd self-atlas

DEMO_VAULT="$PWD/examples/demo-vault"

python3 scripts/self_atlas.py validate-links --vault "$DEMO_VAULT"
python3 scripts/self_atlas.py schema-report --vault "$DEMO_VAULT"
python3 scripts/self_atlas.py suggest-question --vault "$DEMO_VAULT" --count 5 --with-examples
python3 scripts/self_atlas.py refresh-questions --vault "$DEMO_VAULT" --mode mixed --count 8 --with-examples
python3 scripts/self_atlas.py graph-summary --vault "$DEMO_VAULT"
python3 scripts/self_atlas.py timeline-report --vault "$DEMO_VAULT"
python3 scripts/self_atlas.py export-json --vault "$DEMO_VAULT" --pretty
```

For a personal vault, choose a folder outside this repo:

```bash
VAULT="$HOME/Documents/Self-Atlas-Vault"

python3 scripts/self_atlas.py ensure --vault "$VAULT" --yes
python3 scripts/self_atlas.py sync-templates --vault "$VAULT"
python3 scripts/self_atlas.py suggest-question --vault "$VAULT" --count 5 --with-examples
```

To install it as a local Codex plugin instead of running from the clone:

```bash
python3 scripts/install_local_plugin.py --force
```

That copies the repo to `~/plugins/self-atlas`, generates local-only plugin metadata, and registers it in the local Codex marketplace. Your personal vault still stays outside the repo.

Open the vault in any Markdown editor. Obsidian can visualize the links today, but the source is a plain Markdown graph that can power a dedicated Self Atlas visualizer later. `init` creates the minimal core by default; `init --full` creates the larger starter scaffold. `list-templates` shows the current template library, and `sync-templates` copies missing templates into `00 System/Templates` without overwriting existing files unless `--overwrite` is passed.

## Development Checks

Before publishing or opening a pull request:

```bash
python3 scripts/public_release_check.py
python3 tests/test_self_atlas.py
```

The report commands are read-only. They do not change existing Atlas content. `source-hygiene` reports oversized captures, unextracted sources, Source Log gaps, and archive pressure so `90 Sources/Captures/` can grow without turning into a junk drawer. `extract-plan` turns one raw capture into a typed, reviewable plan: `RawCapture -> MemoryCandidate[] -> DurableNotePatch[] -> LinkPatch[] -> ReviewFlags`. It reads both current headings (`Extracted Notes`, `Follow-Up Threads`) and legacy headings (`Derived Notes`, `Open Questions`), and each memory candidate and durable patch carries `SourceEvidence` with the source path, section, line hint, raw excerpt, confidence, and sensitivity. It proposes note appends, source-lineage links, and review flags without writing them. `QuestionTemplate` drives the question layer with `domain`, `intent`, `why`, `hint`, `examples`, `target_note_types`, `sensitivity`, and `evidence_needed`, so prompts ask for dates, names, numbers, links, examples, values, places, and artifacts instead of mush. `timeline-report` and `timeline-export` build an app-ready life timeline from timeline notes and dated/era bullets: items, derived periods, threads, rough-date precision, pressure, emotional charge, turning points, linked people/projects/places, and sources. `timeline-export --exclude-sensitive` drops private/health/financial/intimate notes and skips items that point at hidden notes. `suggest-question` reads Question Queue and Open Threads before template fallback, rotates domains, and caps batches at eight. `refresh-questions` previews by default and can shuffle existing queue items, regenerate from the template library, or mix both; with `--apply`, it rewrites `00 System/Question Queue.md`, bumps `updated`, and preserves rotated-out questions under `Question Refresh History`. `sync-templates` only writes template files under `00 System/Templates`. `enrich-thin-notes` is report-only by default; with `--apply`, it appends targeted questions to `00 System/Question Queue.md` without inventing facts. `migrate-source-fields` is dry-run by default; with `--apply`, it derives frontmatter `sources` from existing source-capture links and creates a backup before writing. `migrate-relationship-fields` is dry-run by default; with `--apply`, it adds typed relationship frontmatter to person notes so love, friends, family, mentors, and collaborators export as different graph semantics. `migrate-app-fields` is dry-run by default; with `--apply`, it adds deterministic `id` and `schema_version` fields to note frontmatter and leaves note bodies and existing memory values alone. `export-json` reads the vault without modifying it; by default it excludes private/health/financial/intimate notes and omits note bodies. Use `--include-body` and `--include-sensitive` only for private, local exports you do not intend to share.

## Plugin Behavior

When summoned, Codex should:

1. Find the vault or ask to create a minimal one before saving.
2. Search existing notes before answering.
3. Before asking a question, read the current graph, find useful gaps, and prefer queued/open-thread questions over generic onboarding.
4. Use Question Queue and Open Threads before starter templates.
5. Ask up to eight questions when the user wants a batch. Default to five for a general batch, three for a light pass, and one when explicitly asked for one.
6. Include a hint, evidence needed, target note types, and optional examples with each question.
7. Convert answers into atomic, linked Markdown notes.
8. Create domain maps only when the answer needs them.
9. Keep maps compact and split bloated notes before they become giant Markdown junk drawers.
10. Update maps and indexes so the graph stays usable instead of becoming note soup.
11. Use the template library as light scaffolding only: facts like birthday, communication style, dates, source links, and care notes are useful, but empty fields should not turn the vault into intake-form sludge.

If no initialized vault exists, Codex should ask:

```md
I do not see an initialized Self Atlas vault yet. Want me to create one at:

`~/Documents/Self-Atlas-Vault`
```

That default setup should be minimal. The full scaffold is opt-in.

Sensitive areas such as health, family, relationships, money, and identity should be written only with clear user intent and marked in frontmatter.

## Example-Led Prompting

Self Atlas asks in normal chat. No fake native question UI promise. Each prompt should include the question, why it matters, a hint, and a few example answer shapes.

Example:

```md
**Question:** What do you instantly reject because it feels fake, cold, generic, or soulless?
Why it matters: This builds anti-taste, which is one of the fastest ways to protect taste.
Hint: Give examples from apps, films, brands, writing, UI, rooms, clothes, or music.

Examples, if useful:
1. Generic startup language and lifeless UI make me reject things instantly.
2. Cold copy, fake polish, template layouts, weak motion, and safe taste all bother me.
3. The real list is messier: ...
```

The user can answer with a number, mix examples, or ignore them and write normally. The examples are there to reduce friction, not trap the answer in checkbox cosplay.
