from __future__ import annotations

import datetime as dt
import json
import re
from collections import Counter, defaultdict, deque
from pathlib import Path

from .constants import DEFAULT_THIN_NOTE_WORDS
from .export import note_is_excluded_sensitive
from .vault import (
    as_list,
    as_string,
    bullet_lines,
    collect_validation,
    extract_section_bullets,
    link_indexes,
    note_inventory,
    require_vault,
    resolve_link_target,
    wiki_link,
)


def note_kind(note: dict[str, object]) -> str:
    return as_string(note["frontmatter"].get("type"), "missing")

def note_sensitivity(note: dict[str, object]) -> str:
    return as_string(note["frontmatter"].get("sensitivity"), "normal")

def note_confidence(note: dict[str, object]) -> str:
    return as_string(note["frontmatter"].get("confidence"), "missing")

def visible_notes(notes: list[dict[str, object]], include_sensitive: bool) -> tuple[list[dict[str, object]], int]:
    hidden = 0
    visible = []
    for note in notes:
        if not include_sensitive and note_is_excluded_sensitive(note):
            hidden += 1
            continue
        visible.append(note)
    return visible, hidden

def parse_note_date(note: dict[str, object]) -> dt.date:
    for key in ("updated", "created"):
        raw = as_string(note["frontmatter"].get(key))
        try:
            return dt.date.fromisoformat(raw)
        except ValueError:
            continue
    return dt.date.min

def useful_bullets(note: dict[str, object], limit: int = 2) -> list[str]:
    bullets = []
    for bullet in bullet_lines(str(note["body"])):
        if re.search(r"\{\{[^}]+\}\}", bullet):
            continue
        if bullet.strip() in {"None", ""}:
            continue
        bullets.append(bullet)
        if len(bullets) >= limit:
            break
    return bullets

def source_backlink_counts(notes: list[dict[str, object]]) -> tuple[Counter[str], Counter[str]]:
    by_key, by_base = link_indexes(notes)
    source_keys = {str(note["key"]) for note in notes if note["is_source"]}
    durable_keys = {
        str(note["key"])
        for note in notes
        if not note["is_source"] and not note["is_template"] and not str(note["relative"]).startswith("00 System/")
    }
    all_inbound: Counter[str] = Counter()
    durable_inbound: Counter[str] = Counter()

    for note in notes:
        from_key = str(note["key"])
        for target in note["links"]:
            target_note, ambiguous = resolve_link_target(str(target), by_key, by_base)
            if ambiguous or not target_note:
                continue
            target_key = str(target_note["key"])
            if target_key not in source_keys:
                continue
            all_inbound[target_key] += 1
            if from_key in durable_keys:
                durable_inbound[target_key] += 1
    return all_inbound, durable_inbound

