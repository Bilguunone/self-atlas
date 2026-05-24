---
name: self-atlas
description: Build, query, and refine a private Markdown life graph about the user. Use when the user summons Self Atlas, asks to capture personal context, asks personal-memory questions, wants smart onboarding questions, or wants Codex to search a personal Markdown vault for identity, family, work, taste, health, goals, hobbies, and life-pattern context.
---

# Self Atlas

Self Atlas is a local-first personal memory workflow. It turns conversation into a plain Markdown life graph, then uses that graph to answer questions with context instead of generic mush. Obsidian can visualize it today; a custom Self Atlas visualizer can own it later.

## Core Taste

This should feel like a sharp friend slowly building a real map of a life, not a creepy HR intake form. Be warm, specific, and curious. Ask less, extract more. One good answer should create several useful memories.

Do not spray fifty questions at the user. That is lazy and rude.

## Example-Led Questions

Do not promise or force Codex's native question UI. Self Atlas should ask in normal chat with clear examples. The examples are scaffolding, not a form.

Every personal question should support:

- one direct answer
- mixed answers
- a completely custom answer

Use this pattern:

```markdown
**Question:** What do people consistently misunderstand about you?
Why it matters: This can update identity, relationships, work style, and emotional-pattern notes at once.
Hint: Answer with a repeated misread, a specific person, or a moment where you felt unseen.

Examples, if useful:
1. People mistake my intensity for arrogance.
2. Intensity, sensitivity, ambition, and weird taste all get flattened.
3. The real answer is stranger: ...
```

The user can answer with a number, a quoted example, a fragment, or a paragraph. Treat selected examples as rough source text, not the whole truth. If the answer is mixed, extract separate candidate memories and mark nuanced interpretations as `confidence: inferred` unless the user clarifies.

For setup and domain selection, use a tiny inline menu only when needed:

```markdown
Pick one, or answer naturally:
1. Create the default vault at `~/Documents/Self-Atlas-Vault`.
2. Use a different folder.
3. Ask questions for now without saving.
```

Keep the menu small. If the user gives prose instead of a number, follow the prose.

## Vault Discovery

Before reading or writing, find the vault:

1. Use a vault path explicitly named by the user.
2. Else use `SELF_ATLAS_VAULT` if that environment variable is set.
3. Else try the default path: `~/Documents/Self-Atlas-Vault`.
4. Else look in the current workspace for `Self Atlas`, `Self-Atlas`, `Self-Atlas-Vault`, `self-atlas`, `self-atlas-vault`, or `vault`.
5. If the user only wants a question, design, or reasoning, continue without writing.
6. If a write is needed and no initialized vault exists, ask to set one up before saving anything.

Use this setup prompt:

```markdown
I do not see an initialized Self Atlas vault yet. Want me to create one at:

`~/Documents/Self-Atlas-Vault`

I will add the minimal Markdown graph core there, then create domain maps only as your answers need them.
```

If the user says yes, initialize that vault. If they give a different path, initialize that path instead.

If the folder exists and is not empty but does not look like a Self Atlas vault, ask before adding structure:

```markdown
That folder already has files in it and does not look like a Self Atlas vault yet. Should I add the Self Atlas structure there without overwriting existing files?
```

For shell searches, prefer `rg`:

```bash
rg --files <vault>
rg -n "query|alias|tag" <vault> -g "*.md"
```

## Graph Structure

Start minimal by default. Do not pre-create a museum of empty life folders. The graph should grow from real answers.

Default minimal core:

```text
00 System/
  Home.md
  Graph Rules.md
  Question Queue.md
  Source Log.md
  Open Threads.md
  Templates/
90 Sources/
  Captures/
```

Create domain folders and map-of-content notes only when capture needs them:

```text
10 Self/Identity.md
10 Self/Desires.md
20 People/Family.md
30 Work/Career.md
40 Health/Health Overview.md
50 Taste/Taste Profile.md
60 Interests/Obsessions.md
80 Reflections/<Emergent Pattern>.md
```

