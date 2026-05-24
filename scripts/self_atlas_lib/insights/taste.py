from __future__ import annotations

import json
from pathlib import Path

from ..models import TasteGenomeReport
from ..vault import bullet_lines, clean_bullet
from .core import mode_label, note_matches_lens, note_ref, visible_inventory

MOTION_WORDS = (
    "motion",
    "animation",
    "pacing",
    "rhythm",
    "transition",
    "cinematic",
    "slow",
    "dramatic",
    "alive",
    "replayable",
)

MATERIAL_WORDS = (
    "warm",
    "tactile",
    "texture",
    "textured",
    "grain",
    "soft",
    "visual",
    "poster",
    "artifact",
    "export",
    "emotional",
)

ANTI_TASTE_WORDS = (
    "anti",
    "reject",
    "generic",
    "fake",
    "soulless",
    "cold",
    "dashboard sludge",
    "productivity theater",
    "weak",
    "dead",
    "lifeless",
)

PROOF_WORDS = ("proof", "artifact", "export", "save", "show", "use", "finished", "real")

def unique_preserve(items: list[str], limit: int) -> tuple[str, ...]:
    seen = set()
    output = []
    for item in items:
        cleaned = item.strip()
        key = clean_bullet(cleaned)
        if not cleaned or key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
        if len(output) >= limit:
            break
    return tuple(output)

def build_taste_genome(vault: Path, include_sensitive: bool, max_items: int) -> dict[str, object]:
    vault, _all_notes, notes, hidden_sensitive = visible_inventory(vault, include_sensitive)
    taste_notes = [
        note
        for note in notes
        if not note["is_template"]
        and not note["is_source"]
        and not str(note["relative"]).startswith("00 System/")
        and str(note["relative"]) != "README.md"
        and (note_matches_lens(note, "taste") or note_matches_lens(note, "creative"))
    ]
    bullets = [(note, bullet) for note in taste_notes for bullet in bullet_lines(str(note["body"]))]
    anti = []
    principles = []
    references = []
    proofs = []
    weak_spots = []
    all_text = "\n".join(str(note["body"]) for note in taste_notes).lower()
    for note, bullet in bullets:
        lowered = bullet.lower()
        if any(word in lowered for word in ANTI_TASTE_WORDS):
            anti.append(bullet)
        elif any(word in lowered for word in PROOF_WORDS):
            proofs.append(bullet)
            principles.append(bullet)
        else:
            principles.append(bullet)
        if any(word in lowered for word in ("reference", "song", "music", "palette", "influence")):
            references.append(bullet)
        if any(word in lowered for word in ("risk", "too much", "drained", "weak", "generic", "dead", "setup copy")):
            weak_spots.append(bullet)
    report = TasteGenomeReport(
        mode=mode_label(include_sensitive),
        hidden_sensitive=hidden_sensitive,
        principles=unique_preserve(principles, max_items),
        anti_taste=unique_preserve(anti, max_items),
        references=unique_preserve(references, max_items),
        motion_words=tuple(word for word in MOTION_WORDS if word in all_text),
        material_words=tuple(word for word in MATERIAL_WORDS if word in all_text),
        proof_examples=unique_preserve(proofs, max_items),
        weak_spots=unique_preserve(weak_spots, max_items),
        source_notes=tuple(note_ref(note) for note in taste_notes[:max_items]),
    )
    data = report.to_json()
    data["vault"] = {"name": vault.name}
    data["counts"] = {
        "taste_notes": len(taste_notes),
        "principles": len(data["principles"]),
        "anti_taste": len(data["anti_taste"]),
        "references": len(data["references"]),
        "weak_spots": len(data["weak_spots"]),
    }
    return data

def print_taste_genome(vault: Path, include_sensitive: bool, max_items: int, json_output: bool) -> None:
    data = build_taste_genome(vault, include_sensitive, max_items)
    if json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("# Taste Genome")
    print()
    print(f"Privacy: {data['mode']} ({data['hidden_sensitive']} sensitive notes hidden)")
    print()
    sections = (
        ("Principles", "principles"),
        ("Anti-Taste", "anti_taste"),
        ("References", "references"),
        ("Proof Examples", "proof_examples"),
        ("Weak Spots", "weak_spots"),
    )
    for title, key in sections:
        print(f"## {title}")
        for item in data[key] or ["None"]:
            print(f"- {item}")
        print()
