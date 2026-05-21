#!/usr/bin/env python3
"""Check that a release tree does not include obvious private vault material."""

from __future__ import annotations

from pathlib import Path
import sys


TEXT_SUFFIXES = {
    ".css",
    ".json",
    ".md",
    ".py",
    ".svg",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

SKIP_DIRS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "venv",
}

BLOCKED_TEXT = (
    "/" + "Users/",
)

PRIVATE_RESIDUE_PATTERNS = (
    "tum" + "endari",
    "gen" + "ie",
    "vel" + "um",
    "tw" + "ill",
    "clo" + "zy",
    "uni" + "vision",
    "mst" + "ars",
    "ard" + "art",
    "seed" + "share",
    "mon" + "arty",
    "sos " + "medica",
    "nose " + "surgery",
    "no job and " + "no money",
)

BLOCKED_FILE_NAMES = {
    ".DS_Store",
    "self-atlas.graph.json",
    "self-atlas.timeline.json",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_local_patterns(root: Path) -> list[str]:
    path = root / ".privacy-patterns"
    if not path.exists():
        return []
    patterns = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            patterns.append(value)
    return patterns


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def is_allowed_demo_capture(relative: Path) -> bool:
    parts = relative.parts
    return len(parts) >= 4 and parts[:3] == ("examples", "demo-vault", "90 Sources")


def scan_files(root: Path) -> list[str]:
    problems = []
    blocked_text = tuple(item.lower() for item in (*BLOCKED_TEXT, *PRIVATE_RESIDUE_PATTERNS, *load_local_patterns(root)))
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if should_skip(relative):
            continue
        if path.name in BLOCKED_FILE_NAMES:
            problems.append(f"blocked file: {relative}")
            continue
        if path.is_dir():
            if relative.parts[:2] == ("90 Sources", "Captures"):
                problems.append(f"private capture directory at repo root: {relative}")
            continue
        if path.suffix in {".graph.json", ".timeline.json"}:
            problems.append(f"generated export file: {relative}")
            continue
        if relative.parts[:2] == ("90 Sources", "Captures") and not is_allowed_demo_capture(relative):
            problems.append(f"private capture file at repo root: {relative}")
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lowered = text.lower()
        for blocked in blocked_text:
            if blocked and blocked in lowered:
                problems.append(f"blocked text `{blocked}` in {relative}")
    return problems


def main() -> int:
    root = project_root()
    problems = scan_files(root)
    if problems:
        print("Public release check failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("Public release check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
