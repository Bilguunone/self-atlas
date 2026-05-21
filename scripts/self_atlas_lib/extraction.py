from __future__ import annotations

import json
import re
from pathlib import Path

from .constants import DOMAIN_CONFIG, WIKI_LINK_RE
from .models import DurableNotePatch, ExtractionPlan, LinkPatch, MemoryCandidate, RawCapture, ReviewFlag, SourceEvidence
from .questions import has_any_keyword, infer_question_domain
from .vault import (
    as_list,
    as_string,
    bullet_lines,
    extract_section_text,
    normalized_source_key,
    note_title,
    parse_frontmatter_text,
    read_note,
    relative_md_key,
    require_vault,
    wiki_link,
)


def wiki_targets_from_text(text: str) -> list[str]:
    targets = []
    seen = set()
    for match in WIKI_LINK_RE.finditer(text):
        target = normalized_source_key(match.group(1))
        if target and target not in seen:
            targets.append(target)
            seen.add(target)
    return targets

def compact_excerpt(text: str, limit: int = 420) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."

def evidence_tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]{3,}", text)}

def best_raw_excerpt(raw_text: str, claim: str) -> str:
    if not raw_text.strip():
        return ""
    if claim and claim in raw_text:
        index = raw_text.index(claim)
        start = max(0, index - 120)
        end = min(len(raw_text), index + len(claim) + 120)
        return compact_excerpt(raw_text[start:end])

    claim_tokens = evidence_tokens(claim)
    best_line = ""
    best_score = 0
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        score = len(evidence_tokens(stripped) & claim_tokens)
        if score > best_score:
            best_line = stripped
            best_score = score
    if best_line and best_score:
        return compact_excerpt(best_line)
    return compact_excerpt(raw_text)

def line_hint_for_excerpt(source_text: str, section: str | None, excerpt: str) -> int | None:
    first_excerpt_line = excerpt.splitlines()[0].strip() if excerpt.strip() else ""
    if first_excerpt_line:
        for index, line in enumerate(source_text.splitlines(), start=1):
            if first_excerpt_line and first_excerpt_line in line:
                return index

    if section:
        marker = f"## {section}"
        for index, line in enumerate(source_text.splitlines(), start=1):
            if line.strip() == marker:
                return index
    return None

def build_source_evidence(
    source_path: str,
    source_text: str,
    section: str | None,
    section_text: str,
    claim: str,
    confidence: str,
    sensitivity: str,
) -> SourceEvidence:
    excerpt = best_raw_excerpt(section_text, claim)
    return SourceEvidence(
        source_path=source_path,
        claim_text=claim,
        raw_excerpt=excerpt,
        section=section,
        line_hint=line_hint_for_excerpt(source_text, section, excerpt),
        confidence=confidence,
        sensitivity=sensitivity,
    )

def relationship_candidate_kind(target: str) -> str | None:
    lowered = target.lower()
    if lowered.startswith("25 love/"):
        return "relationship_love"
    if lowered.startswith("20 people/friends/"):
        return "relationship_friend"
    if lowered.startswith("20 people/family/"):
        return "relationship_family"
    if lowered.startswith("20 people/mentors/"):
        return "relationship_mentor"
    if lowered.startswith("20 people/work/") or lowered.startswith("20 people/collaborators/"):
        return "relationship_collaborator"
    return None

def first_section_text(body: str, headings: tuple[str, ...]) -> tuple[str | None, str]:
    for heading in headings:
        text = extract_section_text(body, heading)
        if text:
            return heading, text
    return None, ""

