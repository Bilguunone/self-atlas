from __future__ import annotations

import datetime as dt
from pathlib import Path

from .constants import EXPORT_SCHEMA_VERSION
from .vault import (
    app_durable_notes,
    apply_app_fields_to_text,
    apply_relationship_fields_to_text,
    apply_source_fields_to_text,
    as_list,
    as_string,
    backup_note,
    computed_note_id,
    note_inventory,
    normalized_path,
    require_vault,
    source_links_from_text,
)


def infer_relationship_kind(note: dict[str, object]) -> str | None:
    frontmatter_data = note["frontmatter"]
    if not isinstance(frontmatter_data, dict):
        return None

    existing = as_string(frontmatter_data.get("relationship_kind")).strip()
    note_type = as_string(frontmatter_data.get("type")).strip()
    if note_type != "person":
        return None

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

def relationship_defaults(kind: str) -> dict[str, str]:
    defaults = {
        "love": {
            "relationship_context": "romantic",
            "emotional_charge": "high",
            "closeness": "central",
            "trust": "unknown",
            "relationship_phase": "active",
        },
        "friend": {
            "relationship_context": "social",
            "emotional_charge": "warm",
            "closeness": "unknown",
            "trust": "unknown",
            "relationship_phase": "active",
        },
        "family": {
            "relationship_context": "family",
            "emotional_charge": "complex",
            "closeness": "unknown",
            "trust": "unknown",
            "relationship_phase": "active",
        },
        "mentor": {
            "relationship_context": "mentorship",
            "emotional_charge": "guiding",
            "closeness": "unknown",
            "trust": "unknown",
            "relationship_phase": "active",
        },
        "collaborator": {
            "relationship_context": "work",
            "emotional_charge": "professional",
            "closeness": "unknown",
            "trust": "unknown",
            "relationship_phase": "active",
        },
        "person": {
            "relationship_context": "unknown",
            "emotional_charge": "unknown",
            "closeness": "unknown",
            "trust": "unknown",
            "relationship_phase": "active",
        },
    }
    fields = {"relationship_kind": kind}
    fields.update(defaults.get(kind, defaults["person"]))
    return fields


def migrate_app_fields(
    vault: Path,
    apply: bool,
    backup_dir: Path | None,
    include_templates: bool,
    fix_existing: bool,
) -> None:
    vault = require_vault(vault)
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = normalized_path(
        backup_dir
        or (vault.parent / f"{vault.name}-Backups" / f"app-fields-{timestamp}")
    )
    changed = []
    skipped = []
    conflicts = []

    for note in note_inventory(vault):
        relative = str(note["relative"])
        if note["is_template"] and not include_templates:
            continue
        path = note["path"]
        note_id = computed_note_id(str(note["key"]))
        updated, changed_fields, note_conflicts = apply_app_fields_to_text(
            str(note["text"]),
            note_id,
            EXPORT_SCHEMA_VERSION,
            fix_existing,
        )
        if note_conflicts and not changed_fields:
            conflicts.append((relative, note_conflicts))
            continue
        if not changed_fields:
            skipped.append(relative)
            continue
        changed.append((path, relative, changed_fields, updated, note_conflicts))

    print("# Migrate App Fields")
    print()
    print(f"Vault: {vault}")
    print(f"Mode: {'apply' if apply else 'dry-run'}")
    print(f"Schema version: {EXPORT_SCHEMA_VERSION}")
    print(f"Files to change: {len(changed)}")
    print(f"Files already ready: {len(skipped)}")
    print(f"Conflicts: {len(conflicts)}")
    if apply and changed:
        print(f"Backup: {backup_root}")
    print()

    for _, relative, changed_fields, _, note_conflicts in changed[:40]:
        suffix = ""
        if note_conflicts:
            suffix = " (fixed existing conflict)"
        print(f"- {relative}: {', '.join(changed_fields)}{suffix}")
    if len(changed) > 40:
        print(f"- ... {len(changed) - 40} more")

    if conflicts:
        print()
        print("## Existing Field Conflicts")
        for relative, note_conflicts in conflicts[:40]:
            print(f"- {relative}: {'; '.join(note_conflicts)}")
        if not fix_existing:
            print()
            print("Run with --fix-existing only if you want deterministic app ids to replace existing values.")

    if not apply:
        print()
        print("Dry run only. Re-run with --apply to write fields.")
        return

    for path, _, _, updated, _ in changed:
        backup_note(vault, path, backup_root)
        path.write_text(updated, encoding="utf-8")

    print()
    print(f"Applied changes: {len(changed)}")
    print("Only frontmatter app fields were changed; body text and memory values were left alone.")

