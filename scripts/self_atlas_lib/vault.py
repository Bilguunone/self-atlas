from __future__ import annotations

import datetime as dt
import re
import shutil
from collections import defaultdict
from pathlib import Path

from .constants import (
    DEFAULT_VAULT_NAME,
    REQUIRED_FRONTMATTER,
    WIKI_LINK_RE,
    WORD_RE,
)


def today() -> str:
    return dt.date.today().isoformat()

def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "untitled"

def titleize(value: str) -> str:
    words = re.sub(r"[^a-zA-Z0-9]+", " ", value).strip().split()
    return " ".join(word.capitalize() for word in words) or "Untitled"

def default_vault_path() -> Path:
    return Path.home() / "Documents" / DEFAULT_VAULT_NAME

def normalized_path(path: Path) -> Path:
    return path.expanduser().resolve()

def require_vault(vault: Path) -> Path:
    vault = normalized_path(vault)
    if not is_self_atlas_vault(vault):
        raise SystemExit(f"Self Atlas vault is not initialized: {vault}")
    return vault

def markdown_files(vault: Path) -> list[Path]:
    return sorted(path for path in vault.rglob("*.md") if path.is_file())

def relative_md_key(vault: Path, path: Path) -> str:
    return path.relative_to(vault).with_suffix("").as_posix()

def is_template_note(vault: Path, path: Path) -> bool:
    return path.relative_to(vault).as_posix().startswith("00 System/Templates/")

def is_source_capture(vault: Path, path: Path, frontmatter_data: dict[str, object] | None = None) -> bool:
    relative = path.relative_to(vault).as_posix()
    if relative.startswith("90 Sources/Captures/"):
        return True
    return (frontmatter_data or {}).get("type") == "source"

def read_note(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def unquote_frontmatter_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value

def parse_frontmatter_value(value: str) -> object:
    value = value.strip()
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [unquote_frontmatter_value(part.strip()) for part in inner.split(",") if part.strip()]
    return unquote_frontmatter_value(value)

def parse_frontmatter_text(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    data: dict[str, object] = {}
    current_list_key: str | None = None
    for line in parts[1].splitlines():
        if line.startswith("  - ") and current_list_key:
            existing = data.setdefault(current_list_key, [])
            if isinstance(existing, list):
                existing.append(unquote_frontmatter_value(line[4:].strip()))
            continue
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        parsed = parse_frontmatter_value(value)
        if value.strip() == "":
            parsed = []
            current_list_key = key
        else:
            current_list_key = key if isinstance(parsed, list) else None
        data[key] = parsed
    return data, parts[2].lstrip("\n")

def note_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip() or fallback
    return fallback

def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))

def heading_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if re.match(r"^#{1,6}\s+", line))

def bullet_lines(text: str) -> list[str]:
    return [line.strip()[2:].strip() for line in text.splitlines() if line.strip().startswith("- ")]

def clean_bullet(line: str) -> str:
    line = WIKI_LINK_RE.sub(lambda match: match.group(1).split("/")[-1], line)
    line = re.sub(r"Source:.*$", "", line).strip()
    line = re.sub(r"`([^`]*)`", r"\1", line)
    line = re.sub(r"[^a-zA-Z0-9]+", " ", line).lower().strip()
    return line

def note_inventory(vault: Path) -> list[dict[str, object]]:
    notes = []
    for path in markdown_files(vault):
        text = read_note(path)
        frontmatter_data, body = parse_frontmatter_text(text)
        relative = path.relative_to(vault).as_posix()
        notes.append(
            {
                "path": path,
                "relative": relative,
                "key": relative_md_key(vault, path),
                "text": text,
                "body": body,
                "frontmatter": frontmatter_data,
                "title": note_title(body, path.stem),
                "words": word_count(body),
                "headings": heading_count(body),
                "links": WIKI_LINK_RE.findall(text),
                "is_template": is_template_note(vault, path),
                "is_source": is_source_capture(vault, path, frontmatter_data),
            }
        )
    return notes

def link_indexes(notes: list[dict[str, object]]) -> tuple[dict[str, dict[str, object]], dict[str, list[dict[str, object]]]]:
    by_key = {str(note["key"]): note for note in notes}
    by_base: dict[str, list[dict[str, object]]] = defaultdict(list)
    for key, note in by_key.items():
        by_base[Path(key).name].append(note)
    return by_key, by_base

