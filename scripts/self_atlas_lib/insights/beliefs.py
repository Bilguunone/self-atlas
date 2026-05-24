from __future__ import annotations

import json
from pathlib import Path

from ..models import BeliefVersion
from .core import mode_label, note_confidence, note_sensitivity, parse_note_date, rank_notes, safe_note_bullets, visible_inventory


BELIEF_WORDS = (
    "believe",
    "belief",
    "think",
    "used to",
    "now",
    "realized",
    "learned",
    "prefer",
    "reject",
    "value",
    "need",
    "want",
    "fear",
    "taste",
)

CHANGE_WORDS = ("used to", "no longer", "now", "but", "instead", "realized", "learned", "changed")


def belief_change_signal(text: str) -> str | None:
    lowered = text.lower()
    if "used to" in lowered and "now" in lowered:
        return "explicit then-now"
    for word in CHANGE_WORDS:
        if word in lowered:
            return f"contains `{word}`"
    return None

def is_belief_bullet(text: str, query: str) -> bool:
    lowered = text.lower()
    if query and any(token in lowered for token in query.lower().split() if len(token) > 2):
        return True
    return any(word in lowered for word in BELIEF_WORDS)

def build_belief_versioning(
    vault: Path,
    query: str,
    lens_id: str | None,
    include_sensitive: bool,
    max_items: int,
) -> dict[str, object]:
    vault, _all_notes, notes, hidden_sensitive = visible_inventory(vault, include_sensitive)
    ranked_notes = [note for _score, _reasons, note in rank_notes(notes, query, lens_id, max_notes=max_items * 2)]
    versions = []
    for note in ranked_notes:
        date = parse_note_date(note).isoformat() if parse_note_date(note).year > 1 else ""
        for bullet in safe_note_bullets(note, notes, include_sensitive, 24):
            if not is_belief_bullet(bullet, query):
                continue
            versions.append(
                BeliefVersion(
                    text=bullet,
                    date=date,
                    path=str(note["relative"]),
                    title=str(note["title"]),
                    confidence=note_confidence(note),
                    sensitivity=note_sensitivity(note),
                    change_signal=belief_change_signal(bullet),
                )
            )
    versions.sort(key=lambda item: (item.date or "0000-00-00", item.path, item.text))
    versions = versions[:max_items]
    arc = None
    if versions:
        arc = {
            "earliest": versions[0].to_json(),
            "latest": versions[-1].to_json(),
            "reading": "This is a version trail, not a final belief. Check source receipts before declaring an identity law.",
        }
    return {
        "vault": {"name": vault.name},
        "mode": mode_label(include_sensitive),
        "hidden_sensitive": hidden_sensitive,
        "query": query,
        "lens": lens_id,
        "counts": {
            "versions": len(versions),
            "change_signals": sum(1 for item in versions if item.change_signal),
        },
        "versions": [item.to_json() for item in versions],
        "arc": arc,
    }

def print_belief_versioning(vault: Path, query: str, lens_id: str | None, include_sensitive: bool, max_items: int, json_output: bool) -> None:
    data = build_belief_versioning(vault, query, lens_id, include_sensitive, max_items)
    if json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("# Belief Versioning")
    print()
    print(f"Privacy: {data['mode']} ({data['hidden_sensitive']} sensitive notes hidden)")
    if query:
        print(f"Query: {query}")
    if lens_id:
        print(f"Lens: {lens_id}")
    print()
    for item in data["versions"] or [{"path": "None"}]:
        if item["path"] == "None":
            print("- No belief versions found.")
            continue
        marker = f" [{item['change_signal']}]" if item["change_signal"] else ""
        print(f"- {item['date'] or 'unknown'} {item['path']}{marker}: {item['text']}")