def infer_candidate_kind(text: str) -> str:
    wiki_targets = wiki_targets_from_text(text)
    if wiki_targets:
        target = wiki_targets[0]
        specific_relationship_kind = relationship_candidate_kind(target)
        if specific_relationship_kind:
            return specific_relationship_kind
        if target.startswith("20 People/"):
            return "person"
        if target.startswith("30 Work/Projects/"):
            return "project"
        if target.startswith("30 Work/Employers/") or target.startswith("30 Work/"):
            return "work"
        if target.startswith("40 Health/"):
            return "health_observation"
        if target.startswith("50 Taste/"):
            return "preference"
        if target.startswith("80 Reflections/"):
            return "pattern"
    if has_any_keyword(
        text,
        (
            "work",
            "role",
            "responsibility",
            "responsibilities",
            "front-end",
            "frontend",
            "swiftui",
            "colleague",
            "team",
            "ownership",
            "employer",
            "genie",
        ),
    ):
        return "work"
    if has_any_keyword(text, ("velum", "project", "prototype", "app", "product", "startup", "twill", "clozy")):
        return "project"
    if has_any_keyword(text, ("taste", "reject", "generic", "soulless", "music", "design", "motion", "ui")):
        return "preference"
    if has_any_keyword(text, ("health", "heart", "pain", "sleep", "energy", "body")):
        return "health_observation"
    if has_any_keyword(text, ("visa", "embassy", "appointment", "document", "deadline", "travel")):
        return "logistics_thread"
    if "?" in text:
        return "question"
    if has_any_keyword(text, ("need", "fear", "pattern", "tension", "structure", "pressure")):
        return "pattern"
    if has_any_keyword(text, ("tumendari", "girlfriend", "boyfriend", "partner", "romantic")):
        return "relationship_love"
    if has_any_keyword(text, ("joao", "colleague", "coworker", "collaborator", "team")):
        return "relationship_collaborator"
    if has_any_keyword(text, ("friend", "friends", "classmate", "parkour")):
        return "relationship_friend"
    if has_any_keyword(text, ("mother", "father", "sister", "family")):
        return "relationship_family"
    if has_any_keyword(text, ("mentor", "guidance", "teacher", "advisor")):
        return "relationship_mentor"
    if has_any_keyword(text, ("person",)):
        return "person"
    return "fact"

def likely_patch_section(candidate_kind: str) -> str:
    sections = {
        "person": "What We Know",
        "project": "What We Know",
        "work": "What We Know",
        "preference": "Evidence",
        "health_observation": "Context",
        "logistics_thread": "Current Status",
        "question": "Open Questions",
        "pattern": "What We Know",
        "fact": "What We Know",
        "relationship_love": "What We Know",
        "relationship_friend": "What We Know",
        "relationship_family": "What We Know",
        "relationship_mentor": "What We Know",
        "relationship_collaborator": "What We Know",
    }
    return sections.get(candidate_kind, "What We Know")

def candidate_target_hint(candidate: str, source_links: list[str], domain: str, candidate_kind: str) -> str | None:
    lowered = candidate.lower()
    wiki_targets = wiki_targets_from_text(candidate)
    durable_targets = [target for target in wiki_targets if not target.startswith("90 Sources/")]
    if durable_targets:
        return durable_targets[0]
    for link in source_links:
        basename = Path(link).name.lower()
        aliasish = basename.replace("-", " ")
        if basename in lowered or aliasish in lowered:
            return link
    kind_targets = {
        "question": "00 System/Question Queue",
        "pattern": "80 Reflections/Patterns",
        "preference": "50 Taste/Taste Profile",
        "health_observation": "40 Health/Health Overview",
        "logistics_thread": "00 System/Open Threads",
    }
    if candidate_kind in kind_targets:
        return kind_targets[candidate_kind]
    if domain in DOMAIN_CONFIG:
        return DOMAIN_CONFIG[domain]["map"].removesuffix(".md")
    return None

