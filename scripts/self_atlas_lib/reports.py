from __future__ import annotations

import datetime as dt
import re
from collections import Counter, defaultdict
from pathlib import Path

from .constants import DEFAULT_THIN_NOTE_WORDS, RECOMMENDED_APP_FRONTMATTER
from .vault import (
    app_durable_notes,
    append_under_heading,
    as_string,
    bullet_lines,
    clean_bullet,
    collect_validation,
    extract_section_bullets,
    heading_count,
    link_exists,
    link_indexes,
    note_has_source_reference,
    note_inventory,
    parse_frontmatter_text,
    read_note,
    require_vault,
    resolve_link_target,
    wiki_link,
)


def print_validation_report(vault: Path) -> dict[str, object]:
    vault = require_vault(vault)
    report = collect_validation(vault)
    notes = report["notes"]
    print("# Validate Links")
    print()
    print(f"Vault: {vault}")
    print(f"Markdown files: {len(notes)}")
    print(f"Wiki links: {report['total_links']}")
    print(f"Missing wiki links: {len(report['missing_links'])}")
    print(f"Files missing frontmatter: {len(report['missing_frontmatter'])}")
    print(f"Files missing required metadata: {len(report['missing_metadata'])}")
    print(f"Ambiguous note basenames: {len(report['ambiguous_basename'])}")
    if report["missing_links"]:
        print()
        print("## Missing Links")
        for relative, target in report["missing_links"][:50]:
            print(f"- {relative} -> [[{target}]]")
    if report["missing_frontmatter"]:
        print()
        print("## Missing Frontmatter")
        for relative in report["missing_frontmatter"][:50]:
            print(f"- {relative}")
    if report["missing_metadata"]:
        print()
        print("## Missing Metadata")
        for relative, key in report["missing_metadata"][:50]:
            print(f"- {relative}: {key}")
    if report["ambiguous_basename"]:
        print()
        print("## Ambiguous Basenames")
        for base, values in list(report["ambiguous_basename"].items())[:25]:
            rendered = ", ".join(str(note["relative"]) for note in values)
            print(f"- {base}: {rendered}")
    return report

def graph_summary(vault: Path) -> None:
    vault = require_vault(vault)
    report = collect_validation(vault)
    notes = report["notes"]
    type_counts = Counter(str(note["frontmatter"].get("type", "missing")) for note in notes)
    sensitivity_counts = Counter(str(note["frontmatter"].get("sensitivity", "missing")) for note in notes)
    confidence_counts = Counter(str(note["frontmatter"].get("confidence", "missing")) for note in notes)
    inbound = Counter()
    outbound = []
    by_key, by_base = link_indexes(notes)

    for note in notes:
        outbound.append((len(note["links"]), str(note["relative"])))
        for target in note["links"]:
            target = str(target)
            if target in by_key:
                inbound[target] += 1
            elif target.endswith(".md") and target[:-3] in by_key:
                inbound[target[:-3]] += 1
            else:
                base = Path(target).name
                matches = by_base.get(base, [])
                if len(matches) == 1:
                    inbound[str(matches[0]["key"])] += 1

    sources = [note for note in notes if note["is_source"]]
    print("# Graph Summary")
    print()
    print(f"Vault: {vault}")
    print(f"Markdown files: {len(notes)}")
    print(f"Source notes: {len(sources)}")
    print(f"Wiki links: {report['total_links']}")
    print(f"Broken links: {len(report['missing_links'])}")
    print()
    print("## Types")
    for key, count in sorted(type_counts.items()):
        print(f"- {key}: {count}")
    print()
    print("## Sensitivity")
    for key, count in sorted(sensitivity_counts.items()):
        print(f"- {key}: {count}")
    print()
    print("## Confidence")
    for key, count in sorted(confidence_counts.items()):
        print(f"- {key}: {count}")
    print()
    print("## Most Linked Notes")
    for key, count in inbound.most_common(10):
        print(f"- {key}: {count}")
    print()
    print("## Most Outgoing Links")
    for count, relative in sorted(outbound, reverse=True)[:10]:
        print(f"- {relative}: {count}")

