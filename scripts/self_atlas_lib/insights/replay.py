from __future__ import annotations

import json
from pathlib import Path

from ..models import DecisionReplayReport
from .core import mode_label, note_ref, rank_notes, safe_note_bullets, visible_inventory


OUTCOME_WORDS = ("outcome", "result", "learned", "proof", "finished", "save", "show", "use", "real", "no longer", "now")


def outcome_signals_from_note(note: dict[str, object], visible_notes: list[dict[str, object]], include_sensitive: bool) -> list[str]:
    signals = []
    for bullet in safe_note_bullets(note, visible_notes, include_sensitive, 8):
        lowered = bullet.lower()
        if any(word in lowered for word in OUTCOME_WORDS):
            signals.append(bullet)
    return signals

def build_decision_replay(
    vault: Path,
    decision: str,
    include_sensitive: bool,
    max_items: int,
) -> dict[str, object]:
    vault, _all_notes, notes, hidden_sensitive = visible_inventory(vault, include_sensitive)
    ranked = rank_notes(notes, decision, None, max_notes=max_items)
    receipts = []
    outcomes = []
    for _score, _reasons, note in ranked:
        receipts.append(note_ref(note, include_excerpt=True, visible_notes=notes, include_sensitive=include_sensitive))
        outcomes.extend(outcome_signals_from_note(note, notes, include_sensitive))
    if not outcomes:
        outcomes.append("No explicit outcome receipt found yet.")
    questions = (
        "What did you actually choose?",
        "What happened after the choice, in concrete artifact or relationship terms?",
        "What did the original decision brief overvalue or miss?",
        "What should Self Atlas remember for the next similar decision?",
    )
    report = DecisionReplayReport(
        decision=decision,
        mode=mode_label(include_sensitive),
        hidden_sensitive=hidden_sensitive,
        receipts=tuple(receipts[:max_items]),
        outcome_signals=tuple(outcomes[:max_items]),
        calibration_questions=questions,
    )
    data = report.to_json()
    data["vault"] = {"name": vault.name}
    return data

def print_decision_replay(vault: Path, decision: str, include_sensitive: bool, max_items: int, json_output: bool) -> None:
    data = build_decision_replay(vault, decision, include_sensitive, max_items)
    if json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("# Decision Replay")
    print()
    print(f"Decision: {data['decision']}")
    print(f"Privacy: {data['mode']} ({data['hidden_sensitive']} sensitive notes hidden)")
    print()
    print("## Outcome Signals")
    for item in data["outcome_signals"]:
        print(f"- {item}")
    print()
    print("## Calibration Questions")
    for item in data["calibration_questions"]:
        print(f"- {item}")
