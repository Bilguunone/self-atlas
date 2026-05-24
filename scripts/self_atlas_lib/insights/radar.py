from __future__ import annotations

import datetime as dt
import json
import re
from collections import Counter
from pathlib import Path

from ..models import OpenLoop
from ..vault import extract_section_bullets
from .contradictions import build_contradictions
from .core import (
    durable_source_backlinks,
    infer_lens_id,
    mode_label,
    note_confidence,
    note_matches_lens,
    note_ref,
    parse_note_date,
    visible_inventory,
)

def visible_system_bullets(
    vault: Path,
    notes: list[dict[str, object]],
    relative: str,
    heading: str,
) -> list[str]:
    visible_relatives = {str(note["relative"]) for note in notes}
    if relative not in visible_relatives:
        return []
    return extract_section_bullets(vault, relative, heading)

def source_log_contains(source_log_text: str, source_key: str) -> bool:
    return source_key in source_log_text or f"{source_key}.md" in source_log_text

def build_open_loop_radar(
    vault: Path,
    lens_id: str | None,
    include_sensitive: bool,
    stale_days: int,
    max_items: int,
) -> dict[str, object]:
    vault, _all_notes, notes, hidden_sensitive = visible_inventory(vault, include_sensitive)
    all_inbound, durable_inbound = durable_source_backlinks(notes)
    loops: list[OpenLoop] = []
    queued = visible_system_bullets(vault, notes, "00 System/Question Queue.md", "Next Questions")
    for item in queued:
        loops.append(OpenLoop("queued-question", "medium", "00 System/Question Queue.md", "Question Queue", item, lens_id))
    open_threads = visible_system_bullets(vault, notes, "00 System/Open Threads.md", "Active Threads")
    for item in open_threads:
        loops.append(OpenLoop("open-thread", "high", "00 System/Open Threads.md", "Open Threads", item, lens_id))
    today_date = dt.date.today()
    stale_cutoff = today_date - dt.timedelta(days=max(1, stale_days))
    source_log_path = vault / "00 System" / "Source Log.md"
    source_log_text = source_log_path.read_text(encoding="utf-8") if source_log_path.exists() else ""
    for note in notes:
        relative = str(note["relative"])
        if note["is_template"]:
            continue
        if lens_id and not note_matches_lens(note, lens_id):
            continue
        if note["is_source"] and durable_inbound[str(note["key"])] == 0:
            priority = "high" if parse_note_date(note) <= stale_cutoff else "medium"
            loops.append(
                OpenLoop(
                    "unextracted-source",
                    priority,
                    relative,
                    str(note["title"]),
                    f"Source has {all_inbound[str(note['key'])]} inbound links and no durable-note backlink.",
                    infer_lens_id(note),
                    (note_ref(note),),
                )
            )
        if note["is_source"] and not source_log_contains(source_log_text, str(note["key"])):
            loops.append(
                OpenLoop(
                    "source-log-gap",
                    "medium",
                    relative,
                    str(note["title"]),
                    "Source capture is missing from Source Log.",
                    infer_lens_id(note),
                    (note_ref(note),),
                )
            )
        if not note["is_source"] and note_confidence(note).lower() in {"uncertain", "inferred", "missing"}:
            loops.append(
                OpenLoop(
                    "confidence-review",
                    "medium",
                    relative,
                    str(note["title"]),
                    f"Confidence is `{note_confidence(note)}`.",
                    infer_lens_id(note),
                    (note_ref(note),),
                )
            )
        if not note["is_source"] and re.search(r"\b(stale|conflict|needs clarification|placeholder)\b", str(note["body"]), re.I):
            loops.append(
                OpenLoop(
                    "review-language",
                    "medium",
                    relative,
                    str(note["title"]),
                    "Body contains stale/conflict/placeholder review language.",
                    infer_lens_id(note),
                    (note_ref(note, include_excerpt=True),),
                )
            )
    contradiction_data = build_contradictions(vault, "", lens_id, include_sensitive, max_items)
    for signal in contradiction_data["signals"]:
        loops.append(
            OpenLoop(
                "contradiction-signal",
                "high" if signal["severity"] == "high" else "medium",
                signal["path"],
                signal["title"],
                signal["signal"],
                lens_id,
            )
        )
    priority_sort = {"high": 0, "medium": 1, "low": 2}
    loops.sort(key=lambda loop: (priority_sort.get(loop.priority, 9), loop.kind, loop.path, loop.description))
    counts = Counter(loop.kind for loop in loops)
    return {
        "vault": {"name": vault.name},
        "mode": mode_label(include_sensitive),
        "hidden_sensitive": hidden_sensitive,
        "lens": lens_id,
        "stale_days": stale_days,
        "counts": dict(sorted(counts.items())) | {"total": len(loops)},
        "loops": [loop.to_json() for loop in loops[: max(1, max_items)]],
        "recommendations": open_loop_recommendations(loops),
    }

def open_loop_recommendations(loops: list[OpenLoop]) -> list[str]:
    kinds = Counter(loop.kind for loop in loops)
    recommendations = []
    if kinds["open-thread"]:
        recommendations.append("Walk one active thread before adding another question.")
    if kinds["unextracted-source"]:
        recommendations.append("Run `capture-review` on the oldest unextracted source.")
    if kinds["contradiction-signal"]:
        recommendations.append("Review the highest-severity contradiction signal before treating the note as settled.")
    if kinds["queued-question"]:
        recommendations.append("Ask one queued question that can update multiple notes.")
    if not recommendations:
        recommendations.append("No urgent open loops. Capture a fresh artifact or deepen a thin note.")
    return recommendations[:4]

def print_open_loop_radar(vault: Path, lens_id: str | None, include_sensitive: bool, stale_days: int, max_items: int, json_output: bool) -> None:
    data = build_open_loop_radar(vault, lens_id, include_sensitive, stale_days, max_items)
    if json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("# Open Loop Radar")
    print()
    print("Mode: read-only. No files were changed.")
    print(f"Privacy: {data['mode']} ({data['hidden_sensitive']} sensitive notes hidden)")
    if lens_id:
        print(f"Lens: {lens_id}")
    print()
    print("## Loops")
    for item in data["loops"] or [{"path": "None"}]:
        if item["path"] == "None":
            print("- None")
            continue
        print(f"- [{item['priority']}] {item['kind']}: {item['path']} - {item['description']}")
    print()
    print("## Best Next Moves")
    for item in data["recommendations"]:
        print(f"- {item}")