def confidence_report(vault: Path) -> None:
    vault = require_vault(vault)
    notes = note_inventory(vault)
    confidence_counts = Counter(str(note["frontmatter"].get("confidence", "missing")) for note in notes)
    sensitivity_counts = Counter(str(note["frontmatter"].get("sensitivity", "missing")) for note in notes)
    uncertain = [note for note in notes if str(note["frontmatter"].get("confidence", "")).lower() in {"uncertain", "inferred"}]
    mentions_uncertain = [
        note
        for note in notes
        if note not in uncertain
        and not str(note["relative"]).startswith("00 System/")
        and not note["is_source"]
        and re.search(r"\b(uncertain|inferred|stale|conflict|placeholder)\b", str(note["body"]), re.I)
    ]

    print("# Confidence Report")
    print()
    print(f"Vault: {vault}")
    print()
    print("## Confidence Counts")
    for key, count in sorted(confidence_counts.items()):
        print(f"- {key}: {count}")
    print()
    print("## Sensitivity Counts")
    for key, count in sorted(sensitivity_counts.items()):
        print(f"- {key}: {count}")
    print()
    print("## Explicitly Uncertain Or Inferred Notes")
    if uncertain:
        for note in uncertain:
            print(f"- {note['relative']} ({note['frontmatter'].get('confidence')})")
    else:
        print("- None")
    print()
    print("## Confirmed Notes Mentioning Uncertainty")
    if mentions_uncertain:
        for note in mentions_uncertain[:25]:
            print(f"- {note['relative']} (review language inside note)")
    else:
        print("- None")

def split_large_notes(vault: Path, words: int, headings: int, include_sources: bool) -> None:
    vault = require_vault(vault)
    candidates = []
    for note in note_inventory(vault):
        if note["is_template"]:
            continue
        if note["is_source"] and not include_sources:
            continue
        reasons = []
        if int(note["words"]) >= words:
            reasons.append(f"{note['words']} words")
        if int(note["headings"]) >= headings:
            reasons.append(f"{note['headings']} headings")
        if reasons:
            candidates.append((int(note["words"]), int(note["headings"]), str(note["relative"]), reasons, bool(note["is_source"])))

    print("# Split Large Notes")
    print()
    print("Mode: report-only. No files were changed.")
    print(f"Thresholds: {words} words, {headings} headings")
    if not include_sources:
        print("Source captures excluded because raw captures are allowed to be long.")
    print()
    if not candidates:
        print("No split candidates found.")
        return
    for words_count, heading_count_value, relative, reasons, is_source in sorted(candidates, reverse=True):
        label = "source capture" if is_source else "note"
        print(f"- {relative} ({label}): {', '.join(reasons)}")
        print("  Suggestion: keep a compact parent summary, split durable subtopics into linked atomic notes.")

def is_capture_note(note: dict[str, object]) -> bool:
    return str(note["relative"]).startswith("90 Sources/Captures/")

def source_log_contains(source_log_text: str, source_key: str) -> bool:
    source_path = f"{source_key}.md"
    return source_key in source_log_text or source_path in source_log_text

def has_empty_extraction_targets(body: str) -> bool:
    marker = "## Extraction Targets"
    if marker not in body:
        return False
    section = body.split(marker, 1)[1]
    next_heading = section.find("\n## ")
    if next_heading != -1:
        section = section[:next_heading]
    bullets = [line.strip() for line in section.splitlines() if line.strip().startswith("- ")]
    if not bullets:
        return True
    filled = [line for line in bullets if not re.match(r"^-\s+[^:]+:\s*$", line)]
    return not filled

