from __future__ import annotations

import argparse
from pathlib import Path

from .capture import capture, search
from .constants import (
    DEFAULT_QUESTION_COUNT,
    DEFAULT_SOURCE_CAPTURE_WORDS,
    DEFAULT_THIN_NOTE_WORDS,
    MAX_QUESTION_BATCH,
)
from .export import export_json
from .export import print_export_preview
from .experience import print_answer_context, print_pulse, print_thread_walk
from .extraction import build_extraction_plan, print_apply_capture_review, print_capture_review, print_extraction_plan
from .init import ensure_vault, init_vault
from .migrations import migrate_app_fields, migrate_relationship_fields, migrate_source_fields
from .questions import (
    QUESTION_REFRESH_MODES,
    list_question_templates,
    print_questions,
    question_domains,
    refresh_questions,
    suggest_question,
)
from .reports import (
    audit,
    confidence_report,
    dedupe_memory,
    enrich_thin_notes,
    find_gaps,
    graph_summary,
    print_validation_report,
    schema_report,
    source_hygiene,
    split_large_notes,
)
from .templates import list_templates, sync_vault_templates, write_template_assets
from .timeline import timeline_export, timeline_report


def parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [tag.strip() for tag in raw.split(",") if tag.strip()]

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Self Atlas vault helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a Self Atlas Markdown life graph vault")
    init_parser.add_argument("--vault", required=True, type=Path)
    init_parser.add_argument("--full", action="store_true", help="Create the larger starter scaffold instead of the minimal core")

    ensure_parser = subparsers.add_parser("ensure", help="Check vault readiness and print setup prompt if missing")
    ensure_parser.add_argument("--vault", type=Path, default=None)
    ensure_parser.add_argument("--yes", action="store_true", help="Initialize the suggested vault without another prompt")
    ensure_parser.add_argument("--full", action="store_true", help="Create the larger starter scaffold when initializing")

    question_parser = subparsers.add_parser("question", help="Print one or more structured question templates")
    question_parser.add_argument("--domain", choices=question_domains(), default=None)
    question_parser.add_argument("--count", type=int, default=DEFAULT_QUESTION_COUNT, help=f"Questions to print, capped at {MAX_QUESTION_BATCH}")
    question_parser.add_argument("--with-examples", action="store_true", dest="with_examples", help="Include optional example answer shapes")

    capture_parser = subparsers.add_parser("capture", help="Create a raw capture note")
    capture_parser.add_argument("--vault", required=True, type=Path)
    capture_parser.add_argument("--title", required=True)
    capture_parser.add_argument("--body", required=True)
    capture_parser.add_argument("--domain", default="identity")
    capture_parser.add_argument("--sensitivity", default="normal")
    capture_parser.add_argument("--tags", default=None, help="Comma-separated tags")

    search_parser = subparsers.add_parser("search", help="Search Markdown notes")
    search_parser.add_argument("--vault", required=True, type=Path)
    search_parser.add_argument("query")

    audit_parser = subparsers.add_parser("audit", help="Report overall vault health without changing files")
    audit_parser.add_argument("--vault", required=True, type=Path)

    pulse_parser = subparsers.add_parser("pulse", help="Show the current graph pulse: threads, questions, captures, gaps, and next moves")
    pulse_parser.add_argument("--vault", required=True, type=Path)
    pulse_parser.add_argument("--include-sensitive", action="store_true", help="Include private, health, financial, and intimate notes in the pulse")
    pulse_parser.add_argument("--max-items", type=int, default=8, help="Maximum rows per pulse section")
    pulse_parser.add_argument("--json", action="store_true", dest="json_output", help="Print pulse as JSON")

    thread_walk_parser = subparsers.add_parser("thread-walk", help="Walk one topic across linked notes without changing files")
    thread_walk_parser.add_argument("--vault", required=True, type=Path)
    thread_walk_parser.add_argument("--query", required=True, help="Project, person, value, taste word, or thread to walk")
    thread_walk_parser.add_argument("--include-sensitive", action="store_true", help="Include private, health, financial, and intimate notes")
    thread_walk_parser.add_argument("--depth", type=int, default=2, help="Link depth to walk from matched notes")
    thread_walk_parser.add_argument("--max-notes", type=int, default=12, help="Maximum notes to include")
    thread_walk_parser.add_argument("--json", action="store_true", dest="json_output", help="Print thread walk as JSON")

    answer_context_parser = subparsers.add_parser("answer-context", help="Return receipt-backed context for answering a query without changing files")
    answer_context_parser.add_argument("--vault", required=True, type=Path)
    answer_context_parser.add_argument("--query", required=True, help="Question or topic to gather receipts for")
    answer_context_parser.add_argument("--include-sensitive", action="store_true", help="Include private, health, financial, and intimate notes")
    answer_context_parser.add_argument("--max-notes", type=int, default=8, help="Maximum matching notes and receipts to include")
    answer_context_parser.add_argument("--json", action="store_true", dest="json_output", help="Print context as JSON")

    find_gaps_parser = subparsers.add_parser("find-gaps", help="Report thin areas, queued questions, and open threads")
    find_gaps_parser.add_argument("--vault", required=True, type=Path)

    enrich_thin_notes_parser = subparsers.add_parser("enrich-thin-notes", help="Generate targeted questions for thin notes without inventing facts")
    enrich_thin_notes_parser.add_argument("--vault", required=True, type=Path)
    enrich_thin_notes_parser.add_argument("--words", type=int, default=DEFAULT_THIN_NOTE_WORDS, help="Notes below this word count are considered thin")
    enrich_thin_notes_parser.add_argument("--limit", type=int, default=12, help="Maximum questions to report or append")
    enrich_thin_notes_parser.add_argument("--apply", action="store_true", help="Append generated questions to 00 System/Question Queue.md")
    enrich_thin_notes_parser.add_argument("--include-system", action="store_true", help="Include 00 System notes in thin-note checks")

    suggest_question_parser = subparsers.add_parser("suggest-question", help="Suggest one graph-aware question without changing files")
    suggest_question_parser.add_argument("--vault", required=True, type=Path)
    suggest_question_parser.add_argument("--domain", choices=question_domains(), default=None, help="Optional domain preference")
    suggest_question_parser.add_argument("--count", type=int, default=DEFAULT_QUESTION_COUNT, help=f"Questions to print, capped at {MAX_QUESTION_BATCH}")
    suggest_question_parser.add_argument("--with-examples", action="store_true", help="Include optional example answer shapes")

    refresh_questions_parser = subparsers.add_parser("refresh-questions", help="Shuffle or regenerate the queued question batch")
    refresh_questions_parser.add_argument("--vault", required=True, type=Path)
    refresh_questions_parser.add_argument("--count", type=int, default=MAX_QUESTION_BATCH, help=f"Questions to select, capped at {MAX_QUESTION_BATCH}")
    refresh_questions_parser.add_argument("--mode", choices=QUESTION_REFRESH_MODES, default="mixed", help="shuffle existing questions, regenerate from templates, or mix both")
    refresh_questions_parser.add_argument("--with-examples", action="store_true", help="Include optional example answer shapes")
    refresh_questions_parser.add_argument("--apply", action="store_true", help="Rewrite 00 System/Question Queue.md. Defaults to preview only.")
    refresh_questions_parser.add_argument("--seed", type=int, default=None, help="Deterministic shuffle seed for repeatable refreshes")

    extract_plan_parser = subparsers.add_parser("extract-plan", help="Build a typed extraction plan for one source capture without changing files")
    extract_plan_parser.add_argument("--vault", required=True, type=Path)
    extract_plan_parser.add_argument("--source", required=True, help="Source note path, with or without .md")
    extract_plan_parser.add_argument("--json", action="store_true", dest="json_output", help="Print the plan as JSON")

    capture_review_parser = subparsers.add_parser("capture-review", help="Review proposed memory writes for one source capture without changing files")
    capture_review_parser.add_argument("--vault", required=True, type=Path)
    capture_review_parser.add_argument("--source", required=True, help="Source note path, with or without .md")
    capture_review_parser.add_argument("--json", action="store_true", dest="json_output", help="Print the review as JSON")

    apply_review_parser = subparsers.add_parser("apply-review", help="Apply an approved capture review to durable notes")
    apply_review_parser.add_argument("--vault", required=True, type=Path)
    apply_review_parser.add_argument("--source", required=True, help="Source note path, with or without .md")
    apply_review_parser.add_argument("--apply", action="store_true", help="Write changes. Defaults to dry-run.")
    apply_review_parser.add_argument("--yes", action="store_true", help="Confirm applying sensitive/private capture material")
    apply_review_parser.add_argument("--backup-dir", type=Path, default=None, help="Backup directory for originals when applying")
    apply_review_parser.add_argument("--json", action="store_true", dest="json_output", help="Print result as JSON")

    validate_links_parser = subparsers.add_parser("validate-links", help="Check wiki links and required frontmatter")
    validate_links_parser.add_argument("--vault", required=True, type=Path)

    confidence_report_parser = subparsers.add_parser("confidence-report", help="Summarize confidence metadata and uncertainty hotspots")
    confidence_report_parser.add_argument("--vault", required=True, type=Path)

    split_large_notes_parser = subparsers.add_parser("split-large-notes", help="Report notes that should probably be split; does not change files")
    split_large_notes_parser.add_argument("--vault", required=True, type=Path)
    split_large_notes_parser.add_argument("--words", type=int, default=1200)
    split_large_notes_parser.add_argument("--headings", type=int, default=7)
    split_large_notes_parser.add_argument("--include-sources", action="store_true", help="Include raw source captures in the report")

    source_hygiene_parser = subparsers.add_parser("source-hygiene", help="Report source capture bloat, extraction gaps, and archive pressure")
    source_hygiene_parser.add_argument("--vault", required=True, type=Path)
    source_hygiene_parser.add_argument("--words", type=int, default=DEFAULT_SOURCE_CAPTURE_WORDS, help="Capture word count considered oversized")
    source_hygiene_parser.add_argument("--max-items", type=int, default=20, help="Maximum rows per report section")
    source_hygiene_parser.add_argument("--stale-days", type=int, default=30, help="Age threshold for unextracted source warnings")

    dedupe_memory_parser = subparsers.add_parser("dedupe-memory", help="Report likely duplicate titles and repeated durable bullets")
    dedupe_memory_parser.add_argument("--vault", required=True, type=Path)
    dedupe_memory_parser.add_argument("--min-words", type=int, default=8)

    graph_summary_parser = subparsers.add_parser("graph-summary", help="Summarize graph counts and link hubs")
    graph_summary_parser.add_argument("--vault", required=True, type=Path)

    timeline_report_parser = subparsers.add_parser("timeline-report", help="Summarize life timeline items, periods, and threads")
    timeline_report_parser.add_argument("--vault", required=True, type=Path)
    timeline_report_parser.add_argument("--max-items", type=int, default=40, help="Maximum timeline items to print")
    timeline_report_parser.add_argument("--include-sensitive", action="store_true", help="Include private, health, financial, and intimate notes. Defaults to excluded.")
    timeline_report_parser.add_argument("--exclude-sensitive", action="store_true", help="Deprecated compatibility flag; sensitive notes are excluded by default.")

    timeline_export_parser = subparsers.add_parser("timeline-export", help="Export an app-ready life timeline JSON snapshot")
    timeline_export_parser.add_argument("--vault", required=True, type=Path)
    timeline_export_parser.add_argument("--out", type=Path, default=None, help="Optional output file. Defaults to stdout.")
    timeline_export_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    timeline_export_parser.add_argument("--include-sensitive", action="store_true", help="Include private, health, financial, and intimate notes. Defaults to excluded.")
    timeline_export_parser.add_argument("--exclude-sensitive", action="store_true", help="Deprecated compatibility flag; sensitive notes are excluded by default.")

    list_question_templates_parser = subparsers.add_parser("list-question-templates", help="List structured question templates")
    list_question_templates_parser.add_argument("--json", action="store_true", dest="json_output", help="Print templates as JSON")

    subparsers.add_parser("list-templates", help="List available starter templates")

    sync_templates_parser = subparsers.add_parser("sync-templates", help="Copy starter templates into an initialized vault")
    sync_templates_parser.add_argument("--vault", required=True, type=Path)
    sync_templates_parser.add_argument("--overwrite", action="store_true", help="Refresh existing template files too")

    write_template_assets_parser = subparsers.add_parser("write-template-assets", help="Write plugin asset templates from the template registry")
    write_template_assets_parser.add_argument("--dir", required=True, type=Path)
    write_template_assets_parser.add_argument("--overwrite", action="store_true", help="Refresh existing template files too")

    migrate_app_fields_parser = subparsers.add_parser("migrate-app-fields", help="Add deterministic id and schema_version frontmatter safely")
    migrate_app_fields_parser.add_argument("--vault", required=True, type=Path)
    migrate_app_fields_parser.add_argument("--apply", action="store_true", help="Write changes. Defaults to dry-run.")
    migrate_app_fields_parser.add_argument("--backup-dir", type=Path, default=None, help="Backup directory for originals when applying")
    migrate_app_fields_parser.add_argument("--include-templates", action="store_true", help="Also add fields to template notes")
    migrate_app_fields_parser.add_argument("--fix-existing", action="store_true", help="Replace conflicting existing id/schema_version values with deterministic values")

    migrate_source_fields_parser = subparsers.add_parser("migrate-source-fields", help="Derive sources frontmatter from existing source links")
    migrate_source_fields_parser.add_argument("--vault", required=True, type=Path)
    migrate_source_fields_parser.add_argument("--apply", action="store_true", help="Write changes. Defaults to dry-run.")
    migrate_source_fields_parser.add_argument("--backup-dir", type=Path, default=None, help="Backup directory for originals when applying")
    migrate_source_fields_parser.add_argument("--include-empty", action="store_true", help="Add sources: [] to eligible notes without source links")
    migrate_source_fields_parser.add_argument("--include-system", action="store_true", help="Also update 00 System notes")
    migrate_source_fields_parser.add_argument("--include-sources", action="store_true", help="Also update 90 Sources notes")

    migrate_relationship_fields_parser = subparsers.add_parser("migrate-relationship-fields", help="Add typed relationship frontmatter to person notes")
    migrate_relationship_fields_parser.add_argument("--vault", required=True, type=Path)
    migrate_relationship_fields_parser.add_argument("--apply", action="store_true", help="Write changes. Defaults to dry-run.")
    migrate_relationship_fields_parser.add_argument("--backup-dir", type=Path, default=None, help="Backup directory for originals when applying")

    schema_report_parser = subparsers.add_parser("schema-report", help="Report app-backend schema readiness without changing files")
    schema_report_parser.add_argument("--vault", required=True, type=Path)

    export_json_parser = subparsers.add_parser("export-json", help="Export an app-ready JSON graph snapshot")
    export_json_parser.add_argument("--vault", required=True, type=Path)
    export_json_parser.add_argument("--out", type=Path, default=None, help="Optional output file. Defaults to stdout.")
    export_json_parser.add_argument("--include-body", action="store_true", help="Include full note body text. Defaults to omitted.")
    export_json_parser.add_argument("--include-sensitive", action="store_true", help="Include private, health, financial, and intimate notes. Defaults to excluded.")
    export_json_parser.add_argument("--exclude-body", action="store_true", help="Deprecated compatibility flag; body text is omitted by default.")
    export_json_parser.add_argument("--exclude-sensitive", action="store_true", help="Deprecated compatibility flag; sensitive notes are excluded by default.")
    export_json_parser.add_argument("--include-templates", action="store_true", help="Include template notes in the graph export")
    export_json_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    export_preview_parser = subparsers.add_parser("export-preview", help="Preview graph export privacy shape without writing files")
    export_preview_parser.add_argument("--vault", required=True, type=Path)
    export_preview_parser.add_argument("--include-body", action="store_true", help="Preview including full note body text")
    export_preview_parser.add_argument("--include-sensitive", action="store_true", help="Preview including private, health, financial, and intimate notes")
    export_preview_parser.add_argument("--include-templates", action="store_true", help="Preview including template notes")
    export_preview_parser.add_argument("--json", action="store_true", dest="json_output", help="Print preview as JSON")

    args = parser.parse_args(argv)

    if args.command == "init":
        init_vault(args.vault, args.full)
    elif args.command == "ensure":
        return ensure_vault(args.vault, args.yes, args.full)
    elif args.command == "question":
        print_questions(args.domain, args.count, args.with_examples)
    elif args.command == "capture":
        capture(args.vault, args.title, args.body, args.domain, args.sensitivity, parse_tags(args.tags))
    elif args.command == "search":
        search(args.vault, args.query)
    elif args.command == "audit":
        audit(args.vault)
    elif args.command == "pulse":
        print_pulse(args.vault, args.include_sensitive, args.max_items, args.json_output)
    elif args.command == "thread-walk":
        print_thread_walk(args.vault, args.query, args.include_sensitive, max(0, args.depth), max(1, args.max_notes), args.json_output)
    elif args.command == "answer-context":
        print_answer_context(args.vault, args.query, args.include_sensitive, max(1, args.max_notes), args.json_output)
    elif args.command == "find-gaps":
        find_gaps(args.vault)
    elif args.command == "enrich-thin-notes":
        enrich_thin_notes(args.vault, args.words, args.limit, args.apply, args.include_system)
    elif args.command == "suggest-question":
        suggest_question(args.vault, args.domain, args.count, args.with_examples)
    elif args.command == "refresh-questions":
        refresh_questions(args.vault, args.count, args.mode, args.with_examples, args.apply, args.seed)
    elif args.command == "extract-plan":
        print_extraction_plan(build_extraction_plan(args.vault, args.source), args.json_output)
    elif args.command == "capture-review":
        print_capture_review(build_extraction_plan(args.vault, args.source), args.json_output)
    elif args.command == "apply-review":
        print_apply_capture_review(args.vault, args.source, args.apply, args.yes, args.backup_dir, args.json_output)
    elif args.command == "validate-links":
        print_validation_report(args.vault)
    elif args.command == "confidence-report":
        confidence_report(args.vault)
    elif args.command == "split-large-notes":
        split_large_notes(args.vault, args.words, args.headings, args.include_sources)
    elif args.command == "source-hygiene":
        source_hygiene(args.vault, args.words, args.max_items, args.stale_days)
    elif args.command == "dedupe-memory":
        dedupe_memory(args.vault, args.min_words)
    elif args.command == "graph-summary":
        graph_summary(args.vault)
    elif args.command == "timeline-report":
        exclude_sensitive = args.exclude_sensitive or not args.include_sensitive
        timeline_report(args.vault, args.max_items, exclude_sensitive)
    elif args.command == "timeline-export":
        exclude_sensitive = args.exclude_sensitive or not args.include_sensitive
        timeline_export(args.vault, args.out, args.pretty, exclude_sensitive)
    elif args.command == "list-question-templates":
        list_question_templates(args.json_output)
    elif args.command == "list-templates":
        list_templates()
    elif args.command == "sync-templates":
        sync_vault_templates(args.vault, args.overwrite)
    elif args.command == "write-template-assets":
        write_template_assets(args.dir, args.overwrite)
    elif args.command == "migrate-app-fields":
        migrate_app_fields(args.vault, args.apply, args.backup_dir, args.include_templates, args.fix_existing)
    elif args.command == "migrate-source-fields":
        migrate_source_fields(args.vault, args.apply, args.backup_dir, args.include_empty, args.include_system, args.include_sources)
    elif args.command == "migrate-relationship-fields":
        migrate_relationship_fields(args.vault, args.apply, args.backup_dir)
    elif args.command == "schema-report":
        schema_report(args.vault)
    elif args.command == "export-json":
        exclude_body = args.exclude_body or not args.include_body
        exclude_sensitive = args.exclude_sensitive or not args.include_sensitive
        export_json(args.vault, args.out, exclude_body, exclude_sensitive, args.pretty, args.include_templates)
    elif args.command == "export-preview":
        print_export_preview(args.vault, args.include_body, args.include_sensitive, args.include_templates, args.json_output)
    return 0
