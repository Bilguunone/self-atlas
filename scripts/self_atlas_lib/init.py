from __future__ import annotations

from pathlib import Path

from .constants import CORE_DIRS, DOMAIN_CONFIG, FULL_EXTRA_DIRS
from .templates import template_files
from .vault import (
    append_under_heading,
    default_vault_path,
    frontmatter,
    has_existing_content,
    is_self_atlas_vault,
    normalized_path,
    slugify,
    titleize,
    today,
    wiki_link,
    write_if_missing,
)


def domain_config(domain: str) -> dict[str, str]:
    normalized = slugify(domain)
    if normalized in DOMAIN_CONFIG:
        return DOMAIN_CONFIG[normalized]
    title = titleize(domain)
    return {
        "folder": "80 Reflections",
        "map": f"80 Reflections/{title}.md",
        "title": title,
        "sensitivity": "private",
    }

def ensure_vault(vault: Path | None, initialize: bool, full: bool) -> int:
    target = normalized_path(vault or default_vault_path())

    if is_self_atlas_vault(target):
        print(f"Self Atlas vault ready: {target}")
        return 0

    if not initialize:
        print("Self Atlas vault is not initialized.")
        print(f"Suggested location: {target}")
        print()
        print("Ask the user before creating it:")
        print(f"Create a Self Atlas vault at {target}?")
        print()
        print("After confirmation, run:")
        script_path = Path(__file__).resolve().parent.parent / "self_atlas.py"
        print(f"python3 {script_path} ensure --vault {target} --yes")
        print()
        print("This creates the minimal core. Add --full only if the user wants the larger starter scaffold.")
        return 2

    if has_existing_content(target) and not is_self_atlas_vault(target):
        print(f"Initializing Self Atlas inside existing folder: {target}")
        print("Existing files will not be overwritten.")

    init_vault(target, full)
    return 0

def init_vault(vault: Path, full: bool = False) -> None:
    vault = normalized_path(vault)
    vault.mkdir(parents=True, exist_ok=True)
    for directory in CORE_DIRS:
        (vault / directory).mkdir(parents=True, exist_ok=True)

    created = []
    files = {
        "00 System/Home.md": home_note(),
        "00 System/Graph Rules.md": graph_rules_note(),
        "00 System/Question Queue.md": question_queue_note(),
        "00 System/Source Log.md": source_log_note(),
        "00 System/Open Threads.md": open_threads_note(),
    }
    files.update(template_files())

    if full:
        for directory in FULL_EXTRA_DIRS:
            (vault / directory).mkdir(parents=True, exist_ok=True)
        files.update(full_domain_files())

    for relative, content in files.items():
        if write_if_missing(vault / relative, content):
            created.append(relative)

    if full:
        for relative, content in full_domain_files().items():
            title = content.split("\n# ", 1)[1].split("\n", 1)[0] if "\n# " in content else relative
            ensure_home_link(vault, relative, title)

    mode = "full" if full else "minimal"
    print(f"Initialized Self Atlas vault: {vault}")
    print(f"Mode: {mode}")
    if created:
        print(f"Created {len(created)} starter files.")
    else:
        print("Vault already had the starter files. Nothing overwritten.")

def full_domain_files() -> dict[str, str]:
    return {
        "10 Self/Identity.md": domain_note("Identity", "identity"),
        "10 Self/Body.md": domain_note("Body", "health"),
        "10 Self/Mindset.md": domain_note("Mindset", "identity"),
        "10 Self/Values.md": domain_note("Values", "identity"),
        "10 Self/Desires.md": domain_note("Desires", "desire"),
        "30 Work/Career.md": domain_note("Career", "work"),
        "30 Work/Skills.md": domain_note("Skills", "work"),
        "40 Health/Health Overview.md": domain_note("Health Overview", "health", "health"),
        "50 Taste/Taste Profile.md": domain_note("Taste Profile", "taste"),
        "50 Taste/Influences.md": domain_note("Influences", "taste"),
        "50 Taste/Anti-Taste.md": domain_note("Anti-Taste", "taste"),
        "60 Interests/Hobbies.md": domain_note("Hobbies", "obsession"),
        "60 Interests/Obsessions.md": domain_note("Obsessions", "obsession"),
        "60 Interests/Media.md": domain_note("Media", "taste"),
        "70 Timeline/Life Timeline.md": domain_note("Life Timeline", "event"),
        "80 Reflections/Patterns.md": domain_note("Patterns", "identity"),
        "80 Reflections/Tensions.md": domain_note("Tensions", "identity"),
    }

def ensure_home_link(vault: Path, relative_path: str, title: str) -> bool:
    home = vault / "00 System" / "Home.md"
    return append_under_heading(home, "Active Maps", f"- {wiki_link(relative_path, title)}")