def build_pulse(vault: Path, include_sensitive: bool, max_items: int) -> dict[str, object]:
    vault = require_vault(vault)
    report = collect_validation(vault)
    all_notes = report["notes"]
    notes, hidden_sensitive = visible_notes(all_notes, include_sensitive)
    note_by_relative = {str(note["relative"]): note for note in all_notes}

    def visible_section_bullets(relative: str, section: str) -> list[str]:
        note = note_by_relative.get(relative)
        if note and not include_sensitive and note_is_excluded_sensitive(note):
            return []
        return extract_section_bullets(vault, relative, section)

    queued = visible_section_bullets("00 System/Question Queue.md", "Next Questions")
    open_threads = visible_section_bullets("00 System/Open Threads.md", "Active Threads")

    captures = [note for note in notes if note["is_source"] and not note["is_template"]]
    recent_captures = sorted(captures, key=parse_note_date, reverse=True)[:max_items]
    _, durable_inbound = source_backlink_counts(notes)
    unextracted_sources = [
        note
        for note in captures
        if durable_inbound[str(note["key"])] == 0
    ]
    uncertain_notes = [
        note
        for note in notes
        if not note["is_source"]
        and not note["is_template"]
        and not str(note["relative"]).startswith("00 System/")
        and note_confidence(note).lower() in {"uncertain", "inferred", "missing"}
    ]
    thin_notes = [
        note
        for note in notes
        if not note["is_source"]
        and not note["is_template"]
        and not str(note["relative"]).startswith("00 System/")
        and int(note["words"]) < DEFAULT_THIN_NOTE_WORDS
        and note_kind(note) in {"identity", "person", "project", "work", "preference", "pattern", "index"}
    ]

    inbound: Counter[str] = Counter()
    by_key, by_base = link_indexes(notes)
    for note in notes:
        for target in note["links"]:
            target_note, ambiguous = resolve_link_target(str(target), by_key, by_base)
            if ambiguous or not target_note:
                continue
            inbound[str(target_note["key"])] += 1
    note_by_key = {str(note["key"]): note for note in notes}
    hubs = [
        note_by_key[key]
        for key, _ in inbound.most_common()
        if key in note_by_key and not note_by_key[key]["is_template"]
    ][:max_items]

    recommendations = []
    if report["missing_links"]:
        recommendations.append("Run `validate-links` before adding more structure.")
    if unextracted_sources:
        recommendations.append("Review the most recent unextracted source with `capture-review`.")
    if open_threads:
        recommendations.append("Walk one active thread with `thread-walk` instead of asking a generic question.")
    if queued:
        recommendations.append("Ask the first queued question if the user wants momentum.")
    if thin_notes:
        recommendations.append("Use `enrich-thin-notes` on the thinnest important note.")
    if not recommendations:
        recommendations.append("Capture one fresh answer or artifact; the graph is clean enough to grow.")

    return {
        "vault": {"name": vault.name},
        "mode": "private" if include_sensitive else "share-safe",
        "counts": {
            "notes": len(notes),
            "all_notes": len(all_notes),
            "hidden_sensitive": hidden_sensitive,
            "source_notes": len(captures),
            "queued_questions": len(queued),
            "open_threads": len(open_threads),
            "unextracted_sources": len(unextracted_sources),
            "thin_notes": len(thin_notes),
            "uncertain_notes": len(uncertain_notes),
            "broken_links": len(report["missing_links"]),
        },
        "open_threads": open_threads[:max_items],
        "queued_questions": queued[:max_items],
        "recent_captures": [
            {
                "path": str(note["relative"]),
                "title": str(note["title"]),
                "updated": as_string(note["frontmatter"].get("updated")),
                "words": int(note["words"]),
                "sensitivity": note_sensitivity(note),
            }
            for note in recent_captures
        ],
        "unextracted_sources": [
            {
                "path": str(note["relative"]),
                "title": str(note["title"]),
                "words": int(note["words"]),
                "updated": as_string(note["frontmatter"].get("updated")),
            }
            for note in sorted(unextracted_sources, key=parse_note_date, reverse=True)[:max_items]
        ],
        "thin_notes": [
            {
                "path": str(note["relative"]),
                "title": str(note["title"]),
                "type": note_kind(note),
                "words": int(note["words"]),
            }
            for note in sorted(thin_notes, key=lambda item: int(item["words"]))[:max_items]
        ],
        "uncertain_notes": [
            {
                "path": str(note["relative"]),
                "title": str(note["title"]),
                "confidence": note_confidence(note),
            }
            for note in uncertain_notes[:max_items]
        ],
        "hubs": [
            {
                "path": str(note["relative"]),
                "title": str(note["title"]),
                "inbound": inbound[str(note["key"])],
            }
            for note in hubs
        ],
        "recommendations": recommendations[:4],
    }

