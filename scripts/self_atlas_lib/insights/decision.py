from __future__ import annotations

import json
from pathlib import Path

from ..models import DecisionBrief
from .core import mode_label, note_card, note_search_text, query_tokens, rank_notes, visible_inventory

def split_options(raw_options: str | None) -> tuple[str, ...]:
    if not raw_options:
        return ()
    return tuple(option.strip() for option in raw_options.split("|") if option.strip())

def score_option(option: str, notes: list[dict[str, object]]) -> int:
    tokens = set(query_tokens(option))
    if not tokens:
        return 0
    score = 0
    for note in notes:
        text_tokens = set(query_tokens(note_search_text(note)))
        score += len(tokens & text_tokens)
    return score

def build_decision_council(
    vault: Path,
    question: str,
    raw_options: str | None,
    include_sensitive: bool,
    max_notes: int,
) -> dict[str, object]:
    vault, _all_notes, notes, hidden_sensitive = visible_inventory(vault, include_sensitive)
    options = split_options(raw_options)
    council_specs = (
        ("practical", ("career", "money", "logistics"), "What does the graph say about execution pressure and constraints?"),
        ("taste", ("taste", "creative"), "What protects the flavor from becoming generic sludge?"),
        ("future-self", ("identity", "timeline"), "What pattern would future-you probably recognize?"),
        ("relationships", ("relationships",), "Who or what relationship context is involved?"),
        ("privacy", ("health", "relationships", "money"), "What should stay local, careful, or explicitly consented?"),
        ("craft", ("creative", "career", "taste"), "What evidence points toward a better artifact?"),
    )
    councils = []
    scored_notes_by_path: dict[str, dict[str, object]] = {}
    for name, lenses, prompt in council_specs:
        selected = []
        for lens_id in lenses:
            selected.extend(rank_notes(notes, question, lens_id, max_notes=3))
        deduped = {}
        for score, reasons, note in selected:
            key = str(note["relative"])
            if key not in deduped or score > deduped[key][0]:
                deduped[key] = (score, reasons, note)
        ranked = sorted(deduped.values(), key=lambda item: (-item[0], str(item[2]["relative"])))[: max(1, max_notes)]
        cards = [note_card(note, score, reasons) for score, reasons, note in ranked]
        for card in cards:
            scored_notes_by_path[str(card["path"])] = card
        councils.append(
            {
                "id": name,
                "prompt": prompt,
                "lenses": list(lenses),
                "evidence_count": len(cards),
                "notes": cards,
            }
        )
    all_selected_notes = [
        note for note in notes if str(note["relative"]) in scored_notes_by_path
    ]
    option_scores = {option: score_option(option, all_selected_notes) for option in options}
    recommendation = "No options supplied; use the council notes as a receipt-backed decision brief."
    if option_scores:
        best_score = max(option_scores.values())
        best = [option for option, score in option_scores.items() if score == best_score]
        if len(best) == 1 and best_score > 0:
            recommendation = f"Best graph-supported option: {best[0]}."
        else:
            recommendation = "No single option clearly wins from existing graph evidence; ask one sharper follow-up."
    review_flags = []
    if hidden_sensitive:
        review_flags.append(f"{hidden_sensitive} sensitive notes hidden; private context may change the decision.")
    if sum(council["evidence_count"] for council in councils) == 0:
        review_flags.append("No strong evidence found. Capture a source before pretending this is a wise council.")
    brief = DecisionBrief(
        question=question,
        options=options,
        mode=mode_label(include_sensitive),
        hidden_sensitive=hidden_sensitive,
        councils=tuple(councils),
        recommendation=recommendation,
        review_flags=tuple(review_flags),
    )
    data = brief.to_json()
    data["vault"] = {"name": vault.name}
    data["option_scores"] = option_scores
    return data

def print_decision_council(vault: Path, question: str, raw_options: str | None, include_sensitive: bool, max_notes: int, json_output: bool) -> None:
    data = build_decision_council(vault, question, raw_options, include_sensitive, max_notes)
    if json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("# Decision Council")
    print()
    print(f"Question: {data['question']}")
    print(f"Privacy: {data['mode']} ({data['hidden_sensitive']} sensitive notes hidden)")
    if data["options"]:
        print(f"Options: {', '.join(data['options'])}")
    print()
    for council in data["councils"]:
        print(f"## {str(council['id']).title()}")
        for note in council["notes"] or [{"path": "None"}]:
            if note["path"] == "None":
                print("- No receipts found.")
                continue
            print(f"- {note['path']} ({note['type']}, score {note['score']})")
    print()
    print(f"Recommendation: {data['recommendation']}")
    for flag in data["review_flags"]:
        print(f"Review: {flag}")
