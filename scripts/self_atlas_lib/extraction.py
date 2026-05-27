from __future__ import annotations

import json
import re
import datetime as dt
from collections import Counter
from pathlib import Path

from .constants import DOMAIN_CONFIG, WIKI_LINK_RE
from .models import DurableNotePatch, ExtractionPlan, LinkPatch, MemoryCandidate, RawCapture, ReviewFlag, SourceEvidence
from .questions import has_any_keyword, infer_question_domain
from .vault import (
    append_under_heading,
    apply_source_fields_to_text,
    as_list,
    as_string,
    backup_note,
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

SENSITIVE_LEVELS = {"private", "health", "financial", "intimate"}


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
        if target.startswith("75 Things/"):
            return "thing"
        if target.startswith("75 Credentials/"):
            return "credential_reference"
        if target.startswith("80 Reflections/"):
            return "pattern"
    if has_any_keyword(
        text,
        (
            "credential",
            "credentials",
            "account",
            "login",
            "password",
            "api key",
            "token",
            "recovery code",
            "license",
            "serial",
            "transfer id",
        ),
    ):
        return "credential_reference"
    if has_any_keyword(
        text,
        (
            "address",
            "home address",
            "phone",
            "phone number",
            "email",
            "contact",
            "emergency contact",
            "handle",
        ),
    ):
        return "person"
    if has_any_keyword(
        text,
        (
            "bought",
            "buy",
            "purchased",
            "ordered",
            "own",
            "owned",
            "gear",
            "device",
            "keyboard",
            "controller",
            "instrument",
            "plugin",
            "hardware",
            "wishlist",
            "wanting",
            "want to buy",
            "thinking of buying",
            "receipt",
        ),
    ):
        return "thing"
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
        ),
    ):
        return "work"
    if has_any_keyword(text, ("project", "prototype", "app", "product", "startup", "tool", "platform")):
        return "project"
    if has_any_keyword(text, ("taste", "reject", "generic", "soulless", "music", "design", "motion", "ui")):
        return "preference"
    if has_any_keyword(text, ("health", "heart", "pain", "sleep", "energy", "body")):
        return "health_observation"
    if has_any_keyword(text, ("visa", "immigration", "relocation", "appointment", "document", "deadline", "travel")):
        return "logistics_thread"
    if "?" in text:
        return "question"
    if has_any_keyword(text, ("need", "fear", "pattern", "tension", "structure", "pressure")):
        return "pattern"
    if has_any_keyword(text, ("girlfriend", "boyfriend", "partner", "spouse", "romantic")):
        return "relationship_love"
    if has_any_keyword(text, ("colleague", "coworker", "collaborator", "team")):
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
        "thing": "Status",
        "credential_reference": "Access Context",
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
        "thing": "75 Things/Things",
        "credential_reference": "75 Credentials/Credentials",
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

    if raw_capture.sensitivity in SENSITIVE_LEVELS:
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

def build_capture_review(plan: ExtractionPlan) -> dict[str, object]:
    candidates = plan.memory_candidates
    patches = plan.durable_note_patches
    targetless = [candidate for candidate in candidates if not candidate.target_hint]
    questions = [candidate for candidate in candidates if candidate.kind == "question"]
    kind_counts = Counter(candidate.kind for candidate in candidates)
    patch_targets = Counter(patch.target for patch in patches)
    sensitive = plan.raw_capture.sensitivity in {"private", "health", "financial", "intimate"}
    missing_raw = any(flag.message.startswith("Source note has no") for flag in plan.review_flags)
    missing_candidates = any("No `Extracted Notes`" in flag.message for flag in plan.review_flags)

    if missing_raw or missing_candidates:
        status = "needs_source_work"
    elif targetless:
        status = "needs_target_decisions"
    elif sensitive:
        status = "needs_consent"
    else:
        status = "ready_for_review"

    consent_notes = []
    if sensitive:
        consent_notes.append(f"Source is `{plan.raw_capture.sensitivity}`; ask before applying patches.")
    if questions:
        consent_notes.append("Follow-up questions should be queued only if the user wants this thread reopened.")
    if targetless:
        consent_notes.append("Some candidates need a durable-note target before anything should be written.")

    return {
        "source": {
            "path": plan.raw_capture.path,
            "title": plan.raw_capture.title,
            "sensitivity": plan.raw_capture.sensitivity,
            "confidence": plan.raw_capture.confidence,
            "raw_words": len(plan.raw_capture.raw_text.split()),
        },
        "status": status,
        "counts": {
            "memory_candidates": len(candidates),
            "durable_note_patches": len(patches),
            "link_patches": len(plan.link_patches),
            "review_flags": len(plan.review_flags),
            "targetless_candidates": len(targetless),
            "follow_up_questions": len(questions),
        },
        "candidate_kinds": dict(sorted(kind_counts.items())),
        "patch_targets": dict(sorted(patch_targets.items())),
        "ready_patches": [
            {
                "target": patch.target,
                "section": patch.section,
                "content": patch.content,
                "evidence": patch.evidence.to_json(),
            }
            for patch in patches
        ],
        "needs_target": [
            {
                "kind": candidate.kind,
                "text": candidate.text,
                "evidence": candidate.evidence.to_json(),
            }
            for candidate in targetless
        ],
        "review_flags": [flag.to_json() for flag in plan.review_flags],
        "consent_notes": consent_notes,
    }

