from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawCapture:
    path: str
    title: str
    sensitivity: str
    confidence: str
    tags: tuple[str, ...]
    links: tuple[str, ...]
    raw_text: str

    def to_json(self) -> dict[str, object]:
        return {
            "path": self.path,
            "title": self.title,
            "sensitivity": self.sensitivity,
            "confidence": self.confidence,
            "tags": list(self.tags),
            "links": list(self.links),
            "raw_text": self.raw_text,
        }

@dataclass(frozen=True)
class SourceEvidence:
    source_path: str
    claim_text: str
    raw_excerpt: str
    section: str | None = None
    line_hint: int | None = None
    confidence: str = "confirmed"
    sensitivity: str = "normal"

    def to_json(self) -> dict[str, object]:
        return {
            "source_path": self.source_path,
            "claim_text": self.claim_text,
            "raw_excerpt": self.raw_excerpt,
            "section": self.section,
            "line_hint": self.line_hint,
            "confidence": self.confidence,
            "sensitivity": self.sensitivity,
        }

@dataclass(frozen=True)
class RelationshipProfile:
    kind: str
    context: str
    emotional_charge: str = "unknown"
    closeness: str = "unknown"
    trust: str = "unknown"
    phase: str = "active"

    def to_json(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "context": self.context,
            "emotional_charge": self.emotional_charge,
            "closeness": self.closeness,
            "trust": self.trust,
            "phase": self.phase,
        }

@dataclass(frozen=True)
class TimelineItem:
    id: str
    title: str
    text: str
    source_note: str
    source_section: str
    date_label: str | None
    date_start: str | None
    date_end: str | None
    date_precision: str
    sort_key: str
    life_period: str | None
    threads: tuple[str, ...]
    people: tuple[str, ...]
    projects: tuple[str, ...]
    places: tuple[str, ...]
    emotional_charge: str
    pressure_level: str
    turning_point: bool
    confidence: str
    sensitivity: str
    links: tuple[str, ...]
    sources: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "source_note": self.source_note,
            "source_section": self.source_section,
            "date_label": self.date_label,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "date_precision": self.date_precision,
            "sort_key": self.sort_key,
            "life_period": self.life_period,
            "threads": list(self.threads),
            "people": list(self.people),
            "projects": list(self.projects),
            "places": list(self.places),
            "emotional_charge": self.emotional_charge,
            "pressure_level": self.pressure_level,
            "turning_point": self.turning_point,
            "confidence": self.confidence,
            "sensitivity": self.sensitivity,
            "links": list(self.links),
            "sources": list(self.sources),
        }

@dataclass(frozen=True)
class TimelinePeriod:
    id: str
    title: str
    start: str | None
    end: str | None
    date_precision: str
    theme: str
    active_threads: tuple[str, ...]
    main_people: tuple[str, ...]
    main_projects: tuple[str, ...]
    pressure_level: str
    emotional_charge: str
    source_note: str

    def to_json(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "start": self.start,
            "end": self.end,
            "date_precision": self.date_precision,
            "theme": self.theme,
            "active_threads": list(self.active_threads),
            "main_people": list(self.main_people),
            "main_projects": list(self.main_projects),
            "pressure_level": self.pressure_level,
            "emotional_charge": self.emotional_charge,
            "source_note": self.source_note,
        }

@dataclass(frozen=True)
class LensSpec:
    id: str
    title: str
    description: str
    note_types: tuple[str, ...]
    path_prefixes: tuple[str, ...]
    tags: tuple[str, ...]
    keywords: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "note_types": list(self.note_types),
            "path_prefixes": list(self.path_prefixes),
            "tags": list(self.tags),
            "keywords": list(self.keywords),
        }

@dataclass(frozen=True)
class EvidenceRef:
    path: str
    title: str
    type: str
    sensitivity: str
    confidence: str
    excerpt: str = ""

    def to_json(self) -> dict[str, object]:
        return {
            "path": self.path,
            "title": self.title,
            "type": self.type,
            "sensitivity": self.sensitivity,
            "confidence": self.confidence,
            "excerpt": self.excerpt,
        }

@dataclass(frozen=True)
class OpenLoop:
    kind: str
    priority: str
    path: str
    title: str
    description: str
    lens: str | None
    evidence: tuple[EvidenceRef, ...] = ()

    def to_json(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "priority": self.priority,
            "path": self.path,
            "title": self.title,
            "description": self.description,
            "lens": self.lens,
            "evidence": [item.to_json() for item in self.evidence],
        }

@dataclass(frozen=True)
class ContradictionSignal:
    kind: str
    severity: str
    path: str
    title: str
    signal: str
    evidence: tuple[EvidenceRef, ...] = ()

    def to_json(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "severity": self.severity,
            "path": self.path,
            "title": self.title,
            "signal": self.signal,
            "evidence": [item.to_json() for item in self.evidence],
        }

@dataclass(frozen=True)
class DecisionBrief:
    question: str
    options: tuple[str, ...]
    mode: str
    hidden_sensitive: int
    councils: tuple[dict[str, object], ...]
    recommendation: str
    review_flags: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "question": self.question,
            "options": list(self.options),
            "mode": self.mode,
            "hidden_sensitive": self.hidden_sensitive,
            "councils": list(self.councils),
            "recommendation": self.recommendation,
            "review_flags": list(self.review_flags),
        }

