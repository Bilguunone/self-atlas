from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from pathlib import Path

from ..constants import WIKI_LINK_RE
from ..models import EvidenceRef, LensSpec
from ..vault import (
    as_list,
    as_string,
    bullet_lines,
    link_indexes,
    note_inventory,
    require_vault,
    resolve_link_target,
)

SENSITIVE_LEVELS = {"private", "health", "financial", "intimate"}
SUPPORTED_IMPORT_SUFFIXES = {".md", ".txt", ".json"}

LIFE_LENSES: tuple[LensSpec, ...] = (
    LensSpec(
        id="identity",
        title="Identity",
        description="Self-story, values, desires, fears, and recurring inner patterns.",
        note_types=("identity", "value", "desire", "pattern", "tension"),
        path_prefixes=("10 Self/", "80 Reflections/"),
        tags=("self-atlas/identity", "self-atlas/value", "self-atlas/desire", "self-atlas/pattern"),
        keywords=("identity", "value", "desire", "fear", "pattern", "tension", "misunderstand"),
    ),
    LensSpec(
        id="career",
        title="Career",
        description="Work, projects, skills, proof, roles, collaborators, and pressure points.",
        note_types=("work", "project", "skill"),
        path_prefixes=("30 Work/",),
        tags=("self-atlas/work", "self-atlas/project", "self-atlas/skill"),
        keywords=("work", "career", "project", "role", "skill", "proof", "prototype", "swift", "swiftui"),
    ),
    LensSpec(
        id="creative",
        title="Creative",
        description="Creative identity, artifacts, references, product feel, and craft pressure.",
        note_types=("project", "preference", "creative_reference", "pattern"),
        path_prefixes=("30 Work/Projects/", "50 Taste/", "60 Interests/", "80 Reflections/"),
        tags=("self-atlas/project", "self-atlas/taste", "self-atlas/craft", "self-atlas/music"),
        keywords=("creative", "artifact", "design", "music", "motion", "export", "poster", "visual", "craft"),
    ),
    LensSpec(
        id="taste",
        title="Taste",
        description="Taste, anti-taste, references, motion, material, and proof moments.",
        note_types=("preference", "creative_reference"),
        path_prefixes=("50 Taste/", "60 Interests/"),
        tags=("self-atlas/taste", "self-atlas/music", "self-atlas/reference"),
        keywords=("taste", "anti", "reference", "motion", "material", "warm", "generic", "soulless", "tactile"),
    ),
    LensSpec(
        id="relationships",
        title="Relationships",
        description="People, closeness, family, friendship, love, mentorship, and collaborators.",
        note_types=("person",),
        path_prefixes=("20 People/", "25 Love/"),
        tags=("self-atlas/person", "self-atlas/friend", "self-atlas/family", "self-atlas/love"),
        keywords=("friend", "family", "love", "relationship", "mentor", "collaborator", "support"),
    ),
    LensSpec(
        id="health",
        title="Health",
        description="Health observations, metrics, body context, energy, sleep, and triggers.",
        note_types=("health_observation", "health_metric"),
        path_prefixes=("40 Health/",),
        tags=("self-atlas/health",),
        keywords=("health", "body", "sleep", "energy", "pain", "metric", "trigger", "frequency"),
    ),
    LensSpec(
        id="money",
        title="Money",
        description="Financial context, income, obligations, tuition, support, and pressure.",
        note_types=("money_context",),
        path_prefixes=("75 Money/",),
        tags=("self-atlas/money", "self-atlas/financial"),
        keywords=("money", "financial", "salary", "tuition", "income", "rent", "budget", "paid", "support"),
    ),
    LensSpec(
        id="logistics",
        title="Logistics",
        description="Documents, deadlines, visas, travel, admin, and practical open threads.",
        note_types=("logistics_thread",),
        path_prefixes=("00 System/Open Threads", "75 Logistics/"),
        tags=("self-atlas/logistics", "self-atlas/open-threads"),
        keywords=("visa", "deadline", "document", "appointment", "travel", "archive", "admin", "confirm"),
    ),
    LensSpec(
        id="timeline",
        title="Timeline",
        description="Events, periods, milestones, turning points, eras, and dated life threads.",
        note_types=("event", "life_period", "milestone"),
        path_prefixes=("70 Timeline/",),
        tags=("self-atlas/timeline", "self-atlas/event", "self-atlas/milestone"),
        keywords=("timeline", "date", "year", "phase", "chapter", "period", "started", "turned"),
    ),
)

LENS_BY_ID = {lens.id: lens for lens in LIFE_LENSES}


def available_lens_ids() -> list[str]:
    return [lens.id for lens in LIFE_LENSES]