def link_exists(target: str, by_key: dict[str, dict[str, object]], by_base: dict[str, list[dict[str, object]]]) -> bool:
    target = target.strip()
    if target in by_key:
        return True
    if target.endswith(".md") and target[:-3] in by_key:
        return True
    return Path(target).name in by_base

def resolve_link_target(
    target: str,
    by_key: dict[str, dict[str, object]],
    by_base: dict[str, list[dict[str, object]]],
) -> tuple[dict[str, object] | None, bool]:
    target = target.strip()
    if target in by_key:
        return by_key[target], False
    if target.endswith(".md") and target[:-3] in by_key:
        return by_key[target[:-3]], False
    matches = by_base.get(Path(target).name, [])
    if len(matches) == 1:
        return matches[0], False
    if len(matches) > 1:
        return None, True
    return None, False

def computed_note_id(note_key: str) -> str:
    return f"note:{slugify(note_key)}"

def frontmatter_has_key(frontmatter_text: str, key: str) -> bool:
    return re.search(rf"(?m)^{re.escape(key)}\s*:", frontmatter_text) is not None

def frontmatter_scalar_matches(value: object, expected: str) -> bool:
    if value is None:
        return False
    return as_string(value).strip() == expected

def replace_frontmatter_scalar(frontmatter_text: str, key: str, value: str) -> str:
    return re.sub(
        rf"(?m)^{re.escape(key)}\s*:.*$",
        f"{key}: {value}",
        frontmatter_text,
        count=1,
    )

def yaml_list(key: str, values: tuple[str, ...], quote: bool = False) -> list[str]:
    if not values:
        return [f"{key}: []"]
    lines = [f"{key}:"]
    for value in values:
        rendered = f'"{value}"' if quote else value
        lines.append(f"  - {rendered}")
    return lines

def replace_or_insert_frontmatter_scalar(
    frontmatter_text: str,
    key: str,
    value: str,
    after_key: str = "type",
) -> str:
    if frontmatter_has_key(frontmatter_text, key):
        return replace_frontmatter_scalar(frontmatter_text, key, value)

    lines = frontmatter_text.splitlines()
    insert_at = len(lines)
    for index, line in enumerate(lines):
        if re.match(rf"^{re.escape(after_key)}\s*:", line):
            insert_at = index + 1
            while insert_at < len(lines) and lines[insert_at].startswith("  - "):
                insert_at += 1
            break
    lines.insert(insert_at, f"{key}: {value}")
    return "\n".join(lines)

def replace_or_insert_frontmatter_list(
    frontmatter_text: str,
    key: str,
    values: list[str],
    after_key: str = "links",
) -> str:
    lines = frontmatter_text.splitlines()
    block = yaml_list(key, tuple(values), quote=True)

    index = 0
    while index < len(lines):
        if re.match(rf"^{re.escape(key)}\s*:", lines[index]):
            end = index + 1
            while end < len(lines) and lines[end].startswith("  - "):
                end += 1
            lines[index:end] = block
            return "\n".join(lines)
        index += 1

    insert_at = len(lines)
    index = 0
    while index < len(lines):
        if re.match(rf"^{re.escape(after_key)}\s*:", lines[index]):
            insert_at = index + 1
            while insert_at < len(lines) and lines[insert_at].startswith("  - "):
                insert_at += 1
            break
        index += 1

    lines[insert_at:insert_at] = block
    return "\n".join(lines)