def print_pulse(vault: Path, include_sensitive: bool, max_items: int, json_output: bool = False) -> None:
    pulse = build_pulse(vault, include_sensitive, max_items)
    if json_output:
        print(json.dumps(pulse, ensure_ascii=False, indent=2))
        return
    counts = pulse["counts"]
    print("# Pulse")
    print()
    print("Mode: read-only. No files were changed.")
    print(f"Privacy: {pulse['mode']} ({counts['hidden_sensitive']} sensitive notes hidden)")
    print(f"Vault: {pulse['vault']['name']}")
    print()
    print("## Now")
    print(f"- Notes visible: {counts['notes']} of {counts['all_notes']}")
    print(f"- Open threads: {counts['open_threads']}")
    print(f"- Queued questions: {counts['queued_questions']}")
    print(f"- Recent source captures: {counts['source_notes']}")
    print(f"- Unextracted sources: {counts['unextracted_sources']}")
    print(f"- Thin notes: {counts['thin_notes']}")
    print(f"- Uncertain notes: {counts['uncertain_notes']}")
    print(f"- Broken links: {counts['broken_links']}")
    print()
    print("## Active Threads")
    for item in pulse["open_threads"] or ["None"]:
        print(f"- {item}")
    print()
    print("## Next Questions")
    for item in pulse["queued_questions"] or ["None"]:
        print(f"- {item}")
    print()
    print("## Recent Captures")
    for item in pulse["recent_captures"] or [{"path": "None"}]:
        if item["path"] == "None":
            print("- None")
        else:
            print(f"- {item['path']} ({item['words']} words, {item['sensitivity']})")
    print()
    print("## Needs Attention")
    if not pulse["unextracted_sources"] and not pulse["thin_notes"] and not pulse["uncertain_notes"]:
        print("- Nothing urgent. Annoyingly healthy.")
    for item in pulse["unextracted_sources"][:max_items]:
        print(f"- Unextracted source: {item['path']} ({item['words']} words)")
    for item in pulse["thin_notes"][:max_items]:
        print(f"- Thin {item['type']}: {item['path']} ({item['words']} words)")
    for item in pulse["uncertain_notes"][:max_items]:
        print(f"- Confidence review: {item['path']} ({item['confidence']})")
    print()
    print("## Strong Hubs")
    for item in pulse["hubs"] or [{"path": "None"}]:
        if item["path"] == "None":
            print("- None")
        else:
            print(f"- {item['path']}: {item['inbound']} inbound links")
    print()
    print("## Best Next Moves")
    for item in pulse["recommendations"]:
        print(f"- {item}")