def ensure_domain_map(vault: Path, domain: str, sensitivity: str) -> Path:
    config = domain_config(domain)
    folder = vault / config["folder"]
    folder.mkdir(parents=True, exist_ok=True)

    map_path = vault / config["map"]
    map_sensitivity = sensitivity if sensitivity != "normal" else config["sensitivity"]
    created = write_if_missing(
        map_path,
        domain_note(config["title"], slugify(domain), map_sensitivity),
    )
    ensure_home_link(vault, config["map"], config["title"])
    if created:
        print(f"Created domain map: {map_path}")
    return map_path

def append_source_log(vault: Path, capture_relative: str, title: str, domain: str) -> None:
    source_log = vault / "00 System" / "Source Log.md"
    line = f"- {today()} - {wiki_link(capture_relative, title)} - `{slugify(domain)}`"
    append_under_heading(source_log, "Captures", line)

def append_domain_capture(map_path: Path, capture_relative: str, title: str) -> None:
    line = f"- {today()} - {wiki_link(capture_relative, title)}"
    append_under_heading(map_path, "Captures", line)

def home_note() -> str:
    return f"""---
type: index
status: active
sensitivity: normal
confidence: confirmed
created: {today()}
updated: {today()}
aliases: [Self Atlas, Personal Graph]
tags:
  - self-atlas/home
links: []
---

# Self Atlas

This is the home map for the personal graph.

## Core System

- [[00 System/Graph Rules]]
- [[00 System/Question Queue]]
- [[00 System/Source Log]]
- [[00 System/Open Threads]]

## Active Maps

## Rule

Small questions. Rich extraction. Dynamic maps. No questionnaire sludge.
"""

def graph_rules_note() -> str:
    return f"""---
type: rules
status: active
sensitivity: normal
confidence: confirmed
created: {today()}
updated: {today()}
aliases: []
tags:
  - self-atlas/system
links:
  - "[[00 System/Home]]"
---

# Graph Rules

- Start with the minimal core. Create domain maps only when real captures need them.
- Prefer atomic notes for durable people, projects, preferences, values, health metrics, and events.
- Preserve raw captures in `90 Sources/Captures/`.
- Keep domain maps compact: summaries, navigation, and links, not giant essays.
- Split notes around `800-1200` words, `5-7` headings, or mixed subjects unless the note is still one coherent idea.
- When splitting, leave a short summary and links in the parent note.
- Use wiki links for meaningful relationships.
- Use tags for broad filters only.
- Mark inferred notes clearly.
- Mark sensitive notes with `sensitivity: private`, `health`, `financial`, or `intimate`.
- Before asking new questions, read Home, Question Queue, Open Threads, Source Log, and relevant maps.
- Use Question Queue and Open Threads before starter templates.
- Prefer questions that fill real gaps, resolve open threads, or clarify stale/uncertain memories.
- Good questions ask for concrete evidence: dates, names, values, places, examples, links, numbers, or artifacts.
- Rotate question domains instead of repeating the same kind of prompt.
- Ask up to eight questions when the user wants a batch. Default to five for a general batch, three for a light pass, and one when explicitly asked for one.
"""

def question_queue_note() -> str:
    return f"""---
type: question
status: active
sensitivity: normal
confidence: confirmed
created: {today()}
updated: {today()}
aliases: []
tags:
  - self-atlas/questions
links:
  - "[[00 System/Home]]"
---

# Question Queue

Use this to park questions worth asking later.

## Next Questions

- What exact dates or date ranges anchor your current work timeline: last big project, current role, and next milestone?
- Who is one person in the graph that still feels like a label instead of a real person, and what specific scene should define them?
- What is one recent example of taste: something that felt alive, or something you rejected instantly because it felt dead?
- What is one number, date, document, or obligation future-you should not be allowed to hand-wave?
- What body, energy, or mood pattern has a recent timestamp, trigger, frequency, or measurable value attached?
"""

def source_log_note() -> str:
    return f"""---
type: source
status: active
sensitivity: normal
confidence: confirmed
created: {today()}
updated: {today()}
aliases: []
tags:
  - self-atlas/sources
links:
  - "[[00 System/Home]]"
---

# Source Log

Add raw capture links here when new source notes are created.

## Captures
"""

def open_threads_note() -> str:
    return f"""---
type: index
status: active
sensitivity: normal
confidence: confirmed
created: {today()}
updated: {today()}
aliases: []
tags:
  - self-atlas/open-threads
links:
  - "[[00 System/Home]]"
---

# Open Threads

Questions, contradictions, and unfinished threads that need future attention.
"""

def domain_note(title: str, domain: str, sensitivity: str = "normal") -> str:
    return f"""{frontmatter('index', domain, sensitivity, [f'self-atlas/{domain}'])}
# {title}

## What We Know

- 

## Captures

## Related

- [[00 System/Home]]
"""