def source_hygiene(vault: Path, words: int, max_items: int, stale_days: int) -> None:
    vault = require_vault(vault)
    notes = note_inventory(vault)
    by_key, by_base = link_indexes(notes)
    captures = [note for note in notes if is_capture_note(note)]
    capture_keys = {str(note["key"]) for note in captures}
    durable = app_durable_notes(notes)
    durable_keys = {str(note["key"]) for note in durable}
    durable_inbound = Counter()
    all_inbound = Counter()
    imported_keywords = ("import", "export", "chatgpt", "memory")

    for note in notes:
        for target in note["links"]:
            target_note, ambiguous = resolve_link_target(str(target), by_key, by_base)
            if ambiguous or not target_note:
                continue
            target_key = str(target_note["key"])
            if target_key in capture_keys:
                all_inbound[target_key] += 1
                if str(note["key"]) in durable_keys:
                    durable_inbound[target_key] += 1

    source_log_path = vault / "00 System" / "Source Log.md"
    source_log_text = source_log_path.read_text(encoding="utf-8") if source_log_path.exists() else ""

    oversized = []
    missing_durable_backlinks = []
    missing_source_log = []
    empty_extraction_targets = []
    import_review = []
    largest = []

    today_date = dt.date.today()
    stale_cutoff = today_date - dt.timedelta(days=stale_days)
    stale_unextracted = []

    for note in captures:
        relative = str(note["relative"])
        key = str(note["key"])
        words_count = int(note["words"])
        largest.append((words_count, relative))
        if words_count >= words:
            oversized.append((words_count, relative, int(note["headings"])))
        if durable_inbound[key] == 0:
            missing_durable_backlinks.append((words_count, relative, all_inbound[key]))
        if not source_log_contains(source_log_text, key):
            missing_source_log.append(relative)
        if has_empty_extraction_targets(str(note["body"])):
            empty_extraction_targets.append(relative)
        if any(keyword in relative.lower() for keyword in imported_keywords):
            import_review.append((words_count, relative, durable_inbound[key]))
        created_raw = as_string(note["frontmatter"].get("created"))
        try:
            created_date = dt.date.fromisoformat(created_raw)
        except ValueError:
            created_date = None
        if created_date and created_date <= stale_cutoff and durable_inbound[key] == 0:
            stale_unextracted.append((created_raw, words_count, relative))

    total_words = sum(int(note["words"]) for note in captures)
    average_words = round(total_words / len(captures)) if captures else 0
    root_capture_count = sum(1 for note in captures if Path(str(note["relative"])).parent.as_posix() == "90 Sources/Captures")

    print("# Source Hygiene")
    print()
    print("Mode: report-only. No files were changed.")
    print(f"Vault: {vault}")
    print()
    print("## Summary")
    print(f"- Capture files: {len(captures)}")
    print(f"- Total capture words: {total_words}")
    print(f"- Average capture words: {average_words}")
    print(f"- Oversized threshold: {words} words")
    print(f"- Oversized captures: {len(oversized)}")
    print(f"- Captures without durable-note backlinks: {len(missing_durable_backlinks)}")
    print(f"- Captures missing from Source Log: {len(missing_source_log)}")
    print(f"- Captures with empty extraction targets: {len(empty_extraction_targets)}")
    print(f"- Root capture files: {root_capture_count}")
    print()

    print("## Largest Captures")
    for words_count, relative in sorted(largest, reverse=True)[:max_items]:
        print(f"- {relative}: {words_count} words")

    print()
    print("## Oversized Captures")
    if oversized:
        for words_count, relative, headings in sorted(oversized, reverse=True)[:max_items]:
            split_hint = "split by headings/topics" if headings >= 3 else "split by topic or date range"
            print(f"- {relative}: {words_count} words, {headings} headings ({split_hint})")
    else:
        print("- None")

    print()
    print("## Sources Without Durable Backlinks")
    if missing_durable_backlinks:
        for words_count, relative, inbound_count in sorted(missing_durable_backlinks, reverse=True)[:max_items]:
            print(f"- {relative}: {words_count} words, {inbound_count} total inbound links")
    else:
        print("- None")

    print()
    print("## Source Log Gaps")
    for relative in missing_source_log[:max_items] or ["None"]:
        print(f"- {relative}")

    print()
    print("## Empty Extraction Targets")
    for relative in empty_extraction_targets[:max_items] or ["None"]:
        print(f"- {relative}")

    print()
    print("## Imported Or Bulk Sources To Review")
    if import_review:
        for words_count, relative, durable_links in sorted(import_review, reverse=True)[:max_items]:
            print(f"- {relative}: {words_count} words, {durable_links} durable backlinks")
    else:
        print("- None")

    print()
    print(f"## Stale Unextracted Sources ({stale_days}+ days)")
    if stale_unextracted:
        for created_raw, words_count, relative in sorted(stale_unextracted)[:max_items]:
            print(f"- {relative}: created {created_raw}, {words_count} words")
    else:
        print("- None")

    print()
    print("## Recommendations")
    if root_capture_count >= 200:
        print("- Consider monthly capture folders like `90 Sources/Captures/YYYY/MM/` before the root folder gets annoying.")
    if oversized:
        print("- Split oversized captures into topic/date chunks, then keep the original only if it is still useful as source evidence.")
    if missing_durable_backlinks:
        print("- Extract durable notes from unreferenced sources or mark them as archive-only if they are just evidence.")
    if empty_extraction_targets:
        print("- Fill extraction targets after capture, or remove the empty scaffold from future captures if it becomes visual clutter.")
    if not (oversized or missing_durable_backlinks or empty_extraction_targets or root_capture_count >= 200):
        print("- Source folder is healthy. Keep captures small, topic-shaped, and linked to durable notes.")