def mode_label(include_sensitive: bool) -> str:
    return "private" if include_sensitive else "share-safe"

def note_type(note: dict[str, object]) -> str:
    return as_string(note["frontmatter"].get("type"), "missing")

def note_status(note: dict[str, object]) -> str:
    return as_string(note["frontmatter"].get("status"), "active")

def note_sensitivity(note: dict[str, object]) -> str:
    return as_string(note["frontmatter"].get("sensitivity"), "normal")

def note_confidence(note: dict[str, object]) -> str:
    return as_string(note["frontmatter"].get("confidence"), "missing")

def note_is_sensitive(note: dict[str, object]) -> bool:
    return note_sensitivity(note) in SENSITIVE_LEVELS

def note_visible(note: dict[str, object], include_sensitive: bool, include_templates: bool = False) -> bool:
    if note["is_template"] and not include_templates:
        return False
    if not include_sensitive and note_is_sensitive(note):
        return False
    return True

def visible_inventory(
    vault: Path,
    include_sensitive: bool,
    include_templates: bool = False,
) -> tuple[Path, list[dict[str, object]], list[dict[str, object]], int]:
    vault = require_vault(vault)
    all_notes = note_inventory(vault)
    visible = [note for note in all_notes if note_visible(note, include_sensitive, include_templates)]
    hidden_sensitive = sum(1 for note in all_notes if not include_sensitive and note_is_sensitive(note))
    return vault, all_notes, visible, hidden_sensitive

def frontmatter_tags(note: dict[str, object]) -> set[str]:
    return {tag.lower() for tag in as_list(note["frontmatter"].get("tags"))}

def note_search_text(note: dict[str, object]) -> str:
    fields = [
        str(note["relative"]),
        str(note["title"]),
        note_type(note),
        " ".join(as_list(note["frontmatter"].get("tags"))),
        str(note["body"]),
    ]
    return "\n".join(fields).lower()

def note_matches_lens(note: dict[str, object], lens_id: str | None) -> bool:
    if not lens_id:
        return True
    lens = LENS_BY_ID.get(lens_id)
    if not lens:
        raise SystemExit(f"Unknown life lens: {lens_id}")
    relative = str(note["relative"])
    tags = frontmatter_tags(note)
    search_text = note_search_text(note)
    if any(relative.startswith(prefix) or relative.removesuffix(".md") == prefix for prefix in lens.path_prefixes):
        return True
    if note_type(note) in lens.note_types:
        return True
    if tags.intersection({tag.lower() for tag in lens.tags}):
        return True
    return any(keyword.lower() in search_text for keyword in lens.keywords)

def lens_match_score(note: dict[str, object], lens: LensSpec) -> int:
    relative = str(note["relative"])
    tags = frontmatter_tags(note)
    search_text = note_search_text(note)
    score = 0
    if any(relative.startswith(prefix) or relative.removesuffix(".md") == prefix for prefix in lens.path_prefixes):
        score += 20
    if note_type(note) in lens.note_types:
        score += 15
    if tags.intersection({tag.lower() for tag in lens.tags}):
        score += 12
    score += sum(1 for keyword in lens.keywords if keyword.lower() in search_text)
    return score

def infer_lens_id(note: dict[str, object]) -> str | None:
    scored = [(lens_match_score(note, lens), lens.id) for lens in LIFE_LENSES]
    scored = [item for item in scored if item[0] > 0]
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], available_lens_ids().index(item[1])))
    return scored[0][1]