def print_capture_review(plan: ExtractionPlan, json_output: bool) -> None:
    review = build_capture_review(plan)
    if json_output:
        print(json.dumps(review, ensure_ascii=False, indent=2))
        return

    print("# Capture Review")
    print()
    print("Mode: review-only. No files were changed.")
    print(f"Source: {review['source']['path']}")
    print(f"Title: {review['source']['title']}")
    print(f"Sensitivity: {review['source']['sensitivity']}")
    print(f"Confidence: {review['source']['confidence']}")
    print(f"Status: {review['status']}")
    print()
    print("## Counts")
    for key, value in review["counts"].items():
        print(f"- {key}: {value}")
    print()
    print("## Candidate Kinds")
    for key, value in review["candidate_kinds"].items():
        print(f"- {key}: {value}")
    print()
    print("## Proposed Durable Patches")
    if review["ready_patches"]:
        for patch in review["ready_patches"]:
            evidence = patch["evidence"]
            source = evidence["source_path"]
            if evidence["section"]:
                source += f"#{evidence['section']}"
            if evidence["line_hint"]:
                source += f":{evidence['line_hint']}"
            print(f"- `{patch['target']}` -> {patch['section']}")
            print(f"  {patch['content']}")
            print(f"  Evidence: {source}")
    else:
        print("- None")
    print()
    print("## Needs Target Decision")
    if review["needs_target"]:
        for item in review["needs_target"]:
            print(f"- [{item['kind']}] {item['text']}")
    else:
        print("- None")
    print()
    print("## Consent And Review Notes")
    if review["consent_notes"]:
        for item in review["consent_notes"]:
            print(f"- {item}")
    else:
        print("- No sensitive write blockers. Still review it, because autopilot memory is how dumb little myths get born.")
    if review["review_flags"]:
        print()
        print("## Review Flags")
        for flag in review["review_flags"]:
            print(f"- [{flag['level']}] {flag['message']}")
            if flag["evidence"]:
                print(f"  Evidence: {flag['evidence']}")

def target_note_path(vault: Path, target: str) -> Path:
    target = target.removesuffix(".md")
    return vault / f"{target}.md"

def backup_once(vault: Path, path: Path, backup_root: Path, backed_up: set[Path]) -> None:
    resolved = path.resolve()
    if resolved in backed_up:
        return
    backup_note(vault, path, backup_root)
    backed_up.add(resolved)