def dedupe_memory(vault: Path, min_words: int) -> None:
    vault = require_vault(vault)
    normalized_lines: dict[str, list[tuple[str, str]]] = defaultdict(list)
    title_map: dict[str, list[str]] = defaultdict(list)

    for note in note_inventory(vault):
        if note["is_template"]:
            continue
        title_map[str(note["title"]).lower()].append(str(note["relative"]))
        for line in bullet_lines(str(note["body"])):
            cleaned = clean_bullet(line)
            if len(cleaned.split()) >= min_words:
                normalized_lines[cleaned].append((str(note["relative"]), line))

    duplicate_titles = {title: paths for title, paths in title_map.items() if len(paths) > 1}
    duplicate_lines = {line: hits for line, hits in normalized_lines.items() if len(hits) > 1}

    print("# Dedupe Memory")
    print()
    print("Mode: report-only. No files were changed.")
    print()
    print(f"Duplicate titles: {len(duplicate_titles)}")
    for title, paths in list(duplicate_titles.items())[:25]:
        print(f"- {title}: {', '.join(paths)}")
    print()
    print(f"Duplicate/similar durable bullets: {len(duplicate_lines)}")
    for _, hits in sorted(duplicate_lines.items(), key=lambda item: len(item[1]), reverse=True)[:25]:
        print("- Possible duplicate:")
        for relative, original in hits[:5]:
            print(f"  - {relative}: {original}")

def find_gaps(vault: Path) -> None:
    vault = require_vault(vault)
    notes = note_inventory(vault)
    queued = extract_section_bullets(vault, "00 System/Question Queue.md", "Next Questions")
    open_threads = extract_section_bullets(vault, "00 System/Open Threads.md", "Active Threads")
    thin_notes = []
    uncertain_notes = []
    placeholder_notes = []

    for note in notes:
        relative = str(note["relative"])
        if note["is_template"] or note["is_source"] or relative.startswith("90 Sources/"):
            continue
        frontmatter_data = note["frontmatter"]
        body = str(note["body"])
        if not relative.startswith("00 System/") and str(frontmatter_data.get("confidence", "")).lower() in {"uncertain", "inferred"}:
            uncertain_notes.append(relative)
        if not relative.startswith("00 System/") and re.search(r"\b(uncertain|stale|conflict|placeholder|needs clarification)\b", body, re.I):
            uncertain_notes.append(relative)
        if re.search(r"(?m)^-\s*$|\{\{[^}]+\}\}", body):
            placeholder_notes.append(relative)
        if int(note["words"]) < DEFAULT_THIN_NOTE_WORDS and str(frontmatter_data.get("type")) in {"index", "person", "project", "work", "identity", "preference"}:
            thin_notes.append((int(note["words"]), relative))

    print("# Find Gaps")
    print()
    print(f"Vault: {vault}")
    print()
    print("## Queued Questions")
    for item in queued[:12] or ["None"]:
        print(f"- {item}")
    print()
    print("## Open Threads")
    for item in open_threads[:12] or ["None"]:
        print(f"- {item}")
    print()
    print("## Thin Notes")
    for count, relative in sorted(thin_notes)[:20]:
        print(f"- {relative}: {count} words")
    print()
    print("## Uncertain Or Conflict Areas")
    for relative in sorted(set(uncertain_notes))[:25] or ["None"]:
        print(f"- {relative}")
    print()
    print("## Placeholder-Looking Notes")
    for relative in sorted(set(placeholder_notes))[:25] or ["None"]:
        print(f"- {relative}")