@dataclass(frozen=True)
class ImportPlan:
    source: str
    source_type: str
    title: str
    domain: str
    sensitivity: str
    target_path: str
    word_count: int
    status: str
    applied: bool
    reason: str = ""

    def to_json(self) -> dict[str, object]:
        return {
            "source": self.source,
            "source_type": self.source_type,
            "title": self.title,
            "domain": self.domain,
            "sensitivity": self.sensitivity,
            "target_path": self.target_path,
            "word_count": self.word_count,
            "status": self.status,
            "applied": self.applied,
            "reason": self.reason,
        }

@dataclass(frozen=True)
class ShareCapsule:
    title: str
    mode: str
    query: str | None
    lens: str | None
    hidden_sensitive: int
    notes: tuple[dict[str, object], ...]
    sources: tuple[EvidenceRef, ...]
    warnings: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "title": self.title,
            "mode": self.mode,
            "query": self.query,
            "lens": self.lens,
            "hidden_sensitive": self.hidden_sensitive,
            "notes": list(self.notes),
            "sources": [item.to_json() for item in self.sources],
            "warnings": list(self.warnings),
        }

@dataclass(frozen=True)
class TasteGenomeReport:
    mode: str
    hidden_sensitive: int
    principles: tuple[str, ...]
    anti_taste: tuple[str, ...]
    references: tuple[str, ...]
    motion_words: tuple[str, ...]
    material_words: tuple[str, ...]
    proof_examples: tuple[str, ...]
    weak_spots: tuple[str, ...]
    source_notes: tuple[EvidenceRef, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "hidden_sensitive": self.hidden_sensitive,
            "principles": list(self.principles),
            "anti_taste": list(self.anti_taste),
            "references": list(self.references),
            "motion_words": list(self.motion_words),
            "material_words": list(self.material_words),
            "proof_examples": list(self.proof_examples),
            "weak_spots": list(self.weak_spots),
            "source_notes": [item.to_json() for item in self.source_notes],
        }

@dataclass(frozen=True)
class ProofSignal:
    claim: str
    strength: str
    score: int
    lens: str | None
    evidence: tuple[EvidenceRef, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "claim": self.claim,
            "strength": self.strength,
            "score": self.score,
            "lens": self.lens,
            "evidence": [item.to_json() for item in self.evidence],
        }

@dataclass(frozen=True)
class BeliefVersion:
    text: str
    date: str
    path: str
    title: str
    confidence: str
    sensitivity: str
    change_signal: str | None = None

    def to_json(self) -> dict[str, object]:
        return {
            "text": self.text,
            "date": self.date,
            "path": self.path,
            "title": self.title,
            "confidence": self.confidence,
            "sensitivity": self.sensitivity,
            "change_signal": self.change_signal,
        }

@dataclass(frozen=True)
class TasteGuardFinding:
    kind: str
    severity: str
    message: str
    evidence: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "severity": self.severity,
            "message": self.message,
            "evidence": list(self.evidence),
        }

@dataclass(frozen=True)
class DecisionReplayReport:
    decision: str
    mode: str
    hidden_sensitive: int
    receipts: tuple[EvidenceRef, ...]
    outcome_signals: tuple[str, ...]
    calibration_questions: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "decision": self.decision,
            "mode": self.mode,
            "hidden_sensitive": self.hidden_sensitive,
            "receipts": [item.to_json() for item in self.receipts],
            "outcome_signals": list(self.outcome_signals),
            "calibration_questions": list(self.calibration_questions),
        }

@dataclass(frozen=True)
class FutureTrajectory:
    name: str
    likelihood: str
    description: str
    supporting_signals: tuple[str, ...]
    suggested_next_move: str

    def to_json(self) -> dict[str, object]:
        return {
            "name": self.name,
            "likelihood": self.likelihood,
            "description": self.description,
            "supporting_signals": list(self.supporting_signals),
            "suggested_next_move": self.suggested_next_move,
        }

@dataclass(frozen=True)
class MemoryCandidate:
    kind: str
    text: str
    confidence: str
    evidence: SourceEvidence
    target_hint: str | None = None

    def to_json(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "text": self.text,
            "confidence": self.confidence,
            "evidence": self.evidence.to_json(),
            "target_hint": self.target_hint,
        }

@dataclass(frozen=True)
class DurableNotePatch:
    target: str
    action: str
    section: str
    content: str
    source: str
    evidence: SourceEvidence

    def to_json(self) -> dict[str, object]:
        return {
            "target": self.target,
            "action": self.action,
            "section": self.section,
            "content": self.content,
            "source": self.source,
            "evidence": self.evidence.to_json(),
        }

@dataclass(frozen=True)
class LinkPatch:
    source: str
    target: str
    action: str
    reason: str

    def to_json(self) -> dict[str, object]:
        return {
            "source": self.source,
            "target": self.target,
            "action": self.action,
            "reason": self.reason,
        }

@dataclass(frozen=True)
class ReviewFlag:
    level: str
    message: str
    evidence: str | None = None

    def to_json(self) -> dict[str, object]:
        return {
            "level": self.level,
            "message": self.message,
            "evidence": self.evidence,
        }

@dataclass(frozen=True)
class ExtractionPlan:
    raw_capture: RawCapture
    memory_candidates: tuple[MemoryCandidate, ...]
    durable_note_patches: tuple[DurableNotePatch, ...]
    link_patches: tuple[LinkPatch, ...]
    review_flags: tuple[ReviewFlag, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "raw_capture": self.raw_capture.to_json(),
            "memory_candidates": [candidate.to_json() for candidate in self.memory_candidates],
            "durable_note_patches": [patch.to_json() for patch in self.durable_note_patches],
            "link_patches": [patch.to_json() for patch in self.link_patches],
            "review_flags": [flag.to_json() for flag in self.review_flags],
        }
