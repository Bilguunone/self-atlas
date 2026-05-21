#!/usr/bin/env python3
"""Install Self Atlas as a home-local Codex plugin."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


PLUGIN_NAME = "self-atlas"

PLUGIN_METADATA = {
    "name": PLUGIN_NAME,
    "version": "0.1.2",
    "description": "Build and query a private Markdown life graph for personal context, memory capture, and smart self-reflection.",
    "author": {
        "name": "Self Atlas contributors",
        "url": "https://github.com/Bilguunone/self-atlas",
    },
    "homepage": "https://github.com/Bilguunone/self-atlas",
    "repository": "https://github.com/Bilguunone/self-atlas",
    "license": "Apache-2.0",
    "keywords": [
        "markdown",
        "personal-memory",
        "knowledge-graph",
        "life-context",
        "graph-visualization",
    ],
    "skills": "./skills/",
    "interface": {
        "displayName": "Self Atlas",
        "shortDescription": "A private Markdown life graph for Codex.",
        "longDescription": (
            "Self Atlas helps Codex build, search, and refine a private Markdown graph "
            "about identity, people, work, taste, health context, goals, hobbies, obsessions, "
            "and life patterns. It favors small smart questions, wiki-style links, "
            "breadcrumb search, and compact capture loops."
        ),
        "developerName": "Self Atlas contributors",
        "category": "Productivity",
        "capabilities": [
            "Interactive",
            "Write",
            "Local Files",
            "Personal Context",
        ],
        "websiteURL": "https://github.com/Bilguunone/self-atlas",
        "privacyPolicyURL": "https://github.com/Bilguunone/self-atlas/blob/main/PRIVACY.md",
        "termsOfServiceURL": "https://github.com/Bilguunone/self-atlas/blob/main/LICENSE",
        "defaultPrompt": [
            "Ask me one Self Atlas question.",
            "Capture this into my Self Atlas.",
            "Answer from my Self Atlas notes.",
        ],
        "brandColor": "#7C5C3B",
        "composerIcon": "./assets/icon.svg",
        "logo": "./assets/logo.svg",
        "screenshots": [],
    },
}


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def marketplace_path() -> Path:
    return Path.home() / ".agents" / "plugins" / "marketplace.json"


def target_plugin_path() -> Path:
    return Path.home() / "plugins" / PLUGIN_NAME


def copy_plugin(source: Path, target: Path, force: bool, dry_run: bool) -> None:
    if source == target:
        print(f"Plugin is already in place: {target}")
        return
    if target.exists() and not force:
        raise SystemExit(
            f"Target already exists: {target}\n"
            "Re-run with --force to replace it, or move the existing plugin first."
        )
    print(f"Copy plugin: {source} -> {target}")
    if dry_run:
        return
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".DS_Store"),
    )

def write_plugin_metadata(target: Path, dry_run: bool) -> None:
    metadata_path = target / ".codex-plugin" / "plugin.json"
    print(f"Generate local plugin metadata: {metadata_path}")
    if dry_run:
        return
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(PLUGIN_METADATA, indent=2) + "\n", encoding="utf-8")


def load_marketplace(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "name": "local",
            "interface": {"displayName": "Local Plugins"},
            "plugins": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def update_marketplace(path: Path, dry_run: bool) -> None:
    data = load_marketplace(path)
    data.setdefault("name", "local")
    interface = data.setdefault("interface", {})
    if isinstance(interface, dict):
        interface.setdefault("displayName", "Local Plugins")
    plugins = data.setdefault("plugins", [])
    if not isinstance(plugins, list):
        raise SystemExit(f"Marketplace `plugins` must be a list: {path}")

    entry = {
        "name": PLUGIN_NAME,
        "source": {
            "source": "local",
            "path": f"./plugins/{PLUGIN_NAME}",
        },
        "policy": {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        },
        "category": "Productivity",
    }

    replaced = False
    for index, existing in enumerate(plugins):
        if isinstance(existing, dict) and existing.get("name") == PLUGIN_NAME:
            plugins[index] = entry
            replaced = True
            break
    if not replaced:
        plugins.append(entry)

    print(f"{'Update' if replaced else 'Create'} marketplace entry: {path}")
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install Self Atlas as a local Codex plugin")
    parser.add_argument("--force", action="store_true", help="Replace an existing ~/plugins/self-atlas folder")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing files")
    args = parser.parse_args(argv)

    source = plugin_root()
    target = target_plugin_path()
    copy_plugin(source, target, args.force, args.dry_run)
    if source.resolve() != target.resolve():
        write_plugin_metadata(target, args.dry_run)
    else:
        print("Skip generated plugin metadata because source and target are the same folder.")
    update_marketplace(marketplace_path(), args.dry_run)

    print()
    print("Next steps:")
    print("1. Restart Codex if it is already open.")
    print("2. Open Plugins and install/enable Self Atlas from Local Plugins.")
    print("3. Initialize a personal vault:")
    print("   python3 ~/plugins/self-atlas/scripts/self_atlas.py ensure --vault ~/Documents/Self-Atlas-Vault --yes")
    print("4. Start a chat with: @Self Atlas ask me one question")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