def thin_note_candidates(vault: Path, words: int, include_system: bool = False) -> list[dict[str, object]]:
    candidates = []
    for note in note_inventory(vault):
        relative = str(note["relative"])
        if note["is_template"] or note["is_source"] or relative.startswith("90 Sources/"):
            continue
        if relative.startswith("00 System/") and not include_system:
            continue
        note_type = as_string(note["frontmatter"].get("type"), "missing")
        if int(note["words"]) < words and note_type in {"index", "person", "project", "work", "identity", "preference", "health_metric"}:
            candidates.append(note)
    return sorted(candidates, key=lambda item: (int(item["words"]), str(item["relative"])))

def enrichment_question_for(note: dict[str, object]) -> str:
    note_type = as_string(note["frontmatter"].get("type"), "missing")
    relative = str(note["relative"])
    title = str(note["title"])
    link = wiki_link(relative, title)

    if note_type == "person":
        return (
            f"For {link}, what should Self Atlas remember beyond the label: "
            "your relationship, emotional weight, specific memories, current closeness, "
            "and what future-you should know?"
        )
    if note_type == "project":
        return (
            f"For {link}, what was it really: your role, why it mattered, current status, "
            "what you learned, who was involved, and whether it still matters?"
        )
    if note_type == "work":
        return (
            f"For {link}, what are the real responsibilities, power dynamics, skills, pressure points, "
            "and parts that feel alive or draining?"
        )
    if note_type == "health_metric" or "Health" in relative or "Body" in title:
        return (
            f"For {link}, what body facts or energy patterns should be remembered with dates, units, "
            "frequency, triggers, and context?"
        )
    if note_type == "preference":
        return (
            f"For {link}, what concrete examples prove this preference: products, people, scenes, UI, "
            "writing, music, objects, and anti-examples?"
        )
    return (
        f"For {link}, what are the missing anchors: concrete facts, dates, examples, emotional weight, "
        "source memories, and related people/projects?"
    )

def enrich_thin_notes(vault: Path, words: int, limit: int, apply: bool, include_system: bool) -> None:
    vault = require_vault(vault)
    candidates = thin_note_candidates(vault, words, include_system)
    selected = candidates[: max(1, limit)]
    appended = 0

    print("# Enrich Thin Notes")
    print()
    print(f"Vault: {vault}")
    print(f"Mode: {'append questions to Question Queue' if apply else 'report-only'}")
    print(f"Threshold: fewer than {words} words")
    print(f"Candidates: {len(candidates)}")
    print()

    if not selected:
        print("No thin-note enrichment candidates found.")
        return

    for note in selected:
        question = enrichment_question_for(note)
        line = f"- {question}"
        print(f"- {note['relative']} ({note['frontmatter'].get('type')}, {note['words']} words)")
        print(f"  Question: {question}")
        if apply and append_under_heading(vault / "00 System" / "Question Queue.md", "Next Questions", line):
            appended += 1

    if apply:
        print()
        print(f"Appended questions: {appended}")
        print("No thin-note facts were invented or written.")

def audit(vault: Path) -> None:
    vault = require_vault(vault)
    report = collect_validation(vault)
    notes = report["notes"]
    ds_store_count = len(list(vault.rglob(".DS_Store")))
    large_non_source = [
        note
        for note in notes
        if not note["is_source"] and not note["is_template"] and (int(note["words"]) >= 1200 or int(note["headings"]) >= 7)
    ]
    confidence_counts = Counter(str(note["frontmatter"].get("confidence", "missing")) for note in notes)
    queued = extract_section_bullets(vault, "00 System/Question Queue.md", "Next Questions")
    open_threads = extract_section_bullets(vault, "00 System/Open Threads.md", "Active Threads")

    print("# Self Atlas Audit")
    print()
    print(f"Vault: {vault}")
    print(f"Markdown files: {len(notes)}")
    print(f"Wiki links: {report['total_links']}")
    print(f"Broken links: {len(report['missing_links'])}")
    print(f"Missing frontmatter: {len(report['missing_frontmatter'])}")
    print(f"Missing required metadata: {len(report['missing_metadata'])}")
    print(f"Large non-source notes: {len(large_non_source)}")
    print(f"Queued questions: {len(queued)}")
    print(f"Open threads: {len(open_threads)}")
    print(f".DS_Store files: {ds_store_count}")
    print()
    print("## Confidence")
    for key, count in sorted(confidence_counts.items()):
        print(f"- {key}: {count}")
    if large_non_source:
        print()
        print("## Large Non-Source Notes")
        for note in large_non_source[:20]:
            print(f"- {note['relative']}: {note['words']} words, {note['headings']} headings")
    if report["missing_links"]:
        print()
        print("## Broken Links")
        for relative, target in report["missing_links"][:20]:
            print(f"- {relative} -> [[{target}]]")

