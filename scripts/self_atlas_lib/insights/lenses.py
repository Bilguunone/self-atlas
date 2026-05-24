from __future__ import annotations

import json
from pathlib import Path

from .core import LENS_BY_ID, LIFE_LENSES, mode_label, note_card, note_matches_lens, rank_notes, visible_inventory

def build_life_lenses(
    vault: Path,
    lens_id: str | None,
    query: str,
    include_sensitive: bool,
    max_notes: int,
) -> dict[str, object]:
    vault, _all_notes, notes, hidden_sensitive = visible_inventory(vault, include_sensitive)
    if lens_id and lens_id not in LENS_BY_ID:
        raise SystemExit(f"Unknown life lens: {lens_id}")
    counts = {
        lens.id: sum(1 for note in notes if note_matches_lens(note, lens.id) and not note["is_template"])
        for lens in LIFE_LENSES
    }
    selected = [
        {
            "lens": (LENS_BY_ID[lens_id].to_json() if lens_id else None),
            "notes": [
                note_card(note, score, reasons)
                for score, reasons, note in rank_notes(notes, query, lens_id, max_notes)
            ],
        }
    ] if lens_id else []
    return {
        "vault": {"name": vault.name},
        "mode": mode_label(include_sensitive),
        "hidden_sensitive": hidden_sensitive,
        "query": query,
        "lens": lens_id,
        "lenses": [lens.to_json() | {"visible_notes": counts[lens.id]} for lens in LIFE_LENSES],
        "selection": selected,
    }

def print_life_lenses(vault: Path, lens_id: str | None, query: str, include_sensitive: bool, max_notes: int, json_output: bool) -> None:
    data = build_life_lenses(vault, lens_id, query, include_sensitive, max_notes)
    if json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("# Life Lenses")
    print()
    print(f"Mode: {data['mode']} ({data['hidden_sensitive']} sensitive notes hidden)")
    if lens_id:
        lens = LENS_BY_ID[lens_id]
        print(f"Lens: {lens.title}")
        if query:
            print(f"Query: {query}")
        print()
        print("## Notes")
        notes = data["selection"][0]["notes"] if data["selection"] else []
        for item in notes or [{"path": "None"}]:
            if item["path"] == "None":
                print("- None")
                continue
            print(f"- {item['path']} ({item['type']}, {item['confidence']}, score {item['score']})")
            for bullet in item["bullets"]:
                print(f"  - {bullet}")
        return
    print("Available lenses:")
    for lens in data["lenses"]:
        print(f"- {lens['id']}: {lens['title']} ({lens['visible_notes']} visible notes)")