def apply_capture_review(
    vault: Path,
    source: str,
    apply: bool,
    yes: bool,
    backup_dir: Path | None = None,
) -> dict[str, object]:
    vault = require_vault(vault)
    plan = build_extraction_plan(vault, source)
    review = build_capture_review(plan)
    sensitive = plan.raw_capture.sensitivity in SENSITIVE_LEVELS
    if apply and sensitive and not yes:
        raise SystemExit(
            f"Source sensitivity is `{plan.raw_capture.sensitivity}`. "
            "Review the plan, then re-run with --apply --yes if you want these writes."
        )

    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = (backup_dir or (vault.parent / f"{vault.name}-Backups" / f"apply-review-{timestamp}")).expanduser().resolve()
    changed_files: set[str] = set()
    backed_up: set[Path] = set()
    appended_patches = 0
    skipped_existing_patches = 0
    missing_targets = []
    source_field_updates = 0
    source_field_skips = 0
    source_field_errors = []

    for patch in plan.durable_note_patches:
        path = target_note_path(vault, patch.target)
        if not path.exists():
            missing_targets.append(patch.target)
            continue
        if not apply:
            if patch.content in path.read_text(encoding="utf-8"):
                skipped_existing_patches += 1
            else:
                appended_patches += 1
            continue
        before = path.read_text(encoding="utf-8")
        backup_once(vault, path, backup_root, backed_up)
        did_append = append_under_heading(path, patch.section, patch.content)
        if did_append:
            appended_patches += 1
            changed_files.add(path.relative_to(vault).as_posix())
        else:
            skipped_existing_patches += 1
        if path.read_text(encoding="utf-8") == before and did_append:
            skipped_existing_patches += 1

    for link_patch in plan.link_patches:
        if link_patch.action != "ensure_source_frontmatter":
            continue
        path = target_note_path(vault, link_patch.source)
        if not path.exists():
            missing_targets.append(link_patch.source)
            continue
        text = path.read_text(encoding="utf-8")
        updated, did_change, error = apply_source_fields_to_text(text, [link_patch.target])
        if error:
            source_field_errors.append((link_patch.source, error))
            continue
        if not did_change:
            source_field_skips += 1
            continue
        source_field_updates += 1
        if apply:
            backup_once(vault, path, backup_root, backed_up)
            path.write_text(updated, encoding="utf-8")
            changed_files.add(path.relative_to(vault).as_posix())

    source_log_path = vault / "00 System" / "Source Log.md"
    source_log_line = (
        f"- {dt.date.today().isoformat()} - Applied review for "
        f"{wiki_link(plan.raw_capture.path, plan.raw_capture.title)}"
    )
    source_log_changed = False
    if source_log_path.exists():
        if apply:
            backup_once(vault, source_log_path, backup_root, backed_up)
            source_log_changed = append_under_heading(source_log_path, "Captures", source_log_line)
            if source_log_changed:
                changed_files.add(source_log_path.relative_to(vault).as_posix())
        else:
            source_log_changed = source_log_line not in source_log_path.read_text(encoding="utf-8")

    return {
        "source": review["source"],
        "status": review["status"],
        "mode": "apply" if apply else "dry-run",
        "sensitive": sensitive,
        "backup": str(backup_root) if apply and changed_files else None,
        "counts": {
            "patches_to_append" if not apply else "patches_appended": appended_patches,
            "patches_already_present": skipped_existing_patches,
            "source_fields_to_update" if not apply else "source_fields_updated": source_field_updates,
            "source_fields_already_present": source_field_skips,
            "missing_targets": len(set(missing_targets)),
            "source_field_errors": len(source_field_errors),
            "source_log_to_update" if not apply else "source_log_updated": 1 if source_log_changed else 0,
            "changed_files": len(changed_files),
        },
        "changed_files": sorted(changed_files),
        "missing_targets": sorted(set(missing_targets)),
        "source_field_errors": [
            {"target": target, "error": error}
            for target, error in source_field_errors
        ],
        "consent_notes": review["consent_notes"],
    }

def print_apply_capture_review(
    vault: Path,
    source: str,
    apply: bool,
    yes: bool,
    backup_dir: Path | None,
    json_output: bool,
) -> None:
    result = apply_capture_review(vault, source, apply, yes, backup_dir)
    if json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("# Apply Review")
    print()
    print(f"Mode: {result['mode']}")
    print(f"Source: {result['source']['path']}")
    print(f"Sensitivity: {result['source']['sensitivity']}")
    if result["backup"]:
        print(f"Backup: {result['backup']}")
    print()
    print("## Counts")
    for key, value in result["counts"].items():
        print(f"- {key}: {value}")
    print()
    print("## Changed Files")
    for path in result["changed_files"] or ["None"]:
        print(f"- {path}")
    if result["missing_targets"]:
        print()
        print("## Missing Targets")
        for target in result["missing_targets"]:
            print(f"- {target}")
    if result["source_field_errors"]:
        print()
        print("## Source Field Errors")
        for item in result["source_field_errors"]:
            print(f"- {item['target']}: {item['error']}")
    if result["consent_notes"] and not apply:
        print()
        print("## Consent Notes")
        for item in result["consent_notes"]:
            print(f"- {item}")
    if not apply:
        print()
        print("Dry run only. Re-run with --apply, and add --yes for sensitive sources.")
