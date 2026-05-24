from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from ..models import ContradictionSignal
from .core import mode_label, note_confidence, note_matches_lens, note_query_score, note_ref, note_status, visible_inventory

def status_conflict_signal(note: dict[str, object]) -> str | None:
    status = note_status(note).lower()
    body = str(note["body"]).lower()
    if status in {"inactive", "archived", "complete", "completed", "closed"} and re.search(r"\b(active|current|currently|still|now)\b", body):
        return f"Frontmatter says status `{status}`, but the note body sounds active/current."
    if status == "active" and re.search(r"\b(no longer|stopped|ended|archived|marked archived|marked complete|closed)\b", body):
        return "Frontmatter says status `active`, but the note body sounds ended or archived."
    return None

def confidence_conflict_signal(note: dict[str, object]) -> str | None:
    confidence = note_confidence(note).lower()
    body = str(note["body"]).lower()
    if confidence == "confirmed" and re.search(r"\b(uncertain|inferred|maybe|needs clarification|stale)\b", body):
        return "Frontmatter says `confirmed`, but the body contains uncertainty or review language."
    return None

def tension_signal(note: dict[str, object]) -> str | None:
    body = str(note["body"]).lower()
    if re.search(r"\b(contradiction|conflict|tension|tradeoff|however|but now|used to|no longer|instead of)\b", body):
        return "Body contains tension, reversal, or then-vs-now language worth reviewing."
    return None

def duplicate_status_signals(notes: list[dict[str, object]]) -> list[ContradictionSignal]:
    by_title: dict[str, list[dict[str, object]]] = defaultdict(list)
    for note in notes:
        if note["is_template"] or note["is_source"]:
            continue
        by_title[str(note["title"]).lower()].append(note)
    signals = []
    for title, title_notes in by_title.items():
        statuses = {note_status(note).lower() for note in title_notes}
        if len(title_notes) <= 1 or len(statuses) <= 1:
            continue
        primary = sorted(title_notes, key=lambda item: str(item["relative"]))[0]
        evidence = tuple(note_ref(note) for note in sorted(title_notes, key=lambda item: str(item["relative"]))[:4])
        signals.append(
            ContradictionSignal(
                kind="duplicate-status",
                severity="medium",
                path=str(primary["relative"]),
                title=str(primary["title"]),
                signal=f"Multiple notes titled `{title}` have different statuses: {', '.join(sorted(statuses))}.",
                evidence=evidence,
            )
        )
    return signals

def build_contradictions(
    vault: Path,
    query: str,
    lens_id: str | None,
    include_sensitive: bool,
    max_items: int,
) -> dict[str, object]:
    vault, _all_notes, notes, hidden_sensitive = visible_inventory(vault, include_sensitive)
    candidates = [
        note
        for note in notes
        if not note["is_template"]
        and not note["is_source"]
        and not str(note["relative"]).startswith("00 System/")
        and note_matches_lens(note, lens_id)
    ]
    if query:
        matched = []
        for note in candidates:
            score, _reasons = note_query_score(note, query)
            if score:
                matched.append(note)
        candidates = matched
    signals = []
    for note in candidates:
        checks = (
            ("status-conflict", "high", status_conflict_signal(note)),
            ("confidence-conflict", "medium", confidence_conflict_signal(note)),
            ("tension-language", "low", tension_signal(note)),
        )
        for kind, severity, message in checks:
            if message:
                signals.append(
                    ContradictionSignal(
                        kind=kind,
                        severity=severity,
                        path=str(note["relative"]),
                        title=str(note["title"]),
                        signal=message,
                        evidence=(note_ref(note, include_excerpt=True),),
                    )
                )
    signals.extend(duplicate_status_signals(candidates))
    priority = {"high": 0, "medium": 1, "low": 2}
    signals.sort(key=lambda item: (priority.get(item.severity, 9), item.path, item.kind))
    return {
        "vault": {"name": vault.name},
        "mode": mode_label(include_sensitive),
        "hidden_sensitive": hidden_sensitive,
        "query": query,
        "lens": lens_id,
        "counts": {"signals": len(signals)},
        "signals": [signal.to_json() for signal in signals[: max(1, max_items)]],
        "note": "Signals are review leads, not automatic truth judgments.",
    }

def print_contradictions(vault: Path, query: str, lens_id: str | None, include_sensitive: bool, max_items: int, json_output: bool) -> None:
    data = build_contradictions(vault, query, lens_id, include_sensitive, max_items)
    if json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("# Contradiction Engine")
    print()
    print("Mode: read-only. These are review leads, not verdicts.")
    print(f"Privacy: {data['mode']} ({data['hidden_sensitive']} sensitive notes hidden)")
    if query:
        print(f"Query: {query}")
    if lens_id:
        print(f"Lens: {lens_id}")
    print()
    for signal in data["signals"] or [{"path": "None"}]:
        if signal["path"] == "None":
            print("- No contradiction signals found.")
            continue
        print(f"- [{signal['severity']}] {signal['path']}: {signal['signal']}")
