# Self Atlas

Self Atlas is a Codex plugin for building a private Markdown life graph about a person: identity, family, work, taste, health context, mindset, hobbies, obsessions, values, projects, desires, things bought/owned/wanted, private contact/logistics details, credential/account references, and the weird little patterns that actually make someone legible.

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
- `scripts/self_atlas_lib/` contains the real implementation modules: vault IO, templates, questions, extraction, reports, migrations, export, insight surfaces, and CLI wiring.
- `scripts/install_local_plugin.py` can copy the repo into a local `~/plugins/self-atlas` folder and generate local-only plugin metadata for private Codex setups.
- `pyproject.toml` provides the optional `self-atlas` console command for editable installs.
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
python3 scripts/self_atlas.py pulse --vault "$DEMO_VAULT" --include-sensitive
python3 scripts/self_atlas.py thread-walk --vault "$DEMO_VAULT" --query "export motion" --include-sensitive
python3 scripts/self_atlas.py answer-context --vault "$DEMO_VAULT" --query "what is Lumen Sketch proof moment" --include-sensitive
python3 scripts/self_atlas.py life-lenses --vault "$DEMO_VAULT"
python3 scripts/self_atlas.py open-loop-radar --vault "$DEMO_VAULT" --include-sensitive
python3 scripts/self_atlas.py contradictions --vault "$DEMO_VAULT" --include-sensitive
python3 scripts/self_atlas.py decision-council --vault "$DEMO_VAULT" --question "should Lumen Sketch focus on export motion or onboarding copy" --options "Export motion|Onboarding copy" --include-sensitive
python3 scripts/self_atlas.py time-travel --vault "$DEMO_VAULT" --include-sensitive
python3 scripts/self_atlas.py share-capsule --vault "$DEMO_VAULT" --query "export motion" --lens taste --json
python3 scripts/self_atlas.py taste-genome --vault "$DEMO_VAULT"
python3 scripts/self_atlas.py proof-engine --vault "$DEMO_VAULT" --claim "Lumen Sketch proof moment is export motion" --include-sensitive
python3 scripts/self_atlas.py belief-versioning --vault "$DEMO_VAULT" --query "export motion" --include-sensitive
python3 scripts/self_atlas.py taste-autopilot --vault "$DEMO_VAULT" --text "A generic productivity dashboard with onboarding copy and no export proof."
python3 scripts/self_atlas.py decision-replay --vault "$DEMO_VAULT" --decision "export motion" --include-sensitive
python3 scripts/self_atlas.py future-self --vault "$DEMO_VAULT" --query "Lumen Sketch" --include-sensitive
python3 scripts/self_atlas.py artifact-import --vault "$DEMO_VAULT" --source https://example.com/lumen-sketch-reference --domain taste
python3 scripts/self_atlas.py suggest-question --vault "$DEMO_VAULT" --count 5 --with-examples
python3 scripts/self_atlas.py refresh-questions --vault "$DEMO_VAULT" --mode mixed --count 8 --with-examples
python3 scripts/self_atlas.py capture-review --vault "$DEMO_VAULT" --source "90 Sources/Captures/2026-05-21-demo-answer"
python3 scripts/self_atlas.py apply-review --vault "$DEMO_VAULT" --source "90 Sources/Captures/2026-05-21-demo-answer"
python3 scripts/self_atlas.py export-preview --vault "$DEMO_VAULT"
python3 scripts/self_atlas.py graph-summary --vault "$DEMO_VAULT"
python3 scripts/self_atlas.py timeline-report --vault "$DEMO_VAULT"
python3 scripts/self_atlas.py timeline-export --vault "$DEMO_VAULT" --pretty
python3 scripts/self_atlas.py export-json --vault "$DEMO_VAULT" --pretty
```

For a personal vault, choose a folder outside this repo:

```bash
VAULT="$HOME/Documents/Self-Atlas-Vault"

