from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from ..constants import EXPORT_SCHEMA_VERSION
from ..timeline import build_timeline
from ..vault import require_vault
from .core import mode_label, query_tokens

def build_time_travel(
    vault: Path,
    query: str,
    thread: str | None,
    include_sensitive: bool,
    max_items: int,
) -> dict[str, object]:
    vault = require_vault(vault)
    timeline = build_timeline(vault, exclude_sensitive=not include_sensitive)
    items = list(timeline["items"])
    if thread:
        items = [item for item in items if thread in item["threads"]]
    if query:
        tokens = query_tokens(query)
        items = [
            item for item in items
            if any(token in json.dumps(item, ensure_ascii=False).lower() for token in tokens)
        ]
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in items:
        key = item["life_period"] or item["date_start"] or item["date_label"] or "undated"
        grouped[key].append(item)
    chapters = []
    for key, chapter_items in sorted(grouped.items()):
        thread_counts = Counter(thread for item in chapter_items for thread in item["threads"])
        pressure_counts = Counter(item["pressure_level"] for item in chapter_items)
        emotional_counts = Counter(item["emotional_charge"] for item in chapter_items)
        chapters.append(
            {
                "id": key,
                "item_count": len(chapter_items),
                "threads": [thread for thread, _ in thread_counts.most_common(5)],
                "pressure_level": pressure_counts.most_common(1)[0][0] if pressure_counts else "unknown",
                "emotional_charge": emotional_counts.most_common(1)[0][0] if emotional_counts else "unknown",
                "first_item": chapter_items[0],
                "last_item": chapter_items[-1],
            }
        )
    then_now = None
    if items:
        then_now = {
            "then": items[0],
            "now": items[-1],
            "shift": "Compare the first and latest receipts before narrating the arc.",
        }
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "vault": {"name": vault.name},
        "mode": mode_label(include_sensitive),
        "query": query,
        "thread": thread,
        "counts": {
            "items": len(items),
            "chapters": len(chapters),
            "hidden_sensitive": timeline["counts"]["excluded_sensitive"] if not include_sensitive else 0,
        },
        "chapters": chapters[: max(1, max_items)],
        "turning_points": [item for item in items if item["turning_point"]][: max(1, max_items)],
        "then_now": then_now,
    }

def print_time_travel(vault: Path, query: str, thread: str | None, include_sensitive: bool, max_items: int, json_output: bool) -> None:
    data = build_time_travel(vault, query, thread, include_sensitive, max_items)
    if json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("# Time Travel")
    print()
    print(f"Privacy: {data['mode']} ({data['counts']['hidden_sensitive']} sensitive timeline items hidden)")
    if query:
        print(f"Query: {query}")
    if thread:
        print(f"Thread: {thread}")
    print()
    for chapter in data["chapters"] or [{"id": "None"}]:
        if chapter["id"] == "None":
            print("- No timeline items found.")
            continue
        print(f"- {chapter['id']}: {chapter['item_count']} items; pressure {chapter['pressure_level']}; charge {chapter['emotional_charge']}")