def migrate_source_fields(
    vault: Path,
    apply: bool,
    backup_dir: Path | None,
    include_empty: bool,
    include_system: bool,
    include_sources: bool,
) -> None:
    vault = require_vault(vault)
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = normalized_path(
        backup_dir
        or (vault.parent / f"{vault.name}-Backups" / f"source-fields-{timestamp}")
    )
    changed = []
    skipped = []
    errors = []

    for note in note_inventory(vault):
        relative = str(note["relative"])
        if note["is_template"]:
            continue
        if relative.startswith("00 System/") and not include_system:
            continue
        if relative.startswith("90 Sources/") and not include_sources:
            continue

        derived_sources = source_links_from_text(str(note["text"]))
        frontmatter_data = note["frontmatter"]
        has_sources_field = "sources" in frontmatter_data
        if not derived_sources and not include_empty and not has_sources_field:
            skipped.append(relative)
            continue

        updated, did_change, error = apply_source_fields_to_text(str(note["text"]), derived_sources)
        if error:
            errors.append((relative, error))
            continue
        if not did_change:
            skipped.append(relative)
            continue
        changed.append((note["path"], relative, derived_sources, updated))

    print("# Migrate Source Fields")
    print()
    print(f"Vault: {vault}")
    print(f"Mode: {'apply' if apply else 'dry-run'}")
    print(f"Include empty fields: {include_empty}")
    print(f"Include 00 System notes: {include_system}")
    print(f"Include 90 Sources notes: {include_sources}")
    print(f"Files to change: {len(changed)}")
    print(f"Files already ready or skipped: {len(skipped)}")
    print(f"Errors: {len(errors)}")
    if apply and changed:
        print(f"Backup: {backup_root}")
    print()

    for _, relative, derived_sources, _ in changed[:50]:
        if derived_sources:
            print(f"- {relative}: {len(derived_sources)} source(s)")
        else:
            print(f"- {relative}: empty sources field")
    if len(changed) > 50:
        print(f"- ... {len(changed) - 50} more")

    if errors:
        print()
        print("## Errors")
        for relative, error in errors[:40]:
            print(f"- {relative}: {error}")

    if not apply:
        print()
        print("Dry run only. Re-run with --apply to write frontmatter source fields.")
        return

    for path, _, _, updated in changed:
        backup_note(vault, path, backup_root)
        path.write_text(updated, encoding="utf-8")

    print()
    print(f"Applied changes: {len(changed)}")
    print("Only frontmatter `sources` fields were changed; body text and memory values were left alone.")

def migrate_relationship_fields(
    vault: Path,
    apply: bool,
    backup_dir: Path | None,
) -> None:
    vault = require_vault(vault)
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = normalized_path(
        backup_dir
        or (vault.parent / f"{vault.name}-Backups" / f"relationship-fields-{timestamp}")
    )
    changed = []
    skipped = []
    errors = []

    for note in note_inventory(vault):
        relative = str(note["relative"])
        if note["is_template"] or note["is_source"]:
            continue
        if relative.startswith("00 System/") or relative.startswith("90 Sources/"):
            continue

        kind = infer_relationship_kind(note)
        if not kind:
            skipped.append(relative)
            continue

        updated, changed_fields, error = apply_relationship_fields_to_text(str(note["text"]), relationship_defaults(kind))
        if error:
            errors.append((relative, error))
            continue
        if not changed_fields:
            skipped.append(relative)
            continue
        changed.append((note["path"], relative, kind, changed_fields, updated))

    print("# Migrate Relationship Fields")
    print()
    print(f"Vault: {vault}")
    print(f"Mode: {'apply' if apply else 'dry-run'}")
    print(f"Files to change: {len(changed)}")
    print(f"Files already ready or skipped: {len(skipped)}")
    print(f"Errors: {len(errors)}")
    if apply and changed:
        print(f"Backup: {backup_root}")
    print()

    for _, relative, kind, changed_fields, _ in changed[:50]:
        print(f"- {relative}: {kind} ({', '.join(changed_fields)})")
    if len(changed) > 50:
        print(f"- ... {len(changed) - 50} more")

    if errors:
        print()
        print("## Errors")
        for relative, error in errors[:40]:
            print(f"- {relative}: {error}")

    if not apply:
        print()
        print("Dry run only. Re-run with --apply to write relationship frontmatter fields.")
        return

    for path, _, _, _, updated in changed:
        backup_note(vault, path, backup_root)
        path.write_text(updated, encoding="utf-8")

    print()
    print(f"Applied changes: {len(changed)}")
    print("Only relationship frontmatter fields were changed; body text and memory values were left alone.")
