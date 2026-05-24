from __future__ import annotations

import json
from pathlib import Path

from ..models import EvidenceRef, ProofSignal
from .core import mode_label, rank_notes, safe_note_bullets, visible_inventory, visible_source_refs


def proof_strength(score: int, evidence_count: int) -> str:
    if score >= 16 and evidence_count >= 3:
        return "strong"
    if score >= 8 and evidence_count >= 2:
        return "usable"
    if evidence_count:
        return "thin"
    return "missing"

def proof_evidence_for_note(
    note: dict[str, object],
    claim: str,
    visible_notes: list[dict[str, object]],
    include_sensitive: bool,
) -> EvidenceRef:
    claim_tokens = {token for token in claim.lower().split() if len(token) > 2}
    bullets = safe_note_bullets(note, visible_notes, include_sensitive, 8)
    matching = [
        bullet for bullet in bullets
        if not claim_tokens or any(token in bullet.lower() for token in claim_tokens)
    ]
    excerpt = " ".join(matching[:2] or bullets[:1])
    return EvidenceRef(
        path=str(note["relative"]),
        title=str(note["title"]),
        type=str(note["frontmatter"].get("type", "missing")),
        sensitivity=str(note["frontmatter"].get("sensitivity", "normal")),
        confidence=str(note["frontmatter"].get("confidence", "missing")),
        excerpt=excerpt,
    )

def build_proof_engine(
    vault: Path,
    claim: str,
    lens_id: str | None,
    include_sensitive: bool,
    max_items: int,
) -> dict[str, object]:
    vault, _all_notes, notes, hidden_sensitive = visible_inventory(vault, include_sensitive)
    ranked = rank_notes(notes, claim, lens_id, max_notes=max_items)
    evidence = []
    source_receipts = []
    total_score = 0
    seen_sources = set()
    for score, _reasons, note in ranked:
        total_score += score
        evidence.append(proof_evidence_for_note(note, claim, notes, include_sensitive))
        for source in visible_source_refs(note, notes):
            if source.path in seen_sources:
                continue
            source_receipts.append(source)
            seen_sources.add(source.path)
    signal = ProofSignal(
        claim=claim,
        strength=proof_strength(total_score, len(evidence) + len(source_receipts)),
        score=total_score,
        lens=lens_id,
        evidence=tuple(evidence),
    )
    review_flags = []
    if hidden_sensitive:
        review_flags.append(f"{hidden_sensitive} sensitive notes hidden; private receipts may change the proof strength.")
    if not evidence:
        review_flags.append("No receipts found. Capture evidence before turning this into a confident claim.")
    return {
        "vault": {"name": vault.name},
        "mode": mode_label(include_sensitive),
        "hidden_sensitive": hidden_sensitive,
        "claim": signal.to_json(),
        "source_receipts": [item.to_json() for item in source_receipts[:max_items]],
        "review_flags": review_flags,
    }

def print_proof_engine(vault: Path, claim: str, lens_id: str | None, include_sensitive: bool, max_items: int, json_output: bool) -> None:
    data = build_proof_engine(vault, claim, lens_id, include_sensitive, max_items)
    if json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("# Proof Engine")
    print()
    print(f"Claim: {data['claim']['claim']}")
    print(f"Strength: {data['claim']['strength']} (score {data['claim']['score']})")
    print(f"Privacy: {data['mode']} ({data['hidden_sensitive']} sensitive notes hidden)")
    print()
    print("## Receipts")
    for item in data["claim"]["evidence"] or [{"path": "None"}]:
        if item["path"] == "None":
            print("- None")
            continue
        print(f"- {item['path']} ({item['confidence']})")
        if item["excerpt"]:
            print(f"  - {item['excerpt']}")
    for flag in data["review_flags"]:
        print(f"Review: {flag}")