def apply_app_fields_to_text(
    text: str,
    note_id: str,
    schema_version: int,
    fix_existing: bool,
) -> tuple[str, list[str], list[str]]:
    frontmatter_data, _ = parse_frontmatter_text(text)
    if not frontmatter_data:
        return text, [], ["missing frontmatter"]

    expected = {
        "id": note_id,
        "schema_version": str(schema_version),
    }
    conflicts = []
    for key, value in expected.items():
        if frontmatter_data.get(key) and not frontmatter_scalar_matches(frontmatter_data.get(key), value):
            conflicts.append(f"{key}: existing `{as_string(frontmatter_data.get(key))}`, expected `{value}`")
    if conflicts and not fix_existing:
        return text, [], conflicts

    parts = text.split("---", 2)
    if len(parts) < 3:
        return text, [], ["frontmatter parse failed"]

    frontmatter_text = parts[1].lstrip("\n")
    changed_fields = []
    prepended_lines = []

    for key, value in expected.items():
        has_key = frontmatter_has_key(frontmatter_text, key)
        if not has_key:
            prepended_lines.append(f"{key}: {value}")
            changed_fields.append(key)
        elif fix_existing and not frontmatter_scalar_matches(frontmatter_data.get(key), value):
            frontmatter_text = replace_frontmatter_scalar(frontmatter_text, key, value)
            changed_fields.append(key)

    if not changed_fields:
        return text, [], []

    prefix = "\n".join(prepended_lines)
    if prefix:
        frontmatter_text = prefix + "\n" + frontmatter_text
    if not frontmatter_text.endswith("\n"):
        frontmatter_text += "\n"
    updated = "---\n" + frontmatter_text + "---" + parts[2]
    return updated, changed_fields, conflicts if fix_existing else []

def apply_source_fields_to_text(
    text: str,
    sources: list[str],
) -> tuple[str, bool, str | None]:
    frontmatter_data, _ = parse_frontmatter_text(text)
    if not frontmatter_data:
        return text, False, "missing frontmatter"

    parts = text.split("---", 2)
    if len(parts) < 3:
        return text, False, "frontmatter parse failed"

    existing_sources = [
        normalized_source_key(source)
        for source in as_list(frontmatter_data.get("sources"))
        if normalized_source_key(source)
    ]
    merged = sorted(set(existing_sources + sources))
    if "sources" in frontmatter_data and existing_sources == merged:
        return text, False, None

    frontmatter_text = parts[1].lstrip("\n")
    frontmatter_text = replace_or_insert_frontmatter_list(frontmatter_text, "sources", merged, "links")
    if not frontmatter_text.endswith("\n"):
        frontmatter_text += "\n"
    updated = "---\n" + frontmatter_text + "---" + parts[2]
    return updated, True, None

def apply_relationship_fields_to_text(
    text: str,
    fields: dict[str, str],
) -> tuple[str, list[str], str | None]:
    frontmatter_data, _ = parse_frontmatter_text(text)
    if not frontmatter_data:
        return text, [], "missing frontmatter"

    parts = text.split("---", 2)
    if len(parts) < 3:
        return text, [], "frontmatter parse failed"

    frontmatter_text = parts[1].lstrip("\n")
    changed_fields = []
    after_key = "type"
    for key, value in fields.items():
        existing = frontmatter_data.get(key)
        if key in frontmatter_data and as_string(existing).strip() not in {"", "[]"}:
            after_key = key
            continue
        frontmatter_text = replace_or_insert_frontmatter_scalar(frontmatter_text, key, value, after_key)
        changed_fields.append(key)
        after_key = key

    if not changed_fields:
        return text, [], None

    if not frontmatter_text.endswith("\n"):
        frontmatter_text += "\n"
    updated = "---\n" + frontmatter_text + "---" + parts[2]
    return updated, changed_fields, None

def backup_note(vault: Path, path: Path, backup_root: Path) -> None:
    relative = path.relative_to(vault)
    target = backup_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)

def as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    raw = str(value).strip()
    if not raw or raw == "[]":
        return []
    parsed = parse_frontmatter_value(raw)
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [str(parsed)]

def as_string(value: object, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)

def normalized_source_key(value: str) -> str:
    value = value.strip().strip('"').strip("'")
    if value.startswith("[[") and value.endswith("]]"):
        value = value[2:-2].split("|", 1)[0].split("#", 1)[0].strip()
    if value.endswith(".md"):
        value = value[:-3]
    return value

def source_links_from_text(text: str) -> list[str]:
    sources = []
    seen = set()
    for match in WIKI_LINK_RE.finditer(text):
        target = normalized_source_key(match.group(1))
        if target.startswith("90 Sources/Captures/") and target not in seen:
            sources.append(target)
            seen.add(target)
    return sources