def query_tokens(query: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9][a-z0-9'-]{1,}", query.lower()) if len(token) > 2]

def note_query_score(note: dict[str, object], query: str, tokens: list[str]) -> tuple[int, list[str]]:
    title = str(note["title"]).lower()
    relative = str(note["relative"]).lower()
    tags = " ".join(as_list(note["frontmatter"].get("tags"))).lower()
    body = str(note["body"]).lower()
    query_lower = query.lower().strip()
    score = 0
    reasons = []

    if query_lower and query_lower in title:
        score += 12
        reasons.append("title")
    if query_lower and query_lower in relative:
        score += 10
        reasons.append("path")
    if query_lower and query_lower in tags:
        score += 8
        reasons.append("tags")
    for token in tokens:
        if token in title:
            score += 5
        if token in relative:
            score += 4
        if token in tags:
            score += 3
        if token in body:
            score += 1
    if score and not reasons:
        reasons.append("body")
    return score, sorted(set(reasons))

def build_thread_walk(
    vault: Path,
    query: str,
    include_sensitive: bool,
    depth: int,
    max_notes: int,
) -> dict[str, object]:
    vault = require_vault(vault)
    all_notes = note_inventory(vault)
    notes, hidden_sensitive = visible_notes(all_notes, include_sensitive)
    notes = [note for note in notes if not note["is_template"]]
    tokens = query_tokens(query)
    scored = []
    for note in notes:
        score, reasons = note_query_score(note, query, tokens)
        if score:
            scored.append((score, str(note["key"]), reasons, note))
    scored.sort(key=lambda item: (-item[0], str(item[3]["relative"])))
    durable_scored = [
        item
        for item in scored
        if not str(item[3]["relative"]).startswith("00 System/")
        and not item[3]["is_source"]
        and str(item[3]["relative"]) != "README.md"
    ]
    starts = (durable_scored or scored)[: min(5, max_notes)]

    by_key, by_base = link_indexes(notes)
    adjacency: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for note in notes:
        from_key = str(note["key"])
        for target in note["links"]:
            target_note, ambiguous = resolve_link_target(str(target), by_key, by_base)
            if ambiguous or not target_note:
                continue
            to_key = str(target_note["key"])
            if to_key == from_key:
                continue
            adjacency[from_key].append((to_key, str(target)))
            adjacency[to_key].append((from_key, from_key))

    visited: dict[str, dict[str, object]] = {}
    queue: deque[tuple[str, int, str | None, str | None]] = deque()
    for score, key, reasons, _note in starts:
        visited[key] = {
            "depth": 0,
            "via": None,
            "via_label": None,
            "match_score": score,
            "match_reasons": reasons,
        }
        queue.append((key, 0, None, None))

    while queue and len(visited) < max_notes:
        key, current_depth, _via, _via_label = queue.popleft()
        if current_depth >= depth:
            continue
        for neighbor, label in sorted(adjacency.get(key, []), key=lambda item: item[0]):
            if neighbor in visited:
                continue
            visited[neighbor] = {
                "depth": current_depth + 1,
                "via": key,
                "via_label": label,
                "match_score": 0,
                "match_reasons": [],
            }
            queue.append((neighbor, current_depth + 1, key, label))
            if len(visited) >= max_notes:
                break

    note_by_key = {str(note["key"]): note for note in notes}
    included_keys = set(visited)
    edges = []
    seen_edges = set()
    for from_key in included_keys:
        for to_key, label in adjacency.get(from_key, []):
            if to_key not in included_keys:
                continue
            edge_key = tuple(sorted((from_key, to_key)))
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            edges.append(
                {
                    "from": str(note_by_key[from_key]["relative"]),
                    "to": str(note_by_key[to_key]["relative"]),
                    "label": label,
                }
            )
    walk_items = []
    for key, meta in sorted(visited.items(), key=lambda item: (int(item[1]["depth"]), str(note_by_key[item[0]]["relative"]))):
        note = note_by_key[key]
        via = meta["via"]
        walk_items.append(
            {
                "path": str(note["relative"]),
                "title": str(note["title"]),
                "type": note_kind(note),
                "sensitivity": note_sensitivity(note),
                "confidence": note_confidence(note),
                "depth": int(meta["depth"]),
                "via": str(note_by_key[via]["relative"]) if via and via in note_by_key else None,
                "match_score": int(meta["match_score"]),
                "match_reasons": list(meta["match_reasons"]),
                "bullets": useful_bullets(note, 2) if include_sensitive else [],
            }
        )

    return {
        "vault": {"name": vault.name},
        "query": query,
        "mode": "private" if include_sensitive else "share-safe",
        "hidden_sensitive": hidden_sensitive,
        "start_count": len(starts),
        "items": walk_items,
        "edges": sorted(edges, key=lambda item: (item["from"], item["to"])),
    }

def print_thread_walk(vault: Path, query: str, include_sensitive: bool, depth: int, max_notes: int, json_output: bool = False) -> None:
    result = build_thread_walk(vault, query, include_sensitive, depth, max_notes)
    if json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print("# Thread Walk")
    print()
    print("Mode: read-only. No files were changed.")
    print(f"Privacy: {result['mode']} ({result['hidden_sensitive']} sensitive notes hidden)")
    print(f"Query: {result['query']}")
    print(f"Vault: {result['vault']['name']}")
    print()
    if not result["items"]:
        print("No thread found. Try a project/person/taste word that exists in the graph.")
        return

    current_depth = -1
    for item in result["items"]:
        if item["depth"] != current_depth:
            current_depth = item["depth"]
            print()
            print(f"## Depth {current_depth}")
        label = wiki_link(item["path"].removesuffix(".md"), item["title"])
        meta = f"{item['type']}, {item['sensitivity']}, {item['confidence']}"
        print(f"- {label} ({meta})")
        if item["depth"] == 0:
            reasons = ", ".join(item["match_reasons"]) or "query"
            print(f"  Why: matched {reasons} (score {item['match_score']})")
        elif item["via"]:
            print(f"  Why: linked from `{item['via']}`")
        for bullet in item["bullets"]:
            print(f"  - {bullet}")

def build_answer_context(
    vault: Path,
    query: str,
    include_sensitive: bool,
    max_notes: int,
) -> dict[str, object]:
    vault = require_vault(vault)
    all_notes = note_inventory(vault)
    notes, hidden_sensitive = visible_notes(all_notes, include_sensitive)
    notes = [note for note in notes if not note["is_template"]]
    by_key, by_base = link_indexes(notes)
    note_by_key = {str(note["key"]): note for note in notes}
    tokens = query_tokens(query)
    scored = []
    for note in notes:
        if note["is_source"] or str(note["relative"]).startswith("00 System/") or str(note["relative"]) == "README.md":
            continue
        score, reasons = note_query_score(note, query, tokens)
        if score:
            scored.append((score, reasons, note))
    scored.sort(key=lambda item: (-item[0], str(item[2]["relative"])))
    selected = scored[:max_notes]

    source_receipts = []
    source_seen = set()
    linked_notes = []
    confidence_counts = Counter()
    sensitivity_counts = Counter()
    review_flags = []
    visible_sources_by_note: dict[str, list[str]] = {}

    for score, reasons, note in selected:
        confidence_counts[note_confidence(note)] += 1
        sensitivity_counts[note_sensitivity(note)] += 1
        body = str(note["body"])
        if re.search(r"\b(uncertain|inferred|stale|conflict|needs clarification)\b", body, re.I):
            review_flags.append(f"{note['relative']} contains review language.")
        visible_note_sources = []
        for source in as_list(note["frontmatter"].get("sources")):
            source_key = source.removesuffix(".md")
            source_note = note_by_key.get(source_key)
            if source_note:
                visible_note_sources.append(source)
            if source_note and source_key not in source_seen:
                source_seen.add(source_key)
                source_receipts.append(
                    {
                        "path": str(source_note["relative"]),
                        "title": str(source_note["title"]),
                        "sensitivity": note_sensitivity(source_note),
                        "confidence": note_confidence(source_note),
                    }
                )
        visible_sources_by_note[str(note["key"])] = visible_note_sources
        for target in note["links"]:
            target_note, ambiguous = resolve_link_target(str(target), by_key, by_base)
            if ambiguous or not target_note or target_note["is_source"]:
                continue
            linked_notes.append(str(target_note["relative"]))

    return {
        "vault": {"name": vault.name},
        "query": query,
        "mode": "private" if include_sensitive else "share-safe",
        "hidden_sensitive": hidden_sensitive,
        "counts": {
            "matching_notes": len(scored),
            "returned_notes": len(selected),
            "source_receipts": len(source_receipts),
            "linked_notes": len(set(linked_notes)),
            "review_flags": len(review_flags),
        },
        "confidence": dict(sorted(confidence_counts.items())),
        "sensitivity": dict(sorted(sensitivity_counts.items())),
        "notes": [
            {
                "path": str(note["relative"]),
                "title": str(note["title"]),
                "type": note_kind(note),
                "sensitivity": note_sensitivity(note),
                "confidence": note_confidence(note),
                "score": score,
                "match_reasons": reasons,
                "bullets": useful_bullets(note, 3) if include_sensitive else [],
                "sources": visible_sources_by_note.get(str(note["key"]), []),
            }
            for score, reasons, note in selected
        ],
        "source_receipts": source_receipts[:max_notes],
        "linked_notes": sorted(set(linked_notes))[:max_notes],
        "review_flags": sorted(set(review_flags))[:max_notes],
    }

def print_answer_context(vault: Path, query: str, include_sensitive: bool, max_notes: int, json_output: bool) -> None:
    context = build_answer_context(vault, query, include_sensitive, max_notes)
    if json_output:
        print(json.dumps(context, ensure_ascii=False, indent=2))
        return

    print("# Answer Context")
    print()
    print("Mode: read-only. No files were changed.")
    print(f"Privacy: {context['mode']} ({context['hidden_sensitive']} sensitive notes hidden)")
    print(f"Query: {context['query']}")
    print(f"Vault: {context['vault']['name']}")
    print()
    print("## Counts")
    for key, value in context["counts"].items():
        print(f"- {key}: {value}")
    print()
    print("## Notes")
    for item in context["notes"] or [{"path": "None"}]:
        if item["path"] == "None":
            print("- None")
            continue
        print(f"- {item['path']} ({item['type']}, {item['confidence']}, score {item['score']})")
        if item["sources"]:
            print(f"  Sources: {', '.join(item['sources'])}")
        for bullet in item["bullets"]:
            print(f"  - {bullet}")
    print()
    print("## Source Receipts")
    for item in context["source_receipts"] or [{"path": "None"}]:
        if item["path"] == "None":
            print("- None")
        else:
            print(f"- {item['path']} ({item['sensitivity']}, {item['confidence']})")
    print()
    print("## Review Flags")
    for item in context["review_flags"] or ["None"]:
        print(f"- {item}")
