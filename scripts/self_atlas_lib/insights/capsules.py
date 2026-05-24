from __future__ import annotations

import json
from pathlib import Path

from ..constants import WIKI_LINK_RE
from ..models import ShareCapsule
from ..vault import link_indexes, normalized_path, resolve_link_target
from .core import mode_label, note_bullets, note_card, rank_notes, visible_inventory, visible_source_refs

def build_share_capsule(
    vault: Path,
    title: str,
    query: str,
    lens_id: str | None,
    include_sensitive: bool,
    yes: bool,
    max_notes: int,
) -> dict[str, object]:
    if include_sensitive and not yes:
        raise SystemExit("Share capsules that include sensitive notes require --yes.")
    vault, _all_notes, notes, hidden_sensitive = visible_inventory(vault, include_sensitive)
    ranked = rank_notes(notes, query, lens_id, max_notes)
    capsule_notes = []
    source_refs = []
    seen_sources = set()
    for score, reasons, note in ranked:
        refs = visible_source_refs(note, notes)
        for ref in refs:
            if ref.path not in seen_sources:
                source_refs.append(ref)
                seen_sources.add(ref.path)
        card = note_card(note, score, reasons)
        card["bullets"] = safe_note_bullets(note, notes, include_sensitive, 3)
        card["sources"] = [ref.path for ref in refs]
        capsule_notes.append(card)
    warnings = []
    if hidden_sensitive:
        warnings.append(f"{hidden_sensitive} sensitive notes were hidden.")
    if include_sensitive:
        warnings.append("Sensitive notes included. Keep this capsule private.")
    if not capsule_notes:
        warnings.append("No matching notes found.")
    capsule = ShareCapsule(
        title=title,
        mode=mode_label(include_sensitive),
        query=query or None,
        lens=lens_id,
        hidden_sensitive=hidden_sensitive,
        notes=tuple(capsule_notes),
        sources=tuple(source_refs),
        warnings=tuple(warnings),
    )
    data = capsule.to_json()
    data["vault"] = {"name": vault.name}
    return data

def safe_note_bullets(
    note: dict[str, object],
    visible_notes: list[dict[str, object]],
    include_sensitive: bool,
    limit: int,
) -> list[str]:
    bullets = note_bullets(note, 12)
    if include_sensitive:
        return bullets[:limit]
    by_key, by_base = link_indexes(visible_notes)
    safe = []
    for bullet in bullets:
        hidden_target = False
        for match in WIKI_LINK_RE.finditer(bullet):
            target_note, ambiguous = resolve_link_target(match.group(1), by_key, by_base)
            if ambiguous or target_note is None:
                hidden_target = True
                break
        if hidden_target:
            continue
        safe.append(bullet)
        if len(safe) >= limit:
            break
    return safe

def capsule_markdown(capsule: dict[str, object]) -> str:
    lines = [
        f"# {capsule['title']}",
        "",
        f"Mode: {capsule['mode']}",
    ]
    if capsule["query"]:
        lines.append(f"Query: {capsule['query']}")
    if capsule["lens"]:
        lines.append(f"Lens: {capsule['lens']}")
    lines.extend(["", "## Notes"])
    for note in capsule["notes"]:
        lines.append(f"- {note['path']} ({note['type']}, {note['confidence']})")
        for bullet in note["bullets"]:
            lines.append(f"  - {bullet}")
        if note["sources"]:
            lines.append(f"  Sources: {', '.join(note['sources'])}")
    lines.extend(["", "## Source Receipts"])
    for source in capsule["sources"]:
        lines.append(f"- {source['path']} ({source['sensitivity']}, {source['confidence']})")
    lines.extend(["", "## Warnings"])
    for warning in capsule["warnings"] or ["None"]:
        lines.append(f"- {warning}")
    return "\n".join(lines) + "\n"

def print_share_capsule(
    vault: Path,
    title: str,
    query: str,
    lens_id: str | None,
    include_sensitive: bool,
    yes: bool,
    max_notes: int,
    out: Path | None,
    json_output: bool,
) -> None:
    data = build_share_capsule(vault, title, query, lens_id, include_sensitive, yes, max_notes)
    if json_output:
        payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    else:
        payload = capsule_markdown(data)
    if out:
        out = normalized_path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")
        print(out)
    else:
        print(payload, end="")