Keep those active maps linked from `00 System/Home.md`.

If the user explicitly asks for the larger starter scaffold, use the full init mode. Otherwise keep it lean.

## Note Size Rules

Avoid giant notes. Self Atlas should be readable as Markdown, searchable by breadcrumbs, and visualizable as a graph later. One swollen master file ruins all three.

Use this shape:

- Raw source captures in `90 Sources/Captures/` may be longer because they preserve what the user actually said.
- Domain maps such as `Identity.md`, `Career.md`, and `Taste Profile.md` should stay compact: navigation, short summaries, and links.
- Durable notes should usually be atomic: one person, one project, one value, one preference, one health metric, one recurring pattern, or one obsession.
- Split a note when it crosses roughly `800-1200` words, has more than `5-7` headings, or mixes multiple unrelated subjects.
- Do not split just to satisfy a number if the note is still one coherent idea.
- When splitting, leave a short summary and links in the original map or parent note. Preserve aliases, tags, sensitivity, confidence, and source links.
- Keep `90 Sources/Captures/` as many topic-shaped source files, not one giant file. Raw captures may be longer than durable notes, but oversized captures should be split by topic/date and extracted into durable notes.
- Use `source-hygiene` when the source folder feels like it may be getting bloated, unextracted, or hard to scan.

Good split examples:

- `Taste Profile.md` links out to `Anti-Taste - Generic Startup Language.md`, `Motion Taste.md`, and `Warm Software References.md`.
- `Career.md` links out to `Product Direction.md`, `Work That Drains Me.md`, and specific project notes.
- `Health Overview.md` links out to dated or metric-specific notes instead of swallowing every body detail like a cursed spreadsheet.

## Note Schema

Use YAML frontmatter for durable notes:

```yaml
---
id: note:path-slug
schema_version: 1
type: index | identity | person | work | project | skill | preference | value | desire | pattern | event | life_period | milestone | source | question | creative_reference | money_context | logistics_thread | health_observation | health_metric
relationship_kind: person | friend | family | mentor | collaborator | love
relationship_context: unknown | social | family | mentorship | work | romantic
date_start: YYYY-MM-DD | YYYY-MM | YYYY | ""
date_end: YYYY-MM-DD | YYYY-MM | YYYY | ""
date_precision: exact | month | year | approximate | unknown | derived
life_period: ""
threads: []
people: []
projects: []
places: []
emotional_charge: unknown
pressure_level: unknown
turning_point: false
closeness: unknown
trust: unknown
relationship_phase: active
status: active
sensitivity: normal | private | health | financial | intimate
confidence: confirmed | inferred | uncertain
created: YYYY-MM-DD
updated: YYYY-MM-DD
aliases: []
tags: []
links: []
sources: []
---
```

Rules:

- `confidence: inferred` is allowed only when the note clearly says what was inferred and why.
- Sensitive notes use `sensitivity: private`, `health`, `financial`, or `intimate`.
- Do not invent facts. If the answer implies something, mark it as inference or ask.
- For health data, record units and date. Do not diagnose or give medical advice.
- For person notes, use relationship fields when known. Love, friends, family, mentors, and collaborators are different graph types, not one emotional junk drawer.
- For timeline notes, keep exact dates exact and rough dates rough. Use `date_precision` instead of inventing fake day-level precision.
- App-ready fields such as `id` and `schema_version` are recommended for future notes but not required for existing notes. Do not migrate old notes just to add them unless the user explicitly asks.
- When migrating app fields, add only deterministic `id` and `schema_version` frontmatter. Do not change `updated`, note bodies, existing facts, source links, sensitivity, confidence, aliases, tags, or wording unless the user explicitly asks for a content edit.
- When migrating relationship fields, add only frontmatter relationship semantics. Do not rewrite person-note body text unless the user explicitly asks for content edits.
- Thin notes should be deepened from user answers or existing sources, never by invented filler. If a people/project note is thin, generate targeted follow-up questions and queue them.