python3 scripts/self_atlas.py ensure --vault "$VAULT" --yes
python3 scripts/self_atlas.py sync-templates --vault "$VAULT"
python3 scripts/self_atlas.py suggest-question --vault "$VAULT" --count 5 --with-examples
```

For the first complete loop, follow [10-Minute First Vault](docs/10-minute-first-vault.md).

Optional editable CLI install:

```bash
python3 -m pip install -e .
self-atlas --help
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
cp .privacy-patterns.example .privacy-patterns  # optional local-only private term scanner
python3 scripts/public_release_check.py
python3 tests/test_self_atlas.py
```

The committed `.privacy-patterns.example` is synthetic. Put real local names, project names, places, clinics, employers, or source phrases only in untracked `.privacy-patterns`.

The report commands are read-only. They do not change existing Atlas content. `pulse` shows the current graph state: open threads, queued questions, recent captures, unextracted sources, thin notes, uncertainty, hubs, and best next moves. `thread-walk` follows one query across linked notes so the graph becomes a readable trail instead of a spaghetti poster. Both can print JSON for future app surfaces. `answer-context` is the receipt layer for answering: matching notes, visible source receipts, confidence, sensitivity, linked notes, and review flags. The insight commands share the same privacy-first engine: `life-lenses` lists and applies reusable graph lenses; `open-loop-radar` combines queues, open threads, source gaps, uncertainty, and contradiction signals; `contradictions` reports stale/conflicting/status/tension leads without resolving them; `decision-council` builds a receipt-backed brief across practical, taste, future-self, relationship, privacy, and craft councils; `time-travel` compares eras and timeline threads; `share-capsule` creates safe Markdown/JSON bundles; `taste-genome` extracts taste principles, anti-taste, references, proof examples, and weak spots; `proof-engine` scores claims against receipts; `belief-versioning` traces belief/preference change over time; `taste-autopilot` checks draft artifacts against the Taste Genome; `decision-replay` compares old choices against later outcome receipts; and `future-self` simulates likely trajectories from current graph patterns. `artifact-import` is dry-run by default; with `--apply`, it creates source captures from `.md`, `.txt`, `.json`, directories of those files, or lightweight URL metadata, then leaves durable extraction to `capture-review` and `apply-review`. `source-hygiene` reports oversized captures, unextracted sources, Source Log gaps, and archive pressure so `90 Sources/Captures/` can grow without turning into a junk drawer. `extract-plan` turns one raw capture into a typed, reviewable plan: `RawCapture -> MemoryCandidate[] -> DurableNotePatch[] -> LinkPatch[] -> ReviewFlags`. `capture-review` summarizes that plan as a consent-aware review surface with candidate counts, target decisions, proposed patches, evidence, and sensitive-write blockers. `apply-review` is dry-run by default; with `--apply` it appends reviewed durable-note bullets, adds source frontmatter, queues follow-up questions, updates Source Log, and creates backups. Sensitive sources require `--apply --yes`. `timeline-report` and `timeline-export` build an app-ready life timeline, including dated `thing` notes for purchases and meaningful usage-start anchors. All safe/default exports exclude private/health/financial/intimate notes; use `--include-sensitive` only for private local output, and `share-capsule --include-sensitive` also requires `--yes`.

`examples/demo-vault/exports/` contains committed fixture JSON for the current demo Pulse, Thread Walk, Answer Context, insight commands, and safe Export Preview shapes. These fixtures are fictional and intended for app/UI development.

## Plugin Behavior

Self Atlas should behave like an always-on capture layer for meaningful context, not a special mode the user has to summon with ceremonial wording. For nearly every normal Codex turn, scan both the user's input and the assistant's output for durable value: facts, preferences, goals, decisions, constraints, work/project updates, advice, product direction, career strategy, taste principles, relationship context, logistics, and recurring patterns. Capture compact source-backed updates when there is durable value, then mention important writes briefly. Do not save pure noise: transient logs, mechanical command output, duplicate facts, throwaway jokes, generic explanations, or temporary debugging chatter. Opt-outs such as "do not save this", "just chatting", "off the record", "don't put this in the vault", or "hypothetical" mean no write.

Attachments count too. Visible text in screenshots, pasted images, PDFs, receipts, order confirmations, chat screenshots, and file previews should be scanned for durable context. If the user says "this should have triggered" and the attachment contains a purchase, pricing, usage pattern, praise/criticism, dates, or object details, capture it. If the user says "this" but the assistant reply/title/receipt/nearby visible context names the object, use that context instead of letting pronoun ambiguity make the system pretend it saw nothing.

For personal advice, Self Atlas should be the first context source, not Codex's built-in memory cosplay. When the user asks about their career, work direction, projects, portfolio, taste, purchases, relationships, health, money, identity, goals, or life choices, Codex should read the local vault before answering if it is available. Built-in memory can help guess what to search, but it should not replace the vault. Codex should not ask "Self Atlas or just chat memory?" for strong personal-context triggers; the default is automatic vault use unless the user explicitly says not to. For private one-to-one advice, Codex may use private graph context; share-safe mode is for export/posting/sharing workflows.

Codex should treat clear first-person durable life facts, work updates, career direction, decisions, advice, preferences, taste signals, relationships, contact details, credentials/account logistics, goals, constraints, and recurring patterns as implicit Self Atlas capture intent, not wait for a perfect "save this" incantation. Phrases like "I bought...", "I own...", "I want...", "I am considering...", "I realized...", "I am into...", "I hate/love...", "at work...", "for my career...", "my address is...", "their phone number is...", "the login uses...", "the account is...", "I decided...", "your advice is...", or "future me should know..." should trigger the Self Atlas workflow when they contain stable personal context.

Self Atlas should also run as a context engine for advice, not only as a memory collector. When the user asks "should I buy this?", "which one should I choose?", "does this fit my taste?", "is this a good career move?", "would I actually use this?", or similar context-dependent questions, Codex should read the relevant graph surfaces before answering. Purchase advice should consider Things, Taste, Money, active projects, past usage, and current goals. Career advice should consider Career, Skills, Projects, values, timeline, and work evidence. Creative/product advice should consider Taste Profile, anti-taste, active projects, references, and product principles. The answer should distinguish "fits you" from "generically good," because generic advice is the exact bland oatmeal this project exists to avoid.

When Self Atlas is triggered explicitly or implicitly, Codex should:

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

Implicit capture should still have taste and restraint:

- Things bought, owned, wanted, returned, sold, subscriptions, gear, objects, tools, apps, clothes, books, and devices route to `75 Things/`.
- Home addresses, phone numbers, email addresses, social handles, emergency contacts, birthdays, and practical contact details for the user or known people route to the relevant self/person notes and should be marked private or stronger.
- Taste, people, work, career advice, accepted recommendations, project direction, health, money, timeline, logistics, values, desires, fears, identity, and recurring patterns route to their matching graph areas.
- Account names, login emails, recovery routes, license/transfer workflows, and where a secret lives may be captured as sensitive credential/account logistics.
- Meaningful advice should be captured only when it affects future choices, not when it is a disposable suggestion.
- For normal/private non-dangerous facts, capture/update directly and mention the write briefly.
- Do not capture if the user says not to save it, is clearly speaking hypothetically, or is asking for read-only brainstorming.
- Do not capture raw passwords, API keys, transfer IDs, private tokens, government ID numbers, exact card/bank numbers, or recovery codes from casual conversation. Prefer safe context and workflows. If the user explicitly confirms storing a raw secret anyway, warn that Markdown is plaintext, do not include the raw secret in Source Log summaries, and do not echo it back.
- Ask first when saving would be surprising, ambiguous, legally risky, very intimate, medically detailed, or third-party contact data from someone the user barely knows.

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