def note_has_source_reference(note: dict[str, object]) -> bool:
    body = str(note["body"])
    frontmatter_data = note["frontmatter"]
    frontmatter_links = as_list(frontmatter_data.get("links")) if isinstance(frontmatter_data, dict) else []
    frontmatter_sources = as_list(frontmatter_data.get("sources")) if isinstance(frontmatter_data, dict) else []
    if frontmatter_sources:
        return True
    if "Source:" in body or "Sources:" in body:
        return True
    if "[[90 Sources/" in body:
        return True
    return any("90 Sources/" in link for link in frontmatter_links)

def app_durable_notes(notes: list[dict[str, object]]) -> list[dict[str, object]]:
    durable = []
    for note in notes:
        relative = str(note["relative"])
        if note["is_template"] or note["is_source"] or relative.startswith("00 System/") or relative.startswith("90 Sources/"):
            continue
        durable.append(note)
    return durable

def collect_validation(vault: Path) -> dict[str, object]:
    notes = note_inventory(vault)
    by_key, by_base = link_indexes(notes)
    missing_links = []
    total_links = 0
    missing_frontmatter = []
    missing_metadata = []
    ambiguous_basename = {base: values for base, values in by_base.items() if len(values) > 1}

    for note in notes:
        frontmatter_data = note["frontmatter"]
        relative = str(note["relative"])
        if not frontmatter_data:
            missing_frontmatter.append(relative)
        else:
            for key in REQUIRED_FRONTMATTER:
                if not frontmatter_data.get(key):
                    missing_metadata.append((relative, key))
        for target in note["links"]:
            total_links += 1
            if not link_exists(str(target), by_key, by_base):
                missing_links.append((relative, str(target)))

    return {
        "notes": notes,
        "total_links": total_links,
        "missing_links": missing_links,
        "missing_frontmatter": missing_frontmatter,
        "missing_metadata": missing_metadata,
        "ambiguous_basename": ambiguous_basename,
    }

def extract_section_bullets(vault: Path, relative: str, heading: str | None = None) -> list[str]:
    path = vault / relative
    if not path.exists():
        return []
    text = read_note(path)
    if heading:
        marker = f"## {heading}"
        if marker in text:
            start = text.index(marker)
            next_heading = text.find("\n## ", start + len(marker))
            text = text[start:] if next_heading == -1 else text[start:next_heading]
    return bullet_lines(text)

def extract_section_text(text: str, heading: str) -> str:
    marker = f"## {heading}"
    if marker not in text:
        return ""
    start = text.index(marker) + len(marker)
    next_heading = text.find("\n## ", start)
    section_text = text[start:] if next_heading == -1 else text[start:next_heading]
    return section_text.strip()

def is_self_atlas_vault(vault: Path) -> bool:
    home = vault / "00 System" / "Home.md"
    if not home.exists():
        return False
    try:
        return "Self Atlas" in home.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False

def has_existing_content(vault: Path) -> bool:
    if not vault.exists():
        return False
    return any(vault.iterdir())

def frontmatter(kind: str, domain: str, sensitivity: str, tags: list[str]) -> str:
    tag_lines = "\n".join(f"  - {tag}" for tag in tags)
    return (
        "---\n"
        f"type: {kind}\n"
        "status: active\n"
        f"sensitivity: {sensitivity}\n"
        "confidence: confirmed\n"
        f"created: {today()}\n"
        f"updated: {today()}\n"
        "aliases: []\n"
        "tags:\n"
        f"{tag_lines if tag_lines else '  - self-atlas/' + domain}\n"
        "links: []\n"
        "---\n"
    )

def write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True

def wiki_link(relative_path: str, alias: str | None = None) -> str:
    target = relative_path[:-3] if relative_path.endswith(".md") else relative_path
    if alias:
        return f"[[{target}|{alias}]]"
    return f"[[{target}]]"

def append_under_heading(path: Path, heading: str, line: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if line in text:
        return False

    marker = f"## {heading}"
    if marker not in text:
        updated = text.rstrip() + f"\n\n{marker}\n\n{line}\n"
    else:
        start = text.index(marker)
        next_heading = text.find("\n## ", start + len(marker))
        insert_at = len(text) if next_heading == -1 else next_heading
        before = text[:insert_at].rstrip()
        after = text[insert_at:]
        updated = before + f"\n{line}\n" + after

    path.write_text(updated, encoding="utf-8")
    return True