## Template Library

The helper script owns the starter template registry. Keep templates light: useful memory handles, not a life-admin spreadsheet pretending to be wisdom.

Use `list-templates` to inspect the current library and `sync-templates` to copy missing templates into `00 System/Templates`. The library covers:

- system notes: source captures, domain maps, open threads, questions
- people: generic people, friends, family, collaborators, love relationships
- work: projects, employers, roles, skills, career threads
- taste and creative direction: preferences, anti-taste, references, music identity, product principles
- inner life: identity, values, desires, fears, patterns, tensions
- timeline and practical life: events, periods, milestones, money, logistics, health observations, health metrics

Person templates may include practical fields such as birthday, met date/context, personality/temperament, communication style, gift/care notes, and important dates. Keep those in the body unless the app truly needs them as structured fields.

## Linking Rules

Use wiki-style links aggressively but cleanly:

- Link people: `[[20 People/Family/Mother|mother]]`
- Link domains: `[[50 Taste/Taste Profile]]`
- Link events: `[[70 Timeline/Life Timeline]]`
- Link projects: `[[30 Work/Projects/Project Name]]`
- Link source captures: `[[90 Sources/Captures/YYYY-MM-DD-title]]`

Prefer stable filenames. Rename only when the existing name is clearly wrong.

Tags are for broad graph filters, not every noun in the sentence:

```yaml
tags:
  - self-atlas/identity
  - self-atlas/family
  - self-atlas/health
  - self-atlas/taste
```

## Breadcrumb Search

When the user asks a question that might be answerable from the vault:

1. Parse the ask into entities, domains, time range, and sensitivity.
2. Search exact terms, likely aliases, tags, and related nouns.
3. Open `00 System/Home.md`, then the most relevant domain map.
4. Follow wiki links and backlinks one hop. Expand to two hops only if the first pass is too thin.
5. Prefer confirmed, recent notes over older inferred notes.
6. If notes conflict, say so and cite the conflicting files.
7. If context is missing, ask one focused follow-up instead of hallucinating.

Answer with local Markdown path references when useful.

## Capture Workflow

When the user answers a question or says to capture something:

1. Preserve the raw answer in `90 Sources/Captures/`.
2. For existing source captures, prefer a `capture-review` or `extract-plan` pass before editing durable notes. `capture-review` is the consent-aware surface; `extract-plan` is the lower-level typed plan. The intended struct is `RawCapture -> MemoryCandidate[] -> DurableNotePatch[] -> LinkPatch[] -> ReviewFlags`.
3. Extract atomic memories:
   - people
   - facts
   - preferences
   - values
   - recurring patterns
   - tensions
   - goals
   - health metrics
   - dates and events
   - open questions
4. Search for an existing domain map before creating anything new.
5. Update an existing domain map if it fits.
6. Create a new domain map only when the answer proves the domain matters.
7. Add links between the source capture and derived notes.
8. Update `00 System/Home.md`, `00 System/Source Log.md`, and the relevant map-of-content note.
9. Check note size and scope before appending. Split notes that are becoming bloated, but do not turn every sentence into a new file unless it deserves one.

Folders should appear because repeated material demands them, not because some template got too excited.

If an answer contains sensitive material, summarize the planned write first and ask before committing if the user has not explicitly asked to save it.

## Pulse And Thread Walk

Use `pulse` when the user wants to know what the atlas needs next, what is alive right now, or where to continue. Pulse is the human home surface: open threads, queued questions, recent captures, unextracted sources, thin notes, uncertainty, hubs, and best next moves. It is read-only.

