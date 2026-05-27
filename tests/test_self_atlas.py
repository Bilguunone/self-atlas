from __future__ import annotations

import json
import contextlib
import io
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from public_release_check import scan_files
from self_atlas_lib.export import build_export_graph, build_export_preview
from self_atlas_lib.experience import build_answer_context, build_pulse, build_thread_walk
from self_atlas_lib.extraction import apply_capture_review, build_capture_review, build_extraction_plan, infer_candidate_kind
from self_atlas_lib.insight import (
    build_artifact_import,
    build_belief_versioning,
    build_contradictions,
    build_decision_council,
    build_decision_replay,
    build_future_self,
    build_life_lenses,
    build_open_loop_radar,
    build_proof_engine,
    build_share_capsule,
    build_taste_autopilot,
    build_taste_genome,
    build_time_travel,
)
from self_atlas_lib.init import init_vault
from self_atlas_lib.questions import build_question_refresh, infer_question_domain, question_templates_for_domain, refresh_questions
from self_atlas_lib.templates import template_files
from self_atlas_lib.timeline import build_timeline
from self_atlas_lib.vault import extract_section_bullets, parse_frontmatter_text
from self_atlas_lib.cli import main as cli_main


def note(
    note_type: str,
    title: str,
    body: str,
    *,
    sensitivity: str = "normal",
    confidence: str = "confirmed",
    tags: tuple[str, ...] = (),
    links: tuple[str, ...] = (),
    sources: tuple[str, ...] = (),
    extra_frontmatter: tuple[str, ...] = (),
) -> str:
    tag_lines = "\n".join(f"  - {tag}" for tag in tags) if tags else "  - self-atlas/test"
    link_lines = "\n".join(f'  - "{link}"' for link in links)
    source_lines = "\n".join(f'  - "{source}"' for source in sources)
    frontmatter = [
        "---",
        f"id: note:{title.lower().replace(' ', '-')}",
        "schema_version: 1",
        f"type: {note_type}",
        *extra_frontmatter,
        "status: active",
        f"sensitivity: {sensitivity}",
        f"confidence: {confidence}",
        "created: 2026-05-21",
        "updated: 2026-05-21",
        "aliases: []",
        "tags:",
        tag_lines,
        "links:" if links else "links: []",
        link_lines,
        "sources:" if sources else "sources: []",
        source_lines,
        "---",
        "",
        f"# {title}",
        "",
        body.strip(),
        "",
    ]
    return "\n".join(line for line in frontmatter if line != "") + "\n"


