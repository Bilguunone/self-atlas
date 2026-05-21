from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from pathlib import Path

from .constants import EXPORT_SCHEMA_VERSION, WIKI_EDGE_RE
from .models import RelationshipProfile
from .vault import (
    as_list,
    as_string,
    collect_validation,
    computed_note_id,
    link_indexes,
    note_inventory,
    normalized_source_key,
    require_vault,
    resolve_link_target,
)

EXCLUDED_SENSITIVITIES = {"private", "health", "financial", "intimate"}


def inferred_relationship_kind(note: dict[str, object]) -> str | None:
    if note.get("is_template") or note.get("is_source"):
        return None

    frontmatter_data = note["frontmatter"]
    if not isinstance(frontmatter_data, dict):
        return None

    note_type = as_string(frontmatter_data.get("type")).strip()
    if note_type != "person":
        return None

    existing = as_string(frontmatter_data.get("relationship_kind")).strip()
    if existing and existing not in {"[]", "unknown"}:
        return existing

    relative = str(note["relative"]).lower()
    tags = {tag.lower() for tag in as_list(frontmatter_data.get("tags"))}
    if relative.startswith("25 love/") or "self-atlas/love" in tags:
        return "love"
    if "/friends/" in relative or "self-atlas/friend" in tags or "self-atlas/friends" in tags:
        return "friend"
    if "/family/" in relative or "self-atlas/family" in tags:
        return "family"
    if "/mentors/" in relative or "self-atlas/mentor" in tags or "self-atlas/mentors" in tags:
        return "mentor"
    if "/work/" in relative or "/collaborators/" in relative or "self-atlas/collaborator" in tags:
        return "collaborator"
    return "person"

def inferred_relationship_context(kind: str) -> str:
    return {
        "love": "romantic",
        "friend": "social",
        "family": "family",
        "mentor": "mentorship",
        "collaborator": "work",
        "person": "unknown",
    }.get(kind, "unknown")

def relationship_profile(note: dict[str, object]) -> RelationshipProfile | None:
    frontmatter_data = note["frontmatter"]
    kind = inferred_relationship_kind(note)
    if not kind:
        return None
    return RelationshipProfile(
        kind=kind,
        context=as_string(frontmatter_data.get("relationship_context"), inferred_relationship_context(kind)),
        emotional_charge=as_string(frontmatter_data.get("emotional_charge"), "unknown"),
        closeness=as_string(frontmatter_data.get("closeness"), "unknown"),
        trust=as_string(frontmatter_data.get("trust"), "unknown"),
        phase=as_string(frontmatter_data.get("relationship_phase"), "active"),
    )

def note_is_excluded_sensitive(note: dict[str, object]) -> bool:
    return as_string(note["frontmatter"].get("sensitivity"), "normal") in EXCLUDED_SENSITIVITIES

def visible_note_keys(
    notes: list[dict[str, object]],
    include_templates: bool,
    exclude_sensitive: bool,
) -> tuple[set[str], int, int]:
    included_keys = set()
    excluded_templates = 0
    excluded_sensitive_count = 0
    for note in notes:
        if note["is_template"] and not include_templates:
            excluded_templates += 1
            continue
        if exclude_sensitive and note_is_excluded_sensitive(note):
            excluded_sensitive_count += 1
            continue
        included_keys.add(str(note["key"]))
    return included_keys, excluded_templates, excluded_sensitive_count

def filtered_frontmatter(
    frontmatter_data: dict[str, object],
    visible_links: list[str],
    visible_sources: list[str],
) -> dict[str, object]:
    filtered = dict(frontmatter_data)
    if "links" in filtered:
        filtered["links"] = visible_links
    if "sources" in filtered:
        filtered["sources"] = visible_sources
    return filtered

def visible_frontmatter_targets(
    values: list[str],
    by_key: dict[str, dict[str, object]],
    by_base: dict[str, list[dict[str, object]]],
    included_keys: set[str],
) -> list[str]:
    visible = []
    for value in values:
        normalized_value = normalized_source_key(value)
        target_note, ambiguous = resolve_link_target(normalized_value, by_key, by_base)
        if ambiguous:
            continue
        if target_note is None:
            continue
        if str(target_note["key"]) in included_keys:
            visible.append(value)
    return visible