Use `thread-walk` when the user asks to trace a project, person, taste thread, fear, value, or recurring pattern through the graph. A Thread Walk should feel like following a trail across source-backed notes, not dumping the whole vault. Prefer a narrow query such as `export motion`, `Velum`, `music identity`, `pressure`, or a person/project name.

Both commands default to share-safe output. Use `--include-sensitive` only when the user clearly wants private local context in the current session.

## Insight Commands

Use `life-lenses` to list or apply reusable views of the graph: identity, career, creative, taste, relationships, health, money, logistics, and timeline.

Use `open-loop-radar` when the user wants to know what is unresolved. It combines queued questions, open threads, unextracted sources, uncertainty, source-log gaps, and contradiction signals.

Use `contradictions` when the user asks what does not line up, what changed, what feels stale, or what needs review. Treat results as leads, not verdicts.

Use `decision-council` when the user asks for help choosing. It builds a receipt-backed brief across practical, taste, future-self, relationship, privacy, and craft angles. If the user gives options, pass them as `--options "A|B|C"`.

Use `time-travel` to compare timeline eras, threads, pressure, emotional charge, turning points, people, and projects.

Use `share-capsule` before sharing any graph-derived summary. It creates a relative-path Markdown or JSON bundle, excludes sensitive notes by default, and requires `--include-sensitive --yes` for private capsules.

Use `taste-genome` when the user asks about taste, anti-taste, references, proof moments, motion/material language, or creative weak spots.

Use `artifact-import` to turn local `.md`, `.txt`, `.json`, directories of those files, or URL metadata into source captures. It is dry-run by default; with `--apply` it writes source captures only. Durable memory still goes through `capture-review` and `apply-review`, because importing a pile of text straight into beliefs would be sloppy little chaos.

## Question Selection Pass

When the user asks Self Atlas to ask a question, do not blindly pull from the starter question list. First read the current graph enough to ask a question that fits what is already known and what is still missing.

If an initialized vault exists, do this quick pass before asking:

1. Read `00 System/Home.md`, `00 System/Question Queue.md`, `00 System/Open Threads.md`, `00 System/Source Log.md`, and `00 System/Graph Rules.md`.
2. Skim the most relevant domain maps linked from `Home.md`.
3. Check recent captures by title and summary before asking something that may already be answered.
4. Build a small mental snapshot:
   - known anchors: confirmed facts, people, projects, values, taste, health context, goals
   - thin areas: short maps, empty people/project notes, missing dates, weak source detail
   - open loops: queued questions, unresolved conflicts, active practical deadlines
   - stale or uncertain areas: imported memories, inferred patterns, contradicted notes
5. Choose a question that fills a real gap or resolves a real open thread.

Selection rules:

- User-requested domain wins.
- If no domain is requested, prefer `Question Queue` and `Open Threads` over generic onboarding questions.
- Rotate domains over time: identity, people/love, family, work, money, health, taste, interests, desires, timeline, logistics.
- Prefer questions that can update multiple notes at once.
- Prefer questions that ask for concrete evidence: dates, names, values, places, examples, links, numbers, artifacts, body metrics, documents, roles, or source references.
- Avoid asking for facts already captured unless they are stale, uncertain, or need detail.
- Do not repeatedly ask the same style of question just because the starter list is easy. That is prompt-deck laziness wearing a little hat.
- Treat sensitive/health/financial/intimate questions with extra care and ask them only when they are useful, not for curiosity points.

When presenting the question, keep the audit invisible or very short. A good pattern:

```markdown
I looked at the current graph. The thinnest useful gap right now is your actual role and responsibility at the current company.

**Question:** What are you actually responsible for at the current company right now?
Why it matters: This can update career, skills, money context, current identity, and future job-direction notes.
Hint: Answer with daily work, ownership, team role, what people rely on you for, and what parts feel alive or draining.

Examples, if useful:
1. I mostly own product/interface craft and prototype direction.
2. I do a mixed role: design, SwiftUI, product thinking, AI/context ideas, and taste feedback.
3. The official role and the real role are different: ...
```

