from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ..models import FutureTrajectory
from .core import mode_label, rank_notes, safe_note_bullets, visible_inventory
from .radar import build_open_loop_radar
from .taste import build_taste_genome


def trajectory(name: str, likelihood: str, description: str, signals: list[str], next_move: str) -> FutureTrajectory:
    return FutureTrajectory(
        name=name,
        likelihood=likelihood,
        description=description,
        supporting_signals=tuple(signals[:6]),
        suggested_next_move=next_move,
    )

def build_future_self(
    vault: Path,
    query: str,
    horizon: str,
    include_sensitive: bool,
    max_items: int,
) -> dict[str, object]:
    vault, _all_notes, notes, hidden_sensitive = visible_inventory(vault, include_sensitive)
    ranked = rank_notes(notes, query, None, max_notes=max_items)
    radar = build_open_loop_radar(vault, None, include_sensitive, stale_days=30, max_items=max_items)
    taste = build_taste_genome(vault, include_sensitive, max_items)
    loop_counts = Counter(loop["kind"] for loop in radar["loops"])
    note_signals = []
    for _score, _reasons, note in ranked:
        note_signals.extend(safe_note_bullets(note, notes, include_sensitive, 2))
    trajectories = [
        trajectory(
            "Continue Current Pattern",
            "likely" if radar["loops"] else "low",
            "The current unresolved loops keep shaping the next chapter if nothing interrupts them.",
            [loop["description"] for loop in radar["loops"]],
            "Clear one high-priority open loop before adding new ambition.",
        ),
        trajectory(
            "Proof-First Path",
            "available" if note_signals else "thin",
            "The healthier path is to convert pressure into a visible artifact instead of more planning smoke.",
            note_signals,
            "Pick one artifact receipt that would make the next week feel real.",
        ),
        trajectory(
            "Taste-Protected Path",
            "available" if taste["counts"].get("anti_taste") else "thin",
            "The graph already knows some anti-taste; use it as a guardrail before shipping.",
            list(taste.get("anti_taste", [])) + list(taste.get("weak_spots", [])),
            "Run `taste-autopilot` on the next artifact draft.",
        ),
        trajectory(
            "Drift Risk",
            "watch" if loop_counts["unextracted-source"] or loop_counts["queued-question"] else "low",
            "Loose captures and unanswered questions can turn into vague self-mythology if they never get receipts.",
            [loop["description"] for loop in radar["loops"] if loop["kind"] in {"unextracted-source", "queued-question", "confidence-review"}],
            "Review one source or answer one queued question with dates/examples.",
        ),
    ]
    return {
        "vault": {"name": vault.name},
        "mode": mode_label(include_sensitive),
        "hidden_sensitive": hidden_sensitive,
        "query": query,
        "horizon": horizon,
        "note": "This is pattern simulation, not prophecy. Future-you is not a weather app.",
        "trajectories": [item.to_json() for item in trajectories],
        "radar_counts": radar["counts"],
    }

def print_future_self(vault: Path, query: str, horizon: str, include_sensitive: bool, max_items: int, json_output: bool) -> None:
    data = build_future_self(vault, query, horizon, include_sensitive, max_items)
    if json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("# Future Self Simulator")
    print()
    print(f"Horizon: {data['horizon']}")
    print(f"Privacy: {data['mode']} ({data['hidden_sensitive']} sensitive notes hidden)")
    if query:
        print(f"Query: {query}")
    print()
    for item in data["trajectories"]:
        print(f"## {item['name']} ({item['likelihood']})")
        print(item["description"])
        for signal in item["supporting_signals"]:
            print(f"- {signal}")
        print(f"Next move: {item['suggested_next_move']}")
        print()