def build_extraction_plan(vault: Path, source: str) -> ExtractionPlan:
    vault = require_vault(vault)
    source_key = source.removesuffix(".md")
    path = vault / f"{source_key}.md"
    if not path.exists():
        path = vault / source
    if not path.exists():
        raise SystemExit(f"Source note does not exist: {source}")

    text = read_note(path)
    frontmatter_data, body = parse_frontmatter_text(text)
    relative = path.relative_to(vault).as_posix()
    source_key = relative_md_key(vault, path)
    raw_section = "Raw Capture"
    raw_text = extract_section_text(body, raw_section)
    if not raw_text:
        raw_section = "Raw Answer"
        raw_text = extract_section_text(body, raw_section)
    if not raw_text:
        raw_section = None
    _extracted_section, extracted_text = first_section_text(body, ("Extracted Notes", "Derived Notes"))
    follow_up_section, follow_up_text = first_section_text(body, ("Follow-Up Threads", "Open Questions"))
    candidate_lines = bullet_lines(extracted_text) if extracted_text else []
    follow_up_lines = bullet_lines(follow_up_text) if follow_up_text else []
    source_links = [
        normalized_source_key(link)
        for link in as_list(frontmatter_data.get("links"))
        if not normalized_source_key(link).startswith("90 Sources/")
    ]
    domain = infer_question_domain(" ".join(as_list(frontmatter_data.get("tags"))) + " " + body)

    raw_capture = RawCapture(
        path=relative,
        title=note_title(body, path.stem),
        sensitivity=as_string(frontmatter_data.get("sensitivity"), "normal"),
        confidence=as_string(frontmatter_data.get("confidence"), "confirmed"),
        tags=tuple(as_list(frontmatter_data.get("tags"))),
        links=tuple(as_list(frontmatter_data.get("links"))),
        raw_text=raw_text,
    )

    memory_candidates = []
    durable_patches = []
    link_patches = []
    link_patch_keys = set()
    review_flags = []

    if not raw_text:
        review_flags.append(ReviewFlag("warning", "Source note has no `Raw Capture` or `Raw Answer` section.", relative))
    if not candidate_lines:
        review_flags.append(ReviewFlag("warning", "No `Extracted Notes` or `Derived Notes` bullets found; extraction needs human or model review.", relative))

    for candidate in candidate_lines:
        kind = infer_candidate_kind(candidate)
        target_hint = candidate_target_hint(candidate, source_links, domain, kind)
        evidence = build_source_evidence(
            relative,
            text,
            raw_section,
            raw_text,
            candidate,
            raw_capture.confidence,
            raw_capture.sensitivity,
        )
        memory_candidates.append(
            MemoryCandidate(
                kind=kind,
                text=candidate,
                confidence=raw_capture.confidence,
                evidence=evidence,
                target_hint=target_hint,
            )
        )
        if target_hint:
            durable_patches.append(
                DurableNotePatch(
                    target=target_hint,
                    action="append",
                    section=likely_patch_section(kind),
                    content=f"- {candidate} Source: {wiki_link(source_key)}.",
                    source=source_key,
                    evidence=evidence,
                )
            )
            link_patch_key = (target_hint, source_key, "ensure_source_frontmatter")
            if link_patch_key not in link_patch_keys:
                link_patches.append(
                    LinkPatch(
                        source=target_hint,
                        target=source_key,
                        action="ensure_source_frontmatter",
                        reason="Durable note should retain source lineage for extracted memories from this source.",
                    )
                )
                link_patch_keys.add(link_patch_key)
        else:
            review_flags.append(ReviewFlag("review", "Candidate needs a target note decision.", candidate))

    for follow_up in follow_up_lines:
        evidence = build_source_evidence(
            relative,
            text,
            follow_up_section,
            follow_up_text,
            follow_up,
            raw_capture.confidence,
            raw_capture.sensitivity,
        )
        memory_candidates.append(
            MemoryCandidate(
                kind="question",
                text=follow_up,
                confidence=raw_capture.confidence,
                evidence=evidence,
                target_hint="00 System/Question Queue",
            )
        )
        durable_patches.append(
            DurableNotePatch(
                target="00 System/Question Queue",
                action="append",
                section="Next Questions",
                content=f"- {follow_up} Source: {wiki_link(source_key)}.",
                source=source_key,
                evidence=evidence,
            )
        )

    if raw_capture.sensitivity in {"private", "health", "financial", "intimate"}:
        review_flags.append(ReviewFlag("sensitive", f"Source sensitivity is `{raw_capture.sensitivity}`; review before applying patches.", relative))

    return ExtractionPlan(
        raw_capture=raw_capture,
        memory_candidates=tuple(memory_candidates),
        durable_note_patches=tuple(durable_patches),
        link_patches=tuple(link_patches),
        review_flags=tuple(review_flags),
    )

def print_extraction_plan(plan: ExtractionPlan, json_output: bool) -> None:
    if json_output:
        print(json.dumps(plan.to_json(), ensure_ascii=False, indent=2))
        return

    data = plan.to_json()
    print("# Extraction Plan")
    print()
    print(f"Source: {data['raw_capture']['path']}")
    print(f"Title: {data['raw_capture']['title']}")
    print(f"Sensitivity: {data['raw_capture']['sensitivity']}")
    print()
    print("## Memory Candidates")
    for candidate in data["memory_candidates"]:
        print(f"- [{candidate['kind']}] {candidate['text']}")
        if candidate["target_hint"]:
            print(f"  Target hint: {candidate['target_hint']}")
        evidence = candidate["evidence"]
        source_detail = evidence["source_path"]
        if evidence["section"]:
            source_detail += f"#{evidence['section']}"
        if evidence["line_hint"]:
            source_detail += f":{evidence['line_hint']}"
        print(f"  Evidence: {source_detail}")
    print()
    print("## Durable Note Patches")
    for patch in data["durable_note_patches"]:
        print(f"- {patch['action']} `{patch['target']}` -> {patch['section']}")
        print(f"  {patch['content']}")
    print()
    print("## Link Patches")
    for patch in data["link_patches"]:
        print(f"- {patch['action']}: `{patch['source']}` -> `{patch['target']}` ({patch['reason']})")
    print()
    print("## Review Flags")
    for flag in data["review_flags"]:
        print(f"- [{flag['level']}] {flag['message']}")
        if flag["evidence"]:
            print(f"  Evidence: {flag['evidence']}")