If no vault exists, use the starter question list. If the vault exists but the user asks for a totally random question, still do a light graph pass and pick something varied.

## Question Loop

Default to five questions for a general batch, three for a light pass, and one when the user explicitly asks for one. Ask up to eight when the user wants a bigger batch. Do not spray fifty questions at them like a broken survey machine.

Each question should include:

- the question
- why it matters
- a short hint or example
- target note types
- sensitivity
- evidence needed
- two or three example answer shapes when examples would help

Format:

```markdown
**Question:** What did you actually own at work this week, not the fake job-description version?
Why it matters: This sharpens role, skill, project, and career evidence without corporate cosplay.
Hint: List the project, artifact, decision, people involved, and what would have broken without you.
Target notes: work, project, skill, person
Sensitivity: normal
Evidence needed: date range, project, artifact, people, decision, outcome

Examples, if useful:
1. I owned the SwiftUI interaction pass for one screen; without me it would have shipped as mush.
2. I made the product call, the UI call, and the taste call, even though only one was official.
3. This week the real ownership was: ...
```

The helper script has a `QuestionTemplate` registry with `domain`, `intent`, `why`, `hint`, `examples`, `target_note_types`, `sensitivity`, and `evidence_needed`. Use `suggest-question` for vault-aware questions because it reads the queue and open threads before falling back to templates.

After the user answers:

1. Capture the answer.
2. Update the graph.
3. Offer another question only if the user seems to want to continue.

Good question types:

- Timeline: "What exact month/year anchors this chapter, project, role, or obligation?"
- Person: "What real scene turns this person from a label into someone future-you recognizes?"
- Work: "What did you actually own this week, and what would have broken without you?"
- Taste: "What recent reference had pulse, and what exact detail made it work?"
- Health: "What happened last time, with date, duration, frequency, intensity, trigger, and action?"
- Money: "What amount, currency, cadence, and deadline make this plan real?"
- Logistics: "What date, document, blocker, and next action should not be hand-waved?"

## Commands The User May Say

- "Self Atlas, ask me one question."
- "Capture this in my Self Atlas."
- "Search my Self Atlas for what I care about in work."
- "Use my Self Atlas to answer this."
- "Keep going."
- "Initialize a Self Atlas vault at `<path>`."

## Helper Script

Use `scripts/self_atlas.py` for repeatable setup and simple vault actions:

```bash
SELF_ATLAS_PLUGIN="${SELF_ATLAS_PLUGIN:-$HOME/plugins/self-atlas}"

python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" ensure --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" init --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" init --vault ~/Documents/Self-Atlas-Vault --full
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" list-templates
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" sync-templates --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" list-question-templates
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" question --count 5 --with-examples
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" question --domain taste --count 3 --with-examples
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" capture --vault ~/Documents/Self-Atlas-Vault --title "Taste note" --domain taste --body "I hate generic startup copy."
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" search --vault ~/Documents/Self-Atlas-Vault "startup copy"
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" audit --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" find-gaps --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" pulse --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" pulse --vault ~/Documents/Self-Atlas-Vault --include-sensitive
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" pulse --vault ~/Documents/Self-Atlas-Vault --include-sensitive --json
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" enrich-thin-notes --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" enrich-thin-notes --vault ~/Documents/Self-Atlas-Vault --apply --limit 12
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" suggest-question --vault ~/Documents/Self-Atlas-Vault --count 5 --with-examples
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" thread-walk --vault ~/Documents/Self-Atlas-Vault --query "music identity"
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" thread-walk --vault ~/Documents/Self-Atlas-Vault --query "music identity" --include-sensitive
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" thread-walk --vault ~/Documents/Self-Atlas-Vault --query "music identity" --include-sensitive --json
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" answer-context --vault ~/Documents/Self-Atlas-Vault --query "who am I creatively?"
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" answer-context --vault ~/Documents/Self-Atlas-Vault --query "who am I creatively?" --include-sensitive --json
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" life-lenses --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" life-lenses --vault ~/Documents/Self-Atlas-Vault --lens taste --query "motion" --json
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" open-loop-radar --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" contradictions --vault ~/Documents/Self-Atlas-Vault --lens career
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" decision-council --vault ~/Documents/Self-Atlas-Vault --question "Which project deserves the next week?" --options "Project A|Project B" --include-sensitive
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" artifact-import --vault ~/Documents/Self-Atlas-Vault --source ~/Downloads/reference.md --domain taste
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" artifact-import --vault ~/Documents/Self-Atlas-Vault --source ~/Downloads/reference.md --domain taste --apply
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" time-travel --vault ~/Documents/Self-Atlas-Vault --thread career
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" share-capsule --vault ~/Documents/Self-Atlas-Vault --query "music identity" --lens taste --json
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" taste-genome --vault ~/Documents/Self-Atlas-Vault --json
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" refresh-questions --vault ~/Documents/Self-Atlas-Vault --mode mixed --count 8 --with-examples
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" refresh-questions --vault ~/Documents/Self-Atlas-Vault --mode regenerate --count 8 --apply
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" extract-plan --vault ~/Documents/Self-Atlas-Vault --source "90 Sources/Captures/YYYY-MM-DD-topic"
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" extract-plan --vault ~/Documents/Self-Atlas-Vault --source "90 Sources/Captures/YYYY-MM-DD-topic" --json
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" capture-review --vault ~/Documents/Self-Atlas-Vault --source "90 Sources/Captures/YYYY-MM-DD-topic"
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" capture-review --vault ~/Documents/Self-Atlas-Vault --source "90 Sources/Captures/YYYY-MM-DD-topic" --json
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" apply-review --vault ~/Documents/Self-Atlas-Vault --source "90 Sources/Captures/YYYY-MM-DD-topic"
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" apply-review --vault ~/Documents/Self-Atlas-Vault --source "90 Sources/Captures/YYYY-MM-DD-topic" --apply --yes
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" validate-links --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" confidence-report --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" split-large-notes --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" source-hygiene --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" dedupe-memory --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" graph-summary --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" timeline-report --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" timeline-export --vault ~/Documents/Self-Atlas-Vault --pretty
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" timeline-export --vault ~/Documents/Self-Atlas-Vault --include-sensitive --pretty
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" migrate-source-fields --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" migrate-source-fields --vault ~/Documents/Self-Atlas-Vault --include-empty --apply
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" migrate-relationship-fields --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" migrate-relationship-fields --vault ~/Documents/Self-Atlas-Vault --apply
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" migrate-app-fields --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" migrate-app-fields --vault ~/Documents/Self-Atlas-Vault --apply
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" schema-report --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" export-json --vault ~/Documents/Self-Atlas-Vault --pretty
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" export-preview --vault ~/Documents/Self-Atlas-Vault
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" export-preview --vault ~/Documents/Self-Atlas-Vault --include-body --include-sensitive
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" export-json --vault ~/Documents/Self-Atlas-Vault --include-body --include-sensitive --pretty
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" export-json --vault ~/Documents/Self-Atlas-Vault --include-templates --pretty
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" export-json --vault ~/Documents/Self-Atlas-Vault --out ~/Documents/Self-Atlas-Vault/self-atlas.graph.json --pretty
python3 "$SELF_ATLAS_PLUGIN/scripts/self_atlas.py" timeline-export --vault ~/Documents/Self-Atlas-Vault --out ~/Documents/Self-Atlas-Vault/self-atlas.timeline.json --pretty
```

