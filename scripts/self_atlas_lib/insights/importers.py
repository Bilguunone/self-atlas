from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from ..constants import EXPORT_SCHEMA_VERSION
from ..init import append_domain_capture, append_source_log, ensure_domain_map
from ..models import ImportPlan
from ..vault import computed_note_id, frontmatter, require_vault, slugify, today, wiki_link, word_count
from .core import SUPPORTED_IMPORT_SUFFIXES

def import_title_from_source(source: str, source_type: str) -> str:
    if source_type == "url":
        parsed = urlparse(source)
        tail = Path(parsed.path).name or parsed.netloc
        return tail.replace("-", " ").replace("_", " ").title() or parsed.netloc
    return Path(source).stem.replace("-", " ").replace("_", " ").title() or "Imported Artifact"

def source_type_for(raw: str) -> str:
    if raw.startswith(("http://", "https://")):
        return "url"
    path = Path(raw).expanduser()
    if path.is_dir():
        return "directory"
    if path.is_file():
        return path.suffix.lower().lstrip(".")
    return "missing"

def import_sources(raw_sources: list[str], max_files: int) -> list[str]:
    expanded = []
    for raw in raw_sources:
        if raw.startswith(("http://", "https://")):
            expanded.append(raw)
            continue
        path = Path(raw).expanduser()
        if path.is_dir():
            files = [
                str(candidate)
                for candidate in sorted(path.rglob("*"))
                if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_IMPORT_SUFFIXES
            ]
            expanded.extend(files[:max_files])
        else:
            expanded.append(raw)
    return expanded[:max_files]

def read_import_body(raw: str, max_chars: int) -> tuple[str, str, str]:
    source_type = source_type_for(raw)
    if source_type == "url":
        parsed = urlparse(raw)
        body = (
            "## Import Metadata\n\n"
            f"- URL: {raw}\n"
            f"- Host: {parsed.netloc}\n"
            f"- Path: {parsed.path or '/'}\n"
            f"- Imported: {today()}\n\n"
            "## Raw Capture\n\n"
            "No page body was fetched. Add human context here, then use capture-review when there is real evidence.\n"
        )
        return body, source_type, ""
    path = Path(raw).expanduser()
    if not path.exists():
        return "", source_type, "source does not exist"
    if path.suffix.lower() not in SUPPORTED_IMPORT_SUFFIXES:
        return "", source_type, f"unsupported file type `{path.suffix}`"
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "", source_type, "file is not valid UTF-8 text"
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n\n[Truncated by artifact-import max-chars limit.]"
    body = (
        "## Import Metadata\n\n"
        f"- File name: {path.name}\n"
        f"- File type: {path.suffix.lower() or 'text'}\n"
        f"- Imported: {today()}\n\n"
        "## Raw Capture\n\n"
        f"{text.strip()}\n"
    )
    return body, source_type, ""

def unique_capture_relative(vault: Path, title: str) -> str:
    base = f"{today()}-artifact-{slugify(title)}"
    candidate = f"90 Sources/Captures/{base}.md"
    index = 2
    while (vault / candidate).exists():
        candidate = f"90 Sources/Captures/{base}-{index}.md"
        index += 1
    return candidate

def build_artifact_import(
    vault: Path,
    raw_sources: list[str],
    domain: str,
    sensitivity: str,
    apply: bool,
    max_files: int,
    max_chars: int,
) -> dict[str, object]:
    vault = require_vault(vault)
    sources = import_sources(raw_sources, max_files)
    plans: list[ImportPlan] = []
    applied_paths = []
    if apply:
        map_path = ensure_domain_map(vault, domain, sensitivity)
    else:
        map_path = None
    for source in sources:
        source_type = source_type_for(source)
        title = import_title_from_source(source, source_type)
        target = unique_capture_relative(vault, title)
        body, body_type, reason = read_import_body(source, max_chars)
        source_type = body_type or source_type
        words = word_count(body)
        status = "ready"
        if reason:
            status = "skipped"
        if apply and not reason:
            target_path = vault / target
            target_path.parent.mkdir(parents=True, exist_ok=True)
            capture_key = target.removesuffix(".md")
            content = (
                frontmatter(
                    "source",
                    domain,
                    sensitivity,
                    [f"self-atlas/{slugify(domain)}", "self-atlas/capture", "self-atlas/imported-artifact"],
                    note_id=computed_note_id(capture_key),
                    schema_version=EXPORT_SCHEMA_VERSION,
                )
                + f"# {title}\n\n"
                + f"## Domain\n\n- {wiki_link(str(map_path.relative_to(vault)), str(map_path.stem))}\n\n"
                + body
                + "\n## Extraction Targets\n\n"
                + "- People:\n"
                + "- Preferences:\n"
                + "- Values:\n"
                + "- Projects:\n"
                + "- Things bought, owned, or wanted:\n"
                + "- Contact details:\n"
                + "- Credential or account logistics:\n"
                + "- Health context:\n"
                + "- Open questions:\n"
                + "\n## Extracted Notes\n\n"
                + "\n## Follow-Up Threads\n"
            )
            target_path.write_text(content, encoding="utf-8")
            append_source_log(vault, target, title, domain)
            append_domain_capture(map_path, target, title)
            applied_paths.append(target)
            status = "imported"
        plans.append(
            ImportPlan(
                source=source,
                source_type=source_type,
                title=title,
                domain=domain,
                sensitivity=sensitivity,
                target_path=target,
                word_count=words,
                status=status,
                applied=apply and status == "imported",
                reason=reason,
            )
        )
    return {
        "vault": {"name": vault.name},
        "mode": "apply" if apply else "dry-run",
        "counts": {
            "sources": len(sources),
            "ready": sum(1 for plan in plans if plan.status == "ready"),
            "imported": sum(1 for plan in plans if plan.status == "imported"),
            "skipped": sum(1 for plan in plans if plan.status == "skipped"),
        },
        "plans": [plan.to_json() for plan in plans],
        "applied_paths": applied_paths,
        "note": "Imported artifacts are source captures only. Use capture-review before durable memory writes.",
    }

def print_artifact_import(
    vault: Path,
    raw_sources: list[str],
    domain: str,
    sensitivity: str,
    apply: bool,
    max_files: int,
    max_chars: int,
    json_output: bool,
) -> None:
    data = build_artifact_import(vault, raw_sources, domain, sensitivity, apply, max_files, max_chars)
    if json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("# Artifact Importer")
    print()
    print(f"Mode: {data['mode']}")
    print("Durable notes were not changed.")
    print()
    for plan in data["plans"]:
        suffix = f" ({plan['reason']})" if plan["reason"] else ""
        print(f"- {plan['status']}: {plan['target_path']} from {plan['source_type']}{suffix}")
    if not apply:
        print()
        print("Dry run only. Re-run with --apply to create source captures.")
