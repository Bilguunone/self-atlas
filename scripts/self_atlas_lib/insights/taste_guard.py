from __future__ import annotations

import json
from pathlib import Path

from ..models import TasteGuardFinding
from ..vault import normalized_path
from .core import mode_label, visible_inventory
from .taste import ANTI_TASTE_WORDS, MATERIAL_WORDS, MOTION_WORDS, PROOF_WORDS, build_taste_genome


def artifact_text_from_inputs(text: str | None, file: Path | None) -> tuple[str, str]:
    if text:
        return text, "inline"
    if file:
        path = normalized_path(file)
        return path.read_text(encoding="utf-8"), path.name
    raise SystemExit("taste-autopilot requires --text or --file.")

def matched_words(text: str, words: tuple[str, ...]) -> tuple[str, ...]:
    lowered = text.lower()
    return tuple(word for word in words if word in lowered)

def finding(kind: str, severity: str, message: str, evidence: tuple[str, ...]) -> TasteGuardFinding:
    return TasteGuardFinding(kind=kind, severity=severity, message=message, evidence=evidence)

def build_taste_autopilot(
    vault: Path,
    artifact_text: str,
    label: str,
    include_sensitive: bool,
    max_items: int,
) -> dict[str, object]:
    vault, _all_notes, _notes, hidden_sensitive = visible_inventory(vault, include_sensitive)
    genome = build_taste_genome(vault, include_sensitive, max_items)
    findings: list[TasteGuardFinding] = []
    anti_hits = matched_words(artifact_text, ANTI_TASTE_WORDS)
    motion_hits = matched_words(artifact_text, MOTION_WORDS)
    material_hits = matched_words(artifact_text, MATERIAL_WORDS)
    proof_hits = matched_words(artifact_text, PROOF_WORDS)
    if anti_hits:
        findings.append(finding("anti-taste-collision", "high", "Artifact uses language Self Atlas already treats as taste-risky.", anti_hits))
    if not proof_hits:
        findings.append(finding("missing-proof", "high", "No proof/artifact/save/use language found. This may explain instead of proving.", ()))
    if not motion_hits:
        findings.append(finding("weak-motion", "medium", "No motion/rhythm/pacing language found.", ()))
    if not material_hits:
        findings.append(finding("weak-material", "medium", "No tactile/material/emotional artifact language found.", ()))
    if motion_hits:
        findings.append(finding("motion-alignment", "positive", "Artifact speaks the motion language in the Taste Genome.", motion_hits))
    if material_hits:
        findings.append(finding("material-alignment", "positive", "Artifact has material/emotional/tactile signals.", material_hits))
    if proof_hits:
        findings.append(finding("proof-alignment", "positive", "Artifact includes proof-oriented language.", proof_hits))
    severe = [item for item in findings if item.severity == "high"]
    recommendation = "Passable taste alignment. Still do a human sniff test, obviously."
    if severe:
        recommendation = "Revise before shipping; the guard found high-severity taste or proof issues."
    return {
        "vault": {"name": vault.name},
        "mode": mode_label(include_sensitive),
        "hidden_sensitive": hidden_sensitive,
        "artifact": {"label": label, "characters": len(artifact_text)},
        "findings": [item.to_json() for item in findings],
        "recommendation": recommendation,
        "taste_genome_counts": genome.get("counts", {}),
    }

def print_taste_autopilot(
    vault: Path,
    text: str | None,
    file: Path | None,
    include_sensitive: bool,
    max_items: int,
    json_output: bool,
) -> None:
    artifact_text, label = artifact_text_from_inputs(text, file)
    data = build_taste_autopilot(vault, artifact_text, label, include_sensitive, max_items)
    if json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("# Taste Autopilot Guard")
    print()
    print(f"Artifact: {data['artifact']['label']}")
    print(f"Privacy: {data['mode']} ({data['hidden_sensitive']} sensitive notes hidden)")
    print()
    for item in data["findings"]:
        print(f"- [{item['severity']}] {item['kind']}: {item['message']}")
        if item["evidence"]:
            print(f"  Evidence: {', '.join(item['evidence'])}")
    print()
    print(f"Recommendation: {data['recommendation']}")