The audit, pulse, thread-walk, answer-context, life-lenses, open-loop-radar, contradictions, decision-council, time-travel, share-capsule, taste-genome, find-gaps, suggest-question, extract-plan, capture-review, validate-links, confidence-report, split-large-notes, source-hygiene, dedupe-memory, graph-summary, timeline-report, export-preview, and schema-report commands are report-only. They must not modify the user's vault. `artifact-import` is dry-run unless `--apply` is passed, and apply mode only writes source captures plus Source Log/domain-map references. `pulse` is the lightweight home surface for continuation. `thread-walk` traces a query through linked notes and can print JSON for app surfaces. `answer-context` gathers answer receipts: matching notes, visible source captures, confidence, sensitivity, linked notes, and review flags. `life-lenses`, `open-loop-radar`, `contradictions`, `decision-council`, `time-travel`, `share-capsule`, and `taste-genome` share one insight layer for lens filtering, privacy hiding, evidence refs, and JSON-ready output. `share-capsule` excludes sensitive notes by default and requires `--include-sensitive --yes` before private capsule output. `suggest-question` reads Question Queue and Open Threads before starter templates, rotates domains in batches, includes evidence requirements, and caps batches at eight. `refresh-questions` previews by default and can shuffle existing queue items, regenerate from the template library, or mix both; with `--apply`, it rewrites `00 System/Question Queue.md`, bumps `updated`, and preserves rotated-out questions under `Question Refresh History`. `extract-plan` converts one source capture into typed review objects: `RawCapture`, `MemoryCandidate`, `DurableNotePatch`, `LinkPatch`, and `ReviewFlag`. `capture-review` summarizes that plan into source status, patch readiness, target decisions, review flags, and consent notes. `apply-review` is dry-run unless `--apply` is passed; sensitive/private captures require `--apply --yes`. It appends reviewed durable bullets, updates `sources` frontmatter, queues follow-up questions, updates Source Log, and creates backups. It reads both current headings (`Extracted Notes`, `Follow-Up Threads`) and legacy headings (`Derived Notes`, `Open Questions`). Each `MemoryCandidate` and `DurableNotePatch` includes `SourceEvidence` with source path, source section, line hint, raw excerpt, confidence, and sensitivity, and candidate confidence should not be stronger than source confidence without human review. It can print Markdown-ish review output or JSON for future app/executor work. `timeline-report` and `timeline-export` build an app-ready life timeline with items, derived periods, threads, rough-date precision, pressure, emotional charge, turning points, linked people/projects/places, and sources. Timeline commands exclude private/health/financial/intimate notes by default, omit absolute vault paths, and skip items that point at hidden notes. Use `--include-sensitive` only for private local timeline output. `source-hygiene` reports oversized captures, captures without durable backlinks, Source Log gaps, empty extraction targets, and archive pressure. `sync-templates` writes only under `00 System/Templates` and does not overwrite existing templates unless `--overwrite` is passed. `enrich-thin-notes` is report-only unless `--apply` is passed; apply mode may append questions to `00 System/Question Queue.md` but must not invent facts or edit target notes. `migrate-source-fields` is dry-run unless `--apply` is passed; apply mode derives `sources` frontmatter from existing source-capture links, can add empty `sources: []` with `--include-empty`, and should create backups. `migrate-relationship-fields` is dry-run unless `--apply` is passed; apply mode adds typed relationship frontmatter to person notes for love, friends, family, mentors, and collaborators while leaving bodies untouched. `migrate-app-fields` is dry-run unless `--apply` is passed; apply mode may add deterministic `id` and `schema_version` to frontmatter and should create backups. `export-preview` must be used before sharing/exporting anything questionable; it reports hidden sensitive notes, omitted edges, warnings, and body/sensitive risk without writing files. `export-json` must read the vault without modifying it; by default it excludes private, health, financial, and intimate notes and omits full body text. Use `--include-body` and `--include-sensitive` only for private local exports. Warn the user before sharing unsanitized exported files. Codex should still use judgment when merging, linking, and refining notes.
