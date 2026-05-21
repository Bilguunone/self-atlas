from __future__ import annotations

import re


WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")

WIKI_EDGE_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]")

WORD_RE = re.compile(r"[A-Za-z0-9_']+")

REQUIRED_FRONTMATTER = ("type", "sensitivity", "confidence")

RECOMMENDED_APP_FRONTMATTER = ("id", "schema_version")

EXPORT_SCHEMA_VERSION = 1

DEFAULT_THIN_NOTE_WORDS = 140

DEFAULT_SOURCE_CAPTURE_WORDS = 1500

DEFAULT_QUESTION_COUNT = 5

MAX_QUESTION_BATCH = 8

CORE_DIRS = [
    "00 System/Templates",
    "90 Sources/Captures",
]

FULL_EXTRA_DIRS = [
    "10 Self",
    "20 People/Family",
    "20 People/Friends",
    "20 People/Collaborators",
    "30 Work/Projects",
    "40 Health/Metrics",
    "50 Taste",
    "60 Interests",
    "70 Timeline",
    "80 Reflections",
]

DOMAIN_CONFIG = {
    "identity": {
        "folder": "10 Self",
        "map": "10 Self/Identity.md",
        "title": "Identity",
        "sensitivity": "normal",
    },
    "family": {
        "folder": "20 People/Family",
        "map": "20 People/Family.md",
        "title": "Family",
        "sensitivity": "private",
    },
    "work": {
        "folder": "30 Work/Projects",
        "map": "30 Work/Career.md",
        "title": "Career",
        "sensitivity": "normal",
    },
    "taste": {
        "folder": "50 Taste",
        "map": "50 Taste/Taste Profile.md",
        "title": "Taste Profile",
        "sensitivity": "normal",
    },
    "health": {
        "folder": "40 Health/Metrics",
        "map": "40 Health/Health Overview.md",
        "title": "Health Overview",
        "sensitivity": "health",
    },
    "desire": {
        "folder": "10 Self",
        "map": "10 Self/Desires.md",
        "title": "Desires",
        "sensitivity": "private",
    },
    "obsession": {
        "folder": "60 Interests",
        "map": "60 Interests/Obsessions.md",
        "title": "Obsessions",
        "sensitivity": "normal",
    },
}

DEFAULT_VAULT_NAME = "Self-Atlas-Vault"