def schema_report(vault: Path) -> None:
    vault = require_vault(vault)
    report = collect_validation(vault)
    notes = report["notes"]
    durable = app_durable_notes(notes)
    missing_recommended = []
    missing_sources_field = []
    thin_notes = []
    missing_source_refs = []
    type_counts = Counter(as_string(note["frontmatter"].get("type"), "missing") for note in notes)
    sensitivity_counts = Counter(as_string(note["frontmatter"].get("sensitivity"), "missing") for note in notes)
    confidence_counts = Counter(as_string(note["frontmatter"].get("confidence"), "missing") for note in notes)

    for note in notes:
        if note["is_template"]:
            continue
        frontmatter_data = note["frontmatter"]
        for key in RECOMMENDED_APP_FRONTMATTER:
            if not frontmatter_data.get(key):
                missing_recommended.append((str(note["relative"]), key))

    for note in durable:
        if "sources" not in note["frontmatter"]:
            missing_sources_field.append(str(note["relative"]))
        if int(note["words"]) < DEFAULT_THIN_NOTE_WORDS:
            thin_notes.append((int(note["words"]), str(note["relative"])))
        if not note_has_source_reference(note):
            missing_source_refs.append(str(note["relative"]))

    score = 100
    score -= min(30, len(report["missing_links"]) * 5)
    score -= min(25, (len(report["missing_frontmatter"]) + len(report["missing_metadata"])) * 5)
    score -= min(10, len(report["ambiguous_basename"]) * 2)
    score -= min(15, len(missing_source_refs))
    score -= min(10, len(missing_recommended) // 10)
    score = max(0, score)

    print("# Schema Report")
    print()
    print(f"Vault: {vault}")
    print(f"App-readiness score: {score}/100")
    print()
    print("## Required Schema")
    print(f"- Markdown files: {len(notes)}")
    print(f"- Missing frontmatter: {len(report['missing_frontmatter'])}")
    print(f"- Missing required metadata: {len(report['missing_metadata'])}")
    print(f"- Broken links: {len(report['missing_links'])}")
    print(f"- Ambiguous basenames: {len(report['ambiguous_basename'])}")
    print()
    print("## Recommended App Fields")
    print("- `id` and `schema_version` are recommended, not required.")
    print(f"- Missing recommended fields: {len(missing_recommended)}")
    for relative, key in missing_recommended[:20]:
        print(f"  - {relative}: {key}")
    if len(missing_recommended) > 20:
        print(f"  - ... {len(missing_recommended) - 20} more")
    print()
    print("## Coverage")
    print(f"- Durable notes: {len(durable)}")
    print(f"- Durable notes missing `sources` field: {len(missing_sources_field)}")
    print(f"- Durable notes without obvious source reference: {len(missing_source_refs)}")
    print(f"- Thin durable notes: {len(thin_notes)}")
    print()
    print("## Type Coverage")
    for key, count in sorted(type_counts.items()):
        print(f"- {key}: {count}")
    print()
    print("## Sensitivity Coverage")
    for key, count in sorted(sensitivity_counts.items()):
        print(f"- {key}: {count}")
    print()
    print("## Confidence Coverage")
    for key, count in sorted(confidence_counts.items()):
        print(f"- {key}: {count}")
    if missing_source_refs:
        print()
        print("## Source Reference Gaps")
        for relative in missing_source_refs[:25]:
            print(f"- {relative}")
    if thin_notes:
        print()
        print("## Thin Notes")
        for words_count, relative in sorted(thin_notes)[:25]:
            print(f"- {relative}: {words_count} words")