def build_export_graph(
    vault: Path,
    include_body: bool,
    exclude_sensitive: bool,
    include_templates: bool = False,
) -> dict[str, object]:
    vault = require_vault(vault)
    report = collect_validation(vault)
    all_notes = report["notes"]
    by_key, by_base = link_indexes(all_notes)
    warnings = []
    included_keys, excluded_templates, excluded_sensitive_count = visible_note_keys(
        all_notes,
        include_templates,
        exclude_sensitive,
    )
    included_notes = [note for note in all_notes if str(note["key"]) in included_keys]

    id_by_key = {str(note["key"]): computed_note_id(str(note["key"])) for note in included_notes}
    relationship_by_key = {
        str(note["key"]): relationship_profile(note)
        for note in included_notes
    }
    id_counts = Counter(id_by_key.values())
    for note_id, count in id_counts.items():
        if count > 1:
            warnings.append(f"Duplicate computed id `{note_id}` appears {count} times.")

    inbound = Counter()
    outbound = Counter()
    edges = []
    omitted_edges = 0

    for note in included_notes:
        from_key = str(note["key"])
        from_id = id_by_key[from_key]
        for match in WIKI_EDGE_RE.finditer(str(note["text"])):
            target = match.group(1).strip()
            alias = match.group(2).strip() if match.group(2) else None
            target_note, ambiguous = resolve_link_target(target, by_key, by_base)
            target_key = str(target_note["key"]) if target_note else None
            if ambiguous or target_note is None:
                if exclude_sensitive:
                    omitted_edges += 1
                    continue
            elif target_key not in included_keys:
                omitted_edges += 1
                continue

            target_id = id_by_key.get(target_key) if target_key in included_keys else None
            missing = target_note is None and not ambiguous
            target_relationship = relationship_by_key.get(target_key) if target_key else None
            is_source_edge = target.startswith("90 Sources/") or (target_key or "").startswith("90 Sources/")
            kind = "source" if is_source_edge else "relationship" if target_relationship else "wiki"
            if ambiguous:
                warnings.append(f"Ambiguous link target `[[{target}]]` from `{note['relative']}`.")
            if missing:
                warnings.append(f"Missing link target `[[{target}]]` from `{note['relative']}`.")
            outbound[from_id] += 1
            if target_id:
                inbound[target_id] += 1
            edges.append(
                {
                    "from": from_id,
                    "to": target_id,
                    "target": target,
                    "kind": kind,
                    "relationship_kind": target_relationship.kind if target_relationship else None,
                    "missing": missing,
                    "alias": alias,
                }
            )

    nodes = []
    for note in included_notes:
        frontmatter_data = note["frontmatter"]
        note_id = id_by_key[str(note["key"])]
        note_relationship = relationship_by_key.get(str(note["key"]))
        visible_body_links = visible_frontmatter_targets(
            [str(link) for link in note["links"]],
            by_key,
            by_base,
            included_keys,
        )
        visible_frontmatter_links = visible_frontmatter_targets(
            as_list(frontmatter_data.get("links")),
            by_key,
            by_base,
            included_keys,
        )
        visible_sources = visible_frontmatter_targets(
            as_list(frontmatter_data.get("sources")),
            by_key,
            by_base,
            included_keys,
        )
        visible_frontmatter = filtered_frontmatter(frontmatter_data, visible_frontmatter_links, visible_sources)
        node = {
            "id": note_id,
            "path": str(note["relative"]),
            "title": str(note["title"]),
            "type": as_string(frontmatter_data.get("type"), "missing"),
            "status": as_string(frontmatter_data.get("status"), "active"),
            "sensitivity": as_string(frontmatter_data.get("sensitivity"), "normal"),
            "confidence": as_string(frontmatter_data.get("confidence"), "missing"),
            "created": as_string(frontmatter_data.get("created")),
            "updated": as_string(frontmatter_data.get("updated")),
            "aliases": as_list(frontmatter_data.get("aliases")),
            "tags": as_list(frontmatter_data.get("tags")),
            "sources": visible_sources,
            "relationship": note_relationship.to_json() if note_relationship else None,
            "links": visible_body_links,
            "body": str(note["body"]) if include_body and not exclude_sensitive else None,
            "word_count": int(note["words"]),
            "heading_count": int(note["headings"]),
            "is_source": bool(note["is_source"]),
            "is_template": bool(note["is_template"]),
            "inbound_link_count": inbound[note_id],
            "outbound_link_count": outbound[note_id],
            "frontmatter": visible_frontmatter,
        }
        nodes.append(node)

    counts = {
        "nodes": len(nodes),
        "edges": len(edges),
        "source_nodes": sum(1 for node in nodes if node["is_source"]),
        "template_nodes": sum(1 for node in nodes if node["is_template"]),
        "relationship_nodes": sum(1 for node in nodes if node["relationship"]),
        "relationship_edges": sum(1 for edge in edges if edge["kind"] == "relationship"),
        "relationship_kinds": dict(sorted(Counter(str(node["relationship"]["kind"]) for node in nodes if node["relationship"]).items())),
        "missing_edges": sum(1 for edge in edges if edge["missing"]),
        "omitted_edges": omitted_edges,
        "broken_links": len(report["missing_links"]),
        "excluded_sensitive": excluded_sensitive_count,
        "excluded_templates": excluded_templates,
    }

    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "vault": str(vault),
        "counts": counts,
        "nodes": nodes,
        "edges": edges,
        "warnings": sorted(set(warnings)),
    }

def export_json(
    vault: Path,
    out: Path | None,
    exclude_body: bool,
    exclude_sensitive: bool,
    pretty: bool,
    include_templates: bool,
) -> None:
    data = build_export_graph(
        vault,
        include_body=not exclude_body,
        exclude_sensitive=exclude_sensitive,
        include_templates=include_templates,
    )
    indent = 2 if pretty else None
    payload = json.dumps(data, ensure_ascii=False, indent=indent)
    if pretty:
        payload += "\n"
    if out:
        out = out.expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")
        print(out)
    else:
        print(payload)
