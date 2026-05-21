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