def write_note(vault: Path, relative: str, content: str) -> None:
    path = vault / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class SelfAtlasTests(unittest.TestCase):
    def make_vault(self) -> tempfile.TemporaryDirectory[str]:
        tmp = tempfile.TemporaryDirectory()
        vault = Path(tmp.name)
        write_note(
            vault,
            "00 System/Home.md",
            note("index", "Self Atlas", "## Home\n\n- [[30 Work/Public Project]]"),
        )
        return tmp

    def test_safe_export_omits_edges_links_sources_frontmatter_and_body_to_excluded_notes(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "30 Work/Public Project.md",
                note(
                    "project",
                    "Public Project",
                    "## What We Know\n\n- Public note points to [[25 Love/River]] and [[90 Sources/Captures/private-source]].",
                    links=("[[25 Love/River]]", "[[90 Sources/Captures/private-source]]"),
                    sources=("90 Sources/Captures/private-source",),
                ),
            )
            write_note(
                vault,
                "25 Love/River.md",
                note(
                    "person",
                    "River",
                    "## What We Know\n\n- Private relationship note.",
                    sensitivity="intimate",
                    tags=("self-atlas/person", "self-atlas/love"),
                    extra_frontmatter=(
                        "relationship_kind: love",
                        "relationship_context: romantic",
                    ),
                ),
            )
            write_note(
                vault,
                "90 Sources/Captures/private-source.md",
                note("source", "private-source", "## Raw Capture\n\nprivate", sensitivity="private"),
            )
            write_note(
                vault,
                "00 System/Templates/person.md",
                note("person", "Person Template", "## Snapshot\n\nTemplate", tags=("self-atlas/person",)),
            )

            data = build_export_graph(vault, include_body=True, exclude_sensitive=True)
            payload = json.dumps(data)

            self.assertNotIn("River", payload)
            self.assertNotIn("private-source", payload)
            self.assertEqual(data["counts"]["template_nodes"], 0)
            self.assertEqual(data["counts"]["relationship_nodes"], 0)
            self.assertEqual(data["counts"]["relationship_edges"], 0)
            self.assertGreater(data["counts"]["omitted_edges"], 0)
            self.assertEqual(data["vault"], {"name": vault.name})
            self.assertTrue(all(node["body"] is None for node in data["nodes"]))
            self.assertFalse([edge for edge in data["edges"] if edge["to"] is None and not edge["missing"]])

    def test_init_vault_minimal_core_has_app_fields_without_templates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            vault = Path(tmp_name)

            with contextlib.redirect_stdout(io.StringIO()):
                init_vault(vault)

            core_notes = (
                "00 System/Home.md",
                "00 System/Graph Rules.md",
                "00 System/Question Queue.md",
                "00 System/Source Log.md",
                "00 System/Open Threads.md",
            )
            for relative in core_notes:
                frontmatter, _ = parse_frontmatter_text((vault / relative).read_text(encoding="utf-8"))
                self.assertTrue(frontmatter.get("id"), relative)
                self.assertEqual(frontmatter.get("schema_version"), "1")

            self.assertFalse(list((vault / "00 System" / "Templates").glob("*.md")))

    def test_default_export_excludes_templates_but_can_include_them_explicitly(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "00 System/Templates/person.md",
                note("person", "Person Template", "## Snapshot\n\nTemplate", tags=("self-atlas/person",)),
            )

            default_data = build_export_graph(vault, include_body=False, exclude_sensitive=False)
            debug_data = build_export_graph(vault, include_body=False, exclude_sensitive=False, include_templates=True)

            self.assertEqual(default_data["counts"]["template_nodes"], 0)
            self.assertEqual(default_data["counts"]["excluded_templates"], 1)
            self.assertEqual(debug_data["counts"]["template_nodes"], 1)

    def test_thing_template_tracks_owned_bought_and_wanted_items(self) -> None:
        files = template_files()
        thing_template = files["00 System/Templates/thing.md"]
        source_template = files["00 System/Templates/source-capture.md"]
        asset_template = (PLUGIN_ROOT / "assets/templates/thing.md").read_text(encoding="utf-8")

        self.assertEqual(asset_template, thing_template)
        self.assertIn("type: thing", thing_template)
        self.assertIn("## Status", thing_template)
        self.assertIn("- State: bought | own | want | considering | borrowed | sold | returned", thing_template)
        self.assertIn("## Taste Signal", thing_template)
        self.assertIn("## Wanting Notes", thing_template)
        self.assertIn("- Things bought, owned, or wanted:", source_template)
        self.assertIn("- Contact details:", source_template)
        self.assertIn("- Credential or account logistics:", source_template)
        self.assertIn("type: thing", asset_template)

    def test_private_contact_and_credential_templates_exist(self) -> None:
        files = template_files()
        person_template = files["00 System/Templates/person.md"]
        credential_template = files["00 System/Templates/credential-reference.md"]
        credential_asset = (PLUGIN_ROOT / "assets/templates/credential-reference.md").read_text(encoding="utf-8")

        self.assertIn("## Contact And Logistics", person_template)
        self.assertIn("- Phone:", person_template)
        self.assertIn("- Address:", person_template)
        self.assertEqual(credential_asset, credential_template)
        self.assertIn("type: credential_reference", credential_template)
        self.assertIn("## Access Context", credential_template)
        self.assertIn("- Where the secret lives:", credential_template)
        self.assertIn("## Do Not Store Here", credential_template)

    def test_things_question_and_extraction_routing(self) -> None:
        self.assertEqual(infer_question_domain("What did I buy and what gear am I wanting next?"), "things")
        self.assertEqual(infer_candidate_kind("Bought a small MIDI controller for music workflow."), "thing")
        self.assertTrue(question_templates_for_domain("things"))

    def test_contact_and_credentials_routing(self) -> None:
        self.assertEqual(infer_question_domain("The account login uses this email."), "credentials")
        self.assertEqual(infer_question_domain("Their phone number and home address changed."), "person")
        self.assertEqual(infer_candidate_kind("The account recovery route uses a login email."), "credential_reference")
        self.assertEqual(infer_candidate_kind("Their phone number changed."), "person")

    def test_extraction_reads_legacy_headings_and_preserves_uncertain_confidence(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "90 Sources/Captures/uncertain-love.md",
                note(
                    "source",
                    "Uncertain Love",
                    textwrap.dedent(
                        """
                        ## Raw Answer

                        Maybe River is the central emotional anchor.

                        ## Derived Notes

                        - [[25 Love/River]] might be the central emotional anchor.

                        ## Open Questions

                        - What date made this feel true?
                        """
                    ),
                    confidence="uncertain",
                    sensitivity="private",
                ),
            )

            plan = build_extraction_plan(vault, "90 Sources/Captures/uncertain-love")

            self.assertEqual(plan.memory_candidates[0].kind, "relationship_love")
            self.assertEqual(plan.memory_candidates[0].confidence, "uncertain")
            self.assertEqual(plan.memory_candidates[0].evidence.confidence, "uncertain")
            self.assertEqual(plan.memory_candidates[1].confidence, "uncertain")
            self.assertEqual(plan.durable_note_patches[0].evidence.section, "Raw Answer")
            self.assertEqual(plan.durable_note_patches[1].evidence.section, "Open Questions")

    def test_collaborator_folder_exports_as_collaborator_relationship(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "20 People/Collaborators/Ada.md",
                note("person", "Ada", "## What We Know\n\n- Works with Mira.", tags=("self-atlas/person",)),
            )

            data = build_export_graph(vault, include_body=False, exclude_sensitive=False)
            relationships = {
                node["path"]: node["relationship"]
                for node in data["nodes"]
                if node["relationship"]
            }

            self.assertEqual(relationships["20 People/Collaborators/Ada.md"]["kind"], "collaborator")

    def test_pulse_surfaces_queue_threads_unextracted_sources_and_hides_sensitive_by_default(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "00 System/Open Threads.md",
                note(
                    "question",
                    "Open Threads",
                    "## Active Threads\n\n- Clarify the proof moment for [[30 Work/Public Project]].",
                    sensitivity="private",
                ),
            )
            write_note(
                vault,
                "00 System/Question Queue.md",
                note(
                    "question",
                    "Question Queue",
                    "## Next Questions\n\n- What makes [[30 Work/Public Project]] worth saving?",
                    sensitivity="private",
                ),
            )
            write_note(
                vault,
                "30 Work/Public Project.md",
                note("project", "Public Project", "## What We Know\n\n- It needs a proof moment."),
            )
            write_note(
                vault,
                "25 Love/River.md",
                note("person", "River", "## What We Know\n\n- Private.", sensitivity="intimate"),
            )
            write_note(
                vault,
                "90 Sources/Captures/fresh.md",
                note("source", "fresh", "## Raw Capture\n\nThis source has not been extracted yet."),
            )

            safe_pulse = build_pulse(vault, include_sensitive=False, max_items=5)
            private_pulse = build_pulse(vault, include_sensitive=True, max_items=5)

            self.assertEqual(safe_pulse["counts"]["hidden_sensitive"], 3)
            self.assertEqual(safe_pulse["counts"]["queued_questions"], 0)
            self.assertEqual(safe_pulse["counts"]["open_threads"], 0)
            self.assertEqual(safe_pulse["counts"]["unextracted_sources"], 1)
            self.assertEqual(safe_pulse["unextracted_sources"][0]["path"], "90 Sources/Captures/fresh.md")
            self.assertEqual(private_pulse["counts"]["queued_questions"], 1)
            self.assertEqual(private_pulse["counts"]["open_threads"], 1)

    def test_thread_walk_starts_from_query_and_follows_links(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "30 Work/Public Project.md",
                note(
                    "project",
                    "Public Project",
                    "## What We Know\n\n- The proof moment links to [[50 Taste/Taste Profile]].",
                    links=("[[50 Taste/Taste Profile]]",),
                ),
            )
            write_note(
                vault,
                "50 Taste/Taste Profile.md",
                note("preference", "Taste Profile", "## Evidence\n\n- Warmth, motion, and proof over decorative sludge."),
            )

            walk = build_thread_walk(vault, query="proof", include_sensitive=False, depth=2, max_notes=6)
            paths = {item["path"] for item in walk["items"]}

            self.assertIn("30 Work/Public Project.md", paths)
            self.assertIn("50 Taste/Taste Profile.md", paths)
            self.assertTrue(walk["edges"])

    def test_capture_review_marks_sensitive_source_as_needing_consent(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "90 Sources/Captures/private.md",
                note(
                    "source",
                    "private",
                    textwrap.dedent(
                        """
                        ## Raw Capture

                        River gave Mira feedback after the prototype demo.

                        ## Extracted Notes

                        - [[25 Love/River]] gave Mira feedback after the prototype demo.
                        """
                    ),
                    sensitivity="intimate",
                ),
            )

            review = build_capture_review(build_extraction_plan(vault, "90 Sources/Captures/private"))

            self.assertEqual(review["status"], "needs_consent")
            self.assertEqual(review["counts"]["durable_note_patches"], 1)
            self.assertTrue(review["consent_notes"])

    def test_apply_review_dry_run_consent_gate_and_apply_writes_reviewed_patches(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "30 Work/Public Project.md",
                note("project", "Public Project", "## What We Know\n\n- Existing fact."),
            )
            write_note(
                vault,
                "00 System/Question Queue.md",
                note("question", "Question Queue", "## Next Questions\n\n", sensitivity="private"),
            )
            write_note(
                vault,
                "00 System/Source Log.md",
                note("index", "Source Log", "## Captures\n\n", sensitivity="private"),
            )
            write_note(
                vault,
                "90 Sources/Captures/private.md",
                note(
                    "source",
                    "private",
                    textwrap.dedent(
                        """
                        ## Raw Capture

                        Mira proved the project with one save-worthy export.

                        ## Extracted Notes

                        - [[30 Work/Public Project]] had a proof moment: one save-worthy export.

                        ## Follow-Up Threads

                        - What did the export look like?
                        """
                    ),
                    sensitivity="private",
                ),
            )

            preview = apply_capture_review(vault, "90 Sources/Captures/private", apply=False, yes=False)
            self.assertEqual(preview["counts"]["patches_to_append"], 2)
            with self.assertRaises(SystemExit):
                apply_capture_review(vault, "90 Sources/Captures/private", apply=True, yes=False)

            result = apply_capture_review(vault, "90 Sources/Captures/private", apply=True, yes=True)
            project_text = (vault / "30 Work/Public Project.md").read_text(encoding="utf-8")
            queue_text = (vault / "00 System/Question Queue.md").read_text(encoding="utf-8")
            source_log_text = (vault / "00 System/Source Log.md").read_text(encoding="utf-8")

            self.assertEqual(result["counts"]["patches_appended"], 2)
            self.assertIn("one save-worthy export", project_text)
            self.assertIn("sources:", project_text)
            self.assertIn("90 Sources/Captures/private", project_text)
            self.assertIn("What did the export look like?", queue_text)
            self.assertIn("Applied review", source_log_text)

    def test_answer_context_hides_private_source_receipts_in_safe_mode(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "30 Work/Public Project.md",
                note(
                    "project",
                    "Public Project",
                    "## What We Know\n\n- The proof moment was one export.",
                    sources=("90 Sources/Captures/private-source",),
                ),
            )
            write_note(
                vault,
                "90 Sources/Captures/private-source.md",
                note("source", "private-source", "## Raw Capture\n\nPrivate receipt.", sensitivity="private"),
            )

            safe_context = build_answer_context(vault, "proof export", include_sensitive=False, max_notes=5)
            private_context = build_answer_context(vault, "proof export", include_sensitive=True, max_notes=5)

            self.assertEqual(safe_context["counts"]["source_receipts"], 0)
            self.assertEqual(safe_context["notes"][0]["sources"], [])
            self.assertEqual(private_context["counts"]["source_receipts"], 1)

    def test_export_preview_firewall_reports_hidden_sensitive_and_body_risk(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "25 Love/River.md",
                note("person", "River", "## What We Know\n\n- Private.", sensitivity="intimate"),
            )

            safe_preview = build_export_preview(vault, include_body=False, include_sensitive=False, include_templates=False)
            private_preview = build_export_preview(vault, include_body=True, include_sensitive=True, include_templates=False)

            self.assertEqual(safe_preview["counts"]["hidden_sensitive"], 1)
            self.assertEqual(safe_preview["hidden_sensitive_notes"][0]["path"], "25 Love/River.md")
            self.assertIn("Sensitive notes are included", " ".join(private_preview["danger_flags"]))
            self.assertIn("Full note bodies", " ".join(private_preview["danger_flags"]))

    def test_frontmatter_parser_handles_current_list_shapes(self) -> None:
        frontmatter, _ = parse_frontmatter_text(
            textwrap.dedent(
                """
                ---
                aliases: [one, "two"]
                tags:
                  - self-atlas/person
                  - self-atlas/friend
                sources:
                  - "90 Sources/Captures/example"
                ---

                # Body
                """
            ).lstrip()
        )

        self.assertEqual(frontmatter["aliases"], ["one", "two"])
        self.assertEqual(frontmatter["tags"], ["self-atlas/person", "self-atlas/friend"])
        self.assertEqual(frontmatter["sources"], ["90 Sources/Captures/example"])

    def test_public_release_check_uses_local_privacy_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            (root / ".privacy-patterns").write_text("secret-fixture-term\n", encoding="utf-8")
            (root / "README.md").write_text("This mentions secret-fixture-term.", encoding="utf-8")

            problems = scan_files(root)

            self.assertEqual(len(problems), 1)
            self.assertIn("secret-fixture-term", problems[0])

    def test_timeline_export_builds_items_threads_periods_and_rough_dates(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "70 Timeline/Life Timeline.md",
                note(
                    "index",
                    "Life Timeline",
                    textwrap.dedent(
                        """
                        ## What We Know

                        - In 3rd grade, Mira met [[20 People/Friends/Ari|Ari]] through YouTube and Minecraft.
                        - Around age 18, Mira entered North Studio School to study Visual Communication.
                        - On 2026-06-08, Mira has a visa interview in the city office.
                        """
                    ),
                    tags=("self-atlas/timeline",),
                    links=("[[20 People/Friends/Ari]]",),
                ),
            )
            write_note(
                vault,
                "20 People/Friends/Ari.md",
                note("person", "Ari", "## What We Know\n\n- Friend.", tags=("self-atlas/person", "self-atlas/friend")),
            )

            data = build_timeline(vault)

            self.assertEqual(data["vault"], {"name": vault.name})
            self.assertNotIn(str(vault), json.dumps(data))
            self.assertEqual(data["counts"]["items"], 3)
            self.assertIn("education", {thread["id"] for thread in data["threads"]})
            self.assertIn("immigration", {thread["id"] for thread in data["threads"]})
            self.assertGreaterEqual(data["counts"]["periods"], 1)
            precisions = data["counts"]["date_precision"]
            self.assertEqual(precisions["approximate"], 2)
            self.assertEqual(precisions["exact"], 1)

    def test_timeline_exclude_sensitive_omits_items_that_point_to_hidden_notes(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "70 Timeline/Public Timeline.md",
                note(
                    "index",
                    "Public Timeline",
                    textwrap.dedent(
                        """
                        ## What We Know

                        - In 2026, Mira worked on [[30 Work/Public Project]].
                        - In 2026, Mira met [[25 Love/River]] at a private moment.
                        """
                    ),
                    tags=("self-atlas/timeline",),
                ),
            )
            write_note(vault, "30 Work/Public Project.md", note("project", "Public Project", "## What We Know\n\n- Public."))
            write_note(
                vault,
                "25 Love/River.md",
                note(
                    "person",
                    "River",
                    "## What We Know\n\n- Private.",
                    sensitivity="intimate",
                    tags=("self-atlas/person", "self-atlas/love"),
                ),
            )

            data = build_timeline(vault)
            payload = json.dumps(data)

            self.assertEqual(data["counts"]["items"], 1)
            self.assertNotIn("River", payload)
            self.assertNotIn("25 Love", payload)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                cli_main(["timeline-report", "--vault", str(vault)])
            report = output.getvalue()

            self.assertIn("Public Project", report)
            self.assertNotIn("River", report)
            self.assertNotIn("25 Love", report)

    def test_question_refresh_mixes_existing_queue_with_generated_prompts(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "00 System/Question Queue.md",
                note(
                    "question",
                    "Question Queue",
                    textwrap.dedent(
                        """
                        Use this to park questions worth asking later.

                        ## Next Questions

                        - What exact years did Mira attend North Studio School, work on the archive project, and start at Lumen Labs?
                        - What has the intermittent heart pain felt like: sharp/dull, duration, triggers, frequency, and when it last happened?
                        - What exact sonic world should Mira's artist identity own?
                        - What does River need most from Mira's support as a filmmaker?
                        """
                    ),
                    sensitivity="private",
                    tags=("self-atlas/questions",),
                ),
            )

            result = build_question_refresh(vault, count=6, mode="mixed", seed=7)

            self.assertEqual(len(result.selected), 6)
            self.assertEqual(result.existing_count, 4)
            self.assertGreater(result.generated_count, 0)
            self.assertGreaterEqual(len({candidate.template.domain for candidate in result.selected}), 4)

    def test_question_refresh_apply_rewrites_queue_and_preserves_history(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            queue = vault / "00 System/Question Queue.md"
            write_note(
                vault,
                "00 System/Question Queue.md",
                note(
                    "question",
                    "Question Queue",
                    textwrap.dedent(
                        """
                        Use this to park questions worth asking later.

                        ## Next Questions

                        - What exact years did Mira attend North Studio School and start at Lumen Labs?
                        - Has Mira confirmed the archive appointments by email yet?
                        - What kind of weekly money plan would support the relocation?
                        - What has the intermittent heart pain felt like?
                        """
                    ),
                    sensitivity="private",
                    tags=("self-atlas/questions",),
                ),
            )
            before = queue.read_text(encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                preview = refresh_questions(vault, count=3, mode="regenerate", with_examples=False, apply=False, seed=5)
            self.assertFalse(preview.applied)
            self.assertEqual(queue.read_text(encoding="utf-8"), before)

            with contextlib.redirect_stdout(io.StringIO()):
                applied = refresh_questions(vault, count=3, mode="regenerate", with_examples=False, apply=True, seed=5)

            next_questions = extract_section_bullets(vault, "00 System/Question Queue.md", "Next Questions")
            after = queue.read_text(encoding="utf-8")
            self.assertTrue(applied.applied)
            self.assertEqual(len(next_questions), 3)
            self.assertIn("## Question Refresh History", after)
            self.assertIn("Rotated out:", after)
            self.assertIn("Has Mira confirmed the archive appointments by email yet?", after)

    def test_life_lenses_filters_relationships_and_hides_sensitive_by_default(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "20 People/Friends/Ari.md",
                note(
                    "person",
                    "Ari",
                    "## What We Know\n\n- Ari gives honest feedback.",
                    sensitivity="private",
                    tags=("self-atlas/person", "self-atlas/friend"),
                ),
            )

            safe = build_life_lenses(vault, "relationships", "", include_sensitive=False, max_notes=5)
            private = build_life_lenses(vault, "relationships", "", include_sensitive=True, max_notes=5)

            self.assertEqual(safe["selection"][0]["notes"], [])
            self.assertEqual(private["selection"][0]["notes"][0]["path"], "20 People/Friends/Ari.md")
            self.assertEqual(safe["hidden_sensitive"], 1)

    def test_contradictions_reports_status_and_confidence_review_signals(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "30 Work/Projects/Archived Project.md",
                note(
                    "project",
                    "Archived Project",
                    "## What We Know\n\n- This is no longer active and needs clarification.",
                    confidence="confirmed",
                ),
            )

            data = build_contradictions(vault, query="", lens_id=None, include_sensitive=False, max_items=10)
            kinds = {signal["kind"] for signal in data["signals"]}

            self.assertIn("status-conflict", kinds)
            self.assertIn("confidence-conflict", kinds)

    def test_open_loop_radar_combines_questions_sources_and_contradictions(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "00 System/Question Queue.md",
                note(
                    "question",
                    "Question Queue",
                    "## Next Questions\n\n- What would make [[30 Work/Public Project]] real?",
                ),
            )
            write_note(
                vault,
                "30 Work/Public Project.md",
                note("project", "Public Project", "## What We Know\n\n- It is no longer active."),
            )
            write_note(
                vault,
                "90 Sources/Captures/unextracted.md",
                note("source", "unextracted", "## Raw Capture\n\nEvidence waiting for review."),
            )

            data = build_open_loop_radar(vault, lens_id=None, include_sensitive=False, stale_days=1, max_items=20)
            kinds = {loop["kind"] for loop in data["loops"]}

            self.assertIn("queued-question", kinds)
            self.assertIn("unextracted-source", kinds)
            self.assertIn("contradiction-signal", kinds)

    def test_decision_council_scores_options_from_graph_evidence(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "30 Work/Projects/Lumen Sketch.md",
                note(
                    "project",
                    "Lumen Sketch",
                    "## What We Know\n\n- Export motion is the proof moment.\n- Onboarding copy is a risk.",
                    tags=("self-atlas/project",),
                ),
            )
            write_note(
                vault,
                "50 Taste/Taste Profile.md",
                note(
                    "preference",
                    "Taste Profile",
                    "## Evidence\n\n- Motion and tactile export quality matter more than explanation.",
                    tags=("self-atlas/taste",),
                ),
            )

            data = build_decision_council(
                vault,
                "Should Lumen Sketch focus on export motion or onboarding copy?",
                "Export motion|Onboarding copy",
                include_sensitive=False,
                max_notes=4,
            )

            self.assertIn("Export motion", data["recommendation"])
            self.assertGreater(data["option_scores"]["Export motion"], data["option_scores"]["Onboarding copy"])

    def test_artifact_import_dry_run_and_apply_create_source_capture_only(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            artifact = vault.parent / "artifact.txt"
            artifact.write_text("A tiny artifact about export motion.", encoding="utf-8")
            write_note(vault, "00 System/Source Log.md", note("source", "Source Log", "## Captures\n\n"))

            preview = build_artifact_import(
                vault,
                [str(artifact)],
                domain="taste",
                sensitivity="normal",
                apply=False,
                max_files=10,
                max_chars=40000,
            )
            target = preview["plans"][0]["target_path"]
            self.assertEqual(preview["counts"]["ready"], 1)
            self.assertFalse((vault / target).exists())

            with contextlib.redirect_stdout(io.StringIO()):
                result = build_artifact_import(
                    vault,
                    [str(artifact)],
                    domain="taste",
                    sensitivity="normal",
                    apply=True,
                    max_files=10,
                    max_chars=40000,
                )
            applied = result["applied_paths"][0]
            capture_text = (vault / applied).read_text(encoding="utf-8")
            source_log_text = (vault / "00 System/Source Log.md").read_text(encoding="utf-8")

            self.assertEqual(result["counts"]["imported"], 1)
            self.assertIn("type: source", capture_text)
            self.assertIn("Raw Capture", capture_text)
            self.assertIn("- Things bought, owned, or wanted:", capture_text)
            self.assertIn("- Contact details:", capture_text)
            self.assertIn("- Credential or account logistics:", capture_text)
            self.assertIn(applied.removesuffix(".md"), source_log_text)

    def test_time_travel_groups_timeline_without_absolute_paths(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "70 Timeline/Life Timeline.md",
                note(
                    "index",
                    "Life Timeline",
                    "## What We Know\n\n- In April 2026, Mira started [[30 Work/Public Project]].",
                    tags=("self-atlas/timeline",),
                ),
            )
            write_note(vault, "30 Work/Public Project.md", note("project", "Public Project", "## What We Know\n\n- Public."))

            data = build_time_travel(vault, query="", thread="career", include_sensitive=False, max_items=5)
            payload = json.dumps(data)

            self.assertEqual(data["counts"]["items"], 1)
            self.assertNotIn(str(vault), payload)

    def test_share_capsule_omits_sensitive_notes_hidden_links_and_absolute_paths(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "30 Work/Public Project.md",
                note(
                    "project",
                    "Public Project",
                    "## What We Know\n\n- Public proof moment.\n- Private link to [[25 Love/River]].",
                ),
            )
            write_note(
                vault,
                "25 Love/River.md",
                note("person", "River", "## What We Know\n\n- Private.", sensitivity="intimate"),
            )

            data = build_share_capsule(
                vault,
                "Public Capsule",
                query="proof",
                lens_id=None,
                include_sensitive=False,
                yes=False,
                max_notes=5,
            )
            payload = json.dumps(data)

            self.assertIn("Public Project", payload)
            self.assertNotIn("River", payload)
            self.assertNotIn(str(vault), payload)
            self.assertEqual(data["hidden_sensitive"], 1)

    def test_taste_genome_extracts_principles_anti_taste_and_motion_language(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "50 Taste/Taste Profile.md",
                note(
                    "preference",
                    "Taste Profile",
                    "## Evidence\n\n- Warm tactile motion matters.\n- Generic dashboard sludge is anti-taste.\n- The proof is one export worth saving.",
                    tags=("self-atlas/taste",),
                ),
            )

            data = build_taste_genome(vault, include_sensitive=False, max_items=8)

            self.assertIn("motion", data["motion_words"])
            self.assertTrue(any("Generic" in item or "generic" in item for item in data["anti_taste"]))
            self.assertTrue(any("export" in item for item in data["proof_examples"]))

    def test_proof_engine_finds_receipts_and_hides_private_sources_by_default(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "30 Work/Public Project.md",
                note(
                    "project",
                    "Public Project",
                    "## What We Know\n\n- Export proof is the artifact worth saving.",
                    sources=("90 Sources/Captures/private-proof",),
                ),
            )
            write_note(
                vault,
                "90 Sources/Captures/private-proof.md",
                note("source", "private-proof", "## Raw Capture\n\nThe export proof came from a private capture.", sensitivity="private"),
            )

            safe = build_proof_engine(vault, "export proof", lens_id=None, include_sensitive=False, max_items=5)
            private = build_proof_engine(vault, "export proof", lens_id=None, include_sensitive=True, max_items=5)
            safe_payload = json.dumps(safe)
            private_payload = json.dumps(private)

            self.assertEqual(safe["hidden_sensitive"], 1)
            self.assertEqual(safe["source_receipts"], [])
            self.assertIn("Public Project", safe_payload)
            self.assertNotIn("private-proof", safe_payload)
            self.assertIn("90 Sources/Captures/private-proof.md", private_payload)
            self.assertNotIn(str(vault), private_payload)

    def test_belief_versioning_traces_change_signals_and_hides_sensitive_notes(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "10 Self/Beliefs.md",
                note(
                    "identity",
                    "Beliefs",
                    "## What We Know\n\n- I used to think polish mattered, but now proof matters more.",
                ),
            )
            write_note(
                vault,
                "10 Self/Private Belief.md",
                note("identity", "Private Belief", "## What We Know\n\n- Secret proof belief.", sensitivity="private"),
            )

            data = build_belief_versioning(vault, "proof", lens_id=None, include_sensitive=False, max_items=8)
            payload = json.dumps(data)

            self.assertEqual(data["hidden_sensitive"], 1)
            self.assertEqual(data["counts"]["change_signals"], 1)
            self.assertIn("explicit then-now", payload)
            self.assertNotIn("Secret proof belief", payload)

    def test_taste_autopilot_flags_generic_proofless_artifacts(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "50 Taste/Taste Profile.md",
                note(
                    "preference",
                    "Taste Profile",
                    "## Evidence\n\n- Generic dashboard sludge is anti-taste.\n- Warm tactile export proof matters.",
                    tags=("self-atlas/taste",),
                ),
            )

            data = build_taste_autopilot(vault, "Generic onboarding dashboard copy.", "draft", include_sensitive=False, max_items=8)
            kinds = {item["kind"] for item in data["findings"]}

            self.assertIn("anti-taste-collision", kinds)
            self.assertIn("missing-proof", kinds)
            self.assertEqual(data["recommendation"], "Revise before shipping; the guard found high-severity taste or proof issues.")

    def test_decision_replay_returns_outcome_signals_and_questions(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "30 Work/Public Project.md",
                note(
                    "project",
                    "Public Project",
                    "## What We Know\n\n- The export decision finished with one proof artifact worth saving.",
                ),
            )

            data = build_decision_replay(vault, "export decision", include_sensitive=False, max_items=5)
            payload = json.dumps(data)

            self.assertTrue(data["receipts"])
            self.assertTrue(any("proof artifact" in item for item in data["outcome_signals"]))
            self.assertIn("What did you actually choose?", data["calibration_questions"])
            self.assertNotIn(str(vault), payload)

    def test_future_self_outputs_trajectories_without_absolute_paths(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            write_note(
                vault,
                "30 Work/Public Project.md",
                note("project", "Public Project", "## What We Know\n\n- Export proof makes the project feel real."),
            )
            write_note(
                vault,
                "50 Taste/Taste Profile.md",
                note(
                    "preference",
                    "Taste Profile",
                    "## Evidence\n\n- Generic dashboard sludge is anti-taste.\n- Warm tactile export proof matters.",
                    tags=("self-atlas/taste",),
                ),
            )
            write_note(
                vault,
                "00 System/Question Queue.md",
                note("question", "Question Queue", "## Next Questions\n\n- What proof would make [[30 Work/Public Project]] real?"),
            )

            data = build_future_self(vault, "export proof", horizon="next month", include_sensitive=False, max_items=6)
            names = {item["name"] for item in data["trajectories"]}
            payload = json.dumps(data)

            self.assertIn("Proof-First Path", names)
            self.assertIn("Drift Risk", names)
            self.assertEqual(data["horizon"], "next month")
            self.assertNotIn(str(vault), payload)

    def test_new_insight_commands_have_cli_smoke_paths(self) -> None:
        with self.make_vault() as tmp_name:
            vault = Path(tmp_name)
            artifact = vault.parent / "artifact.md"
            artifact.write_text("# Artifact\n\nExport motion note.", encoding="utf-8")
            write_note(
                vault,
                "30 Work/Public Project.md",
                note("project", "Public Project", "## What We Know\n\n- Export motion proof."),
            )
            write_note(
                vault,
                "70 Timeline/Life Timeline.md",
                note("index", "Life Timeline", "## What We Know\n\n- In 2026, Mira started [[30 Work/Public Project]].", tags=("self-atlas/timeline",)),
            )

            commands = [
                ["life-lenses", "--vault", str(vault), "--json"],
                ["contradictions", "--vault", str(vault), "--json"],
                ["decision-council", "--vault", str(vault), "--question", "Export motion?", "--options", "Yes|No", "--json"],
                ["open-loop-radar", "--vault", str(vault), "--json"],
                ["artifact-import", "--vault", str(vault), "--source", str(artifact), "--json"],
                ["time-travel", "--vault", str(vault), "--json"],
                ["share-capsule", "--vault", str(vault), "--query", "export", "--json"],
                ["taste-genome", "--vault", str(vault), "--json"],
                ["proof-engine", "--vault", str(vault), "--claim", "Export motion proof", "--json"],
                ["belief-versioning", "--vault", str(vault), "--query", "export", "--json"],
                ["taste-autopilot", "--vault", str(vault), "--text", "Generic onboarding dashboard copy.", "--json"],
                ["decision-replay", "--vault", str(vault), "--decision", "Export motion", "--json"],
                ["future-self", "--vault", str(vault), "--query", "export", "--json"],
            ]

            for command in commands:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(cli_main(command), 0, command)
                self.assertTrue(output.getvalue().strip(), command)


if __name__ == "__main__":
    unittest.main()