def query_tokens(query: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9][a-z0-9'-]{1,}", query.lower()) if len(token) > 2]

def note_query_score(note: dict[str, object], query: str) -> tuple[int, list[str]]:
    query = query.strip().lower()
    if not query:
        return 1, ["recent"]
    title = str(note["title"]).lower()
    relative = str(note["relative"]).lower()
    tags = " ".join(as_list(note["frontmatter"].get("tags"))).lower()
    body = str(note["body"]).lower()
    score = 0
    reasons = []
    if query in title:
        score += 12
        reasons.append("title")
    if query in relative:
        score += 10
        reasons.append("path")
    if query in tags:
        score += 8
        reasons.append("tags")
    for token in query_tokens(query):
        if token in title:
            score += 5
        if token in relative:
            score += 4
        if token in tags:
            score += 3
        if token in body:
            score += 1
    if score and not reasons:
        reasons.append("body")
    return score, sorted(set(reasons))

def parse_note_date(note: dict[str, object]) -> dt.date:
    for key in ("updated", "created"):
        raw = as_string(note["frontmatter"].get(key))
        try:
            return dt.date.fromisoformat(raw)
        except ValueError:
            continue
    return dt.date.min

def compact_excerpt(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."

def note_bullets(note: dict[str, object], limit: int = 3) -> list[str]:
    useful = []
    for bullet in bullet_lines(str(note["body"])):
        if re.search(r"\{\{[^}]+\}\}", bullet):
            continue
        if not bullet.strip():
            continue
        useful.append(bullet)
        if len(useful) >= limit:
            break
    return useful

def safe_note_bullets(
    note: dict[str, object],
    visible_notes: list[dict[str, object]],
    include_sensitive: bool,
    limit: int = 3,
) -> list[str]:
    bullets = note_bullets(note, max(limit * 4, limit))
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

def note_ref(
    note: dict[str, object],
    include_excerpt: bool = False,
    visible_notes: list[dict[str, object]] | None = None,
    include_sensitive: bool = True,
) -> EvidenceRef:
    if include_excerpt and visible_notes is not None:
        bullets = safe_note_bullets(note, visible_notes, include_sensitive, 2)
    else:
        bullets = note_bullets(note, 2)
    excerpt = compact_excerpt(" ".join(bullets)) if include_excerpt else ""
    return EvidenceRef(
        path=str(note["relative"]),
        title=str(note["title"]),
        type=note_type(note),
        sensitivity=note_sensitivity(note),
        confidence=note_confidence(note),
        excerpt=excerpt,
    )

def note_card(
    note: dict[str, object],
    score: int = 0,
    reasons: list[str] | None = None,
    include_bullets: bool = True,
) -> dict[str, object]:
    return {
        "path": str(note["relative"]),
        "title": str(note["title"]),
        "type": note_type(note),
        "status": note_status(note),
        "sensitivity": note_sensitivity(note),
        "confidence": note_confidence(note),
        "score": score,
        "match_reasons": reasons or [],
        "lens": infer_lens_id(note),
        "bullets": note_bullets(note, 3) if include_bullets else [],
    }

def rank_notes(
    notes: list[dict[str, object]],
    query: str = "",
    lens_id: str | None = None,
    max_notes: int = 8,
    include_system: bool = False,
    include_sources: bool = False,
) -> list[tuple[int, list[str], dict[str, object]]]:
    scored = []
    for note in notes:
        relative = str(note["relative"])
        if note["is_template"]:
            continue
        if str(note["relative"]) == "README.md":
            continue
        if not include_system and relative.startswith("00 System/"):
            continue
        if not include_sources and note["is_source"]:
            continue
        if not note_matches_lens(note, lens_id):
            continue
        score, reasons = note_query_score(note, query)
        if not query and lens_id:
            score += 4
            reasons = sorted(set(reasons + ["lens"]))
        if score:
            scored.append((score, reasons, note))
    scored.sort(key=lambda item: (-item[0], str(item[2]["relative"])))
    return scored[: max(1, max_notes)]

def visible_source_refs(note: dict[str, object], visible_notes: list[dict[str, object]], max_sources: int = 6) -> list[EvidenceRef]:
    by_key, by_base = link_indexes(visible_notes)
    refs = []
    seen = set()
    for source in as_list(note["frontmatter"].get("sources")):
        source_key = source.removesuffix(".md")
        source_note = by_key.get(source_key)
        if not source_note:
            source_note, ambiguous = resolve_link_target(source_key, by_key, by_base)
            if ambiguous:
                source_note = None
        if source_note and str(source_note["key"]) not in seen:
            refs.append(note_ref(source_note))
            seen.add(str(source_note["key"]))
    for target in note["links"]:
        target_note, ambiguous = resolve_link_target(str(target), by_key, by_base)
        if ambiguous or not target_note or not target_note["is_source"]:
            continue
        if str(target_note["key"]) in seen:
            continue
        refs.append(note_ref(target_note))
        seen.add(str(target_note["key"]))
    return refs[:max_sources]

def durable_source_backlinks(notes: list[dict[str, object]]) -> tuple[Counter[str], Counter[str]]:
    by_key, by_base = link_indexes(notes)
    capture_keys = {str(note["key"]) for note in notes if note["is_source"]}
    durable_keys = {
        str(note["key"])
        for note in notes
        if not note["is_source"] and not note["is_template"] and not str(note["relative"]).startswith("00 System/")
    }
    all_inbound: Counter[str] = Counter()
    durable_inbound: Counter[str] = Counter()
    for note in notes:
        from_key = str(note["key"])
        for target in note["links"]:
            target_note, ambiguous = resolve_link_target(str(target), by_key, by_base)
            if ambiguous or not target_note:
                continue
            target_key = str(target_note["key"])
            if target_key not in capture_keys:
                continue
            all_inbound[target_key] += 1
            if from_key in durable_keys:
                durable_inbound[target_key] += 1
    return all_inbound, durable_inbound
