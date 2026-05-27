from __future__ import annotations

from pathlib import Path

from .constants import EXPORT_SCHEMA_VERSION
from .init import append_domain_capture, append_source_log, domain_config, ensure_domain_map
from .vault import (
    computed_note_id,
    frontmatter,
    is_self_atlas_vault,
    normalized_path,
    slugify,
    today,
    wiki_link,
)


def capture(vault: Path, title: str, body: str, domain: str, sensitivity: str, tags: list[str]) -> None:
    vault = normalized_path(vault)
    if not is_self_atlas_vault(vault):
        script_path = Path(__file__).resolve().parent.parent / "self_atlas.py"
        raise SystemExit(
            "Self Atlas vault is not initialized. "
            f"Run: python3 {script_path} ensure --vault {vault}"
        )
    normalized_domain = slugify(domain)
    map_path = ensure_domain_map(vault, normalized_domain, sensitivity)
    capture_dir = vault / "90 Sources" / "Captures"
    capture_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{today()}-{slugify(title)}.md"
    path = capture_dir / filename
    capture_key = f"90 Sources/Captures/{filename[:-3]}"
    body = body.strip()
    note_tags = tags or [f"self-atlas/{normalized_domain}", "self-atlas/capture"]
    content = (
        frontmatter(
            "source",
            normalized_domain,
            sensitivity,
            note_tags,
            note_id=computed_note_id(capture_key),
            schema_version=EXPORT_SCHEMA_VERSION,
        )
        + f"# {title}\n\n"
        + "## Domain\n\n"
        + f"- {wiki_link(str(map_path.relative_to(vault)), domain_config(normalized_domain)['title'])}\n\n"
        + "## Raw Capture\n\n"
        + f"{body}\n\n"
        + "## Extraction Targets\n\n"
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
    if path.exists():
        raise SystemExit(f"Capture already exists: {path}")
    path.write_text(content, encoding="utf-8")
    capture_relative = str(path.relative_to(vault))
    append_source_log(vault, capture_relative, title, normalized_domain)
    append_domain_capture(map_path, capture_relative, title)
    print(path)
    print(f"Updated domain map: {map_path}")

def search(vault: Path, query: str) -> None:
    vault = normalized_path(vault)
    if not vault.exists():
        raise SystemExit(f"Vault does not exist: {vault}")
    needle = query.lower()
    matches = []
    for path in vault.rglob("*.md"):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for index, line in enumerate(lines, start=1):
            if needle in line.lower():
                matches.append((path, index, line.strip()))
    for path, index, line in matches[:50]:
        print(f"{path}:{index}: {line}")
    if not matches:
        print("No matches.")
