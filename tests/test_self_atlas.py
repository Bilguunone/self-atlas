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
from self_atlas_lib.export import build_export_graph
from self_atlas_lib.extraction import build_extraction_plan
from self_atlas_lib.init import init_vault
from self_atlas_lib.questions import build_question_refresh, refresh_questions
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


if __name__ == "__main__":
    unittest.main()
