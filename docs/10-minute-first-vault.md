# 10-Minute First Vault

This walkthrough is the smallest useful Self Atlas loop: initialize a private vault, ask one decent question, capture the answer, turn it into a reviewable extraction plan, then validate and export safely.

It is not pretending the CLI is a full memory-writing app yet. `extract-plan` is review-only: it proposes durable note patches and link patches, then a human or Codex applies them. Slightly annoying, yes. Also the correct privacy posture until writes are boringly reliable.

## 1. Create a Vault Outside the Repo

```bash
git clone https://github.com/Bilguunone/self-atlas.git
cd self-atlas

VAULT="$HOME/Documents/Self-Atlas-Vault"
python3 scripts/self_atlas.py ensure --vault "$VAULT" --yes
```

Expected shape:

```text
Initialized Self Atlas vault: ...
Mode: minimal
Created 5 starter files.
```

The minimal vault starts with five core files: Home, Graph Rules, Source Log, Question Queue, and Open Threads.

## 2. Ask a Small Batch

```bash
python3 scripts/self_atlas.py suggest-question --vault "$VAULT" --count 3 --with-examples
```

Good questions should ask for evidence: dates, scenes, examples, artifacts, people, places, numbers, or links. If the questions sound like generic journaling soup, that is a bug, not a lifestyle.

## 3. Capture One Answer

```bash
python3 scripts/self_atlas.py capture \
  --vault "$VAULT" \
  --title "First useful answer" \
  --domain identity \
  --sensitivity private \
  --body "In April 2026, I started a small creative tool after a week of messy visual experiments. A friend pushed me to finish one honest export instead of hiding behind ten directions. The thing I want remembered is that pressure, novelty, and a visible artifact helped me focus."
```

Expected output:

```text
.../90 Sources/Captures/YYYY-MM-DD-first-useful-answer.md
Updated domain map: .../10 Self/Identity.md
```

The raw capture is the evidence. Keep its voice intact.

## 4. Add Extracted Bullets

Open the generated source note under `90 Sources/Captures/` and add bullets like these under `## Extracted Notes`:

```md
- [[10 Self/Identity]] should remember that pressure, novelty, and a visible artifact helped focus.
- [[30 Work/Projects/First Creative Tool]] started in April 2026 after a week of messy visual experiments.
- [[20 People/Friends/Helpful Friend]] gave practical creative feedback that helped narrow the work.
```

Then add follow-up questions under `## Follow-Up Threads`:

```md
- What exact date in April did the first export feel real?
- What did the first saved artifact look like?
```

This is the moment where one messy answer becomes multiple future memories instead of one giant note burrito.

## 5. Review the Extraction Plan

```bash
CAPTURE="90 Sources/Captures/$(date +%F)-first-useful-answer"
python3 scripts/self_atlas.py extract-plan \
  --vault "$VAULT" \
  --source "$CAPTURE"
```

Expected sections:

```text
# Extraction Plan
## Memory Candidates
## Durable Note Patches
## Link Patches
## Review Flags
```

Review the plan before applying anything. Private, health, financial, family, relationship, and intimate material should always get an extra look.

If the plan references new target notes, create those notes or ask Codex to apply the patches before running `validate-links`. The CLI does not write durable patches yet.

## 6. Validate and Export Safely

```bash
python3 scripts/self_atlas.py validate-links --vault "$VAULT"
python3 scripts/self_atlas.py schema-report --vault "$VAULT"
python3 scripts/self_atlas.py timeline-report --vault "$VAULT"
python3 scripts/self_atlas.py export-json --vault "$VAULT" --pretty
```

`export-json`, `timeline-report`, and `timeline-export` exclude private, health, financial, and intimate notes by default. They also omit full note bodies unless you explicitly opt in where supported.

Only use the unsafe flags for private local work:

```bash
python3 scripts/self_atlas.py export-json --vault "$VAULT" --include-body --include-sensitive --pretty
python3 scripts/self_atlas.py timeline-export --vault "$VAULT" --include-sensitive --pretty
```

If you are publishing anything, do not use those flags. That should be obvious, but obvious things are exactly where people do spectacularly stupid stuff at 2 a.m.
