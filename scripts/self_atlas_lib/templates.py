from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .constants import EXPORT_SCHEMA_VERSION
from .vault import normalized_path, require_vault


@dataclass(frozen=True)
class TemplateSection:
    heading: str
    body: str = ""

    def render(self) -> str:
        if not self.body.strip():
            return f"## {self.heading}"
        return f"## {self.heading}\n\n{self.body.strip()}"

@dataclass(frozen=True)
class TemplateSpec:
    filename: str
    note_type: str
    title: str
    sensitivity: str
    tags: tuple[str, ...]
    sections: tuple[TemplateSection, ...]
    links: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    confidence: str = "confirmed"
    status: str = "active"
    extra_frontmatter: tuple[str, ...] = ()
    relationship_kind: str | None = None
    relationship_context: str | None = None
    emotional_charge: str | None = None
    closeness: str | None = None
    trust: str | None = None
    relationship_phase: str | None = None

    def render(self) -> str:
        lines = [
            "---",
            "id: {{id}}",
            f"schema_version: {EXPORT_SCHEMA_VERSION}",
            f"type: {self.note_type}",
            *self.extra_frontmatter,
            *self.relationship_frontmatter_lines(),
            f"status: {self.status}",
            f"sensitivity: {self.sensitivity}",
            f"confidence: {self.confidence}",
            "created: {{date}}",
            "updated: {{date}}",
            "aliases: []",
            *yaml_list("tags", self.tags),
            *yaml_list("links", self.links, quote=True),
            *yaml_list("sources", self.sources, quote=True),
            "---",
            "",
            f"# {self.title}",
            "",
        ]
        for section in self.sections:
            lines.append(section.render())
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def relationship_frontmatter_lines(self) -> list[str]:
        if not self.relationship_kind:
            return []
        return [
            f"relationship_kind: {self.relationship_kind}",
            f"relationship_context: {self.relationship_context or 'unknown'}",
            f"emotional_charge: {self.emotional_charge or 'unknown'}",
            f"closeness: {self.closeness or 'unknown'}",
            f"trust: {self.trust or 'unknown'}",
            f"relationship_phase: {self.relationship_phase or 'active'}",
        ]

def yaml_list(key: str, values: tuple[str, ...], quote: bool = False) -> list[str]:
    if not values:
        return [f"{key}: []"]
    lines = [f"{key}:"]
    for value in values:
        rendered = f'"{value}"' if quote else value
        lines.append(f"  - {rendered}")
    return lines

def section(heading: str, *lines: str) -> TemplateSection:
    return TemplateSection(heading, "\n".join(lines))

TEMPLATE_LIBRARY = (
    TemplateSpec(
        "source-capture.md",
        "source",
        "{{title}}",
        "normal",
        ("self-atlas/source", "self-atlas/capture"),
        (
            section("Source Context", "- Date: {{date}}", "- Domain:", "- Origin:", "- Sensitivity:"),
            section("Raw Capture"),
            section(
                "Extraction Targets",
                "- People:",
                "- Preferences:",
                "- Values:",
                "- Projects:",
                "- Health context:",
                "- Dates and events:",
                "- Open questions:",
            ),
            section("Extracted Notes"),
            section("Follow-Up Threads"),
        ),
    ),
    TemplateSpec(
        "domain-map.md",
        "index",
        "{{title}}",
        "normal",
        ("self-atlas/map",),
        (
            section("What We Know"),
            section("Key Notes"),
            section("Active Threads"),
            section("Recent Captures"),
            section("Related Maps"),
        ),
        links=("[[00 System/Home]]",),
    ),
    TemplateSpec(
        "concept.md",
        "preference",
        "{{title}}",
        "normal",
        ("self-atlas/concept",),
        (
            section("Meaning"),
            section("Evidence"),
            section("Related"),
        ),
    ),
    TemplateSpec(
        "open-thread.md",
        "question",
        "{{thread}}",
        "private",
        ("self-atlas/open-thread",),
        (
            section("Question"),
            section("Why It Matters"),
            section("Current Evidence"),
            section("Unknowns"),
            section("Next Useful Question"),
        ),
    ),
    TemplateSpec(
        "question.md",
        "question",
        "{{question}}",
        "normal",
        ("self-atlas/question",),
        (
            section("Question"),
            section("Domain"),
            section("Why It Matters"),
            section("Hint"),
            section("Example Answers", "1.", "2.", "3."),
            section("Target Notes"),
            section("Sensitivity Notes"),
        ),
    ),
    TemplateSpec(
        "person.md",
        "person",
        "{{name}}",
        "private",
        ("self-atlas/person",),
        (
            section("Snapshot"),
            section("Quick Facts", "- Birthday:", "- Location:", "- Met:", "- Primary context:"),
            section("Relationship"),
            section("Temperament"),
            section("What They Care About"),
            section("Our Dynamic"),
            section("Memories"),
            section("Care Manual"),
            section("Open Questions"),
        ),
        relationship_kind="person",
        relationship_context="unknown",
    ),
    TemplateSpec(
        "friend.md",
        "person",
        "{{name}}",
        "private",
        ("self-atlas/person", "self-atlas/friend"),
        (
            section("Snapshot"),
            section("Quick Facts", "- Birthday:", "- Location:", "- Met:", "- Primary context:", "- Current closeness:"),
            section("Shared History"),
            section("Personality And Rhythm"),
            section("Our Dynamic"),
            section("Rituals And Inside Jokes"),
            section("Creative Or Project Ties"),
            section("Care Manual"),
            section("Open Questions"),
        ),
        relationship_kind="friend",
        relationship_context="social",
        emotional_charge="warm",
    ),
    TemplateSpec(
        "family-member.md",
        "person",
        "{{name}}",
        "private",
        ("self-atlas/person", "self-atlas/family"),
        (
            section("Snapshot"),
            section("Quick Facts", "- Birthday:", "- Family role:", "- Location:"),
            section("Inherited Patterns"),
            section("Care And Tension"),
            section("Formative Memories"),
            section("What To Keep"),
            section("What To Break"),
            section("Open Questions"),
        ),
        relationship_kind="family",
        relationship_context="family",
    ),
    TemplateSpec(
        "collaborator.md",
        "person",
        "{{name}}",
        "private",
        ("self-atlas/person", "self-atlas/collaborator"),
        (
            section("Snapshot"),
            section("Quick Facts", "- Role:", "- Organization:", "- Projects together:", "- Trust level:"),
            section("Strengths"),
            section("Working Style"),
            section("Friction"),
            section("Project History"),
            section("Future Potential"),
            section("Open Questions"),
        ),
        relationship_kind="collaborator",
        relationship_context="work",
    ),
    TemplateSpec(
        "love-relationship.md",
        "person",
        "{{name}}",
        "intimate",
        ("self-atlas/person", "self-atlas/love"),
        (
            section("Snapshot"),
            section("Relationship Shape"),
            section("Emotional Texture"),
            section("Support Patterns"),
            section("Shared Future"),
            section("Tenderness"),
            section("Tensions"),
            section("Important Dates"),
            section("Open Questions"),
        ),
        relationship_kind="love",
        relationship_context="romantic",
        emotional_charge="high",
        closeness="central",
    ),
    TemplateSpec(
        "project.md",
        "project",
        "{{project}}",
        "normal",
        ("self-atlas/project",),
        (
            section("What It Is"),
            section("Why It Matters"),
            section("Status"),
            section("Emotional Charge"),
            section("Product Direction"),
            section("Proof"),
            section("Blockers"),
            section("People And Links"),
            section("Open Questions"),
        ),
    ),
    TemplateSpec(
        "employer.md",
        "work",
        "{{employer}}",
        "normal",
        ("self-atlas/work", "self-atlas/employer"),
        (
            section("Company Context"),
            section("Role History"),
            section("People"),
            section("Responsibilities"),
            section("Career Relevance"),
            section("Money Context"),
            section("Lessons"),
            section("Open Questions"),
        ),
    ),
    TemplateSpec(
        "role.md",
        "work",
        "{{role}}",
        "normal",
        ("self-atlas/work", "self-atlas/role"),
        (
            section("Official Title"),
            section("Real Role"),
            section("Ownership"),
            section("Daily Work"),
            section("What People Rely On"),
            section("What Feels Alive"),
            section("What Feels Draining"),
            section("Growth Edge"),
        ),
    ),
    TemplateSpec(
        "skill.md",
        "skill",
        "{{skill}}",
        "normal",
        ("self-atlas/work", "self-atlas/skill"),
        (
            section("Skill"),
            section("Evidence"),
            section("Current Level"),
            section("Projects Using It"),
            section("Taste Angle"),
            section("Next Improvement"),
        ),
    ),
    TemplateSpec(
        "career-thread.md",
        "work",
        "{{thread}}",
        "private",
        ("self-atlas/work", "self-atlas/career"),
        (
            section("Direction"),
            section("Evidence"),
            section("Constraints"),
            section("Target Roles"),
            section("Portfolio Proof"),
            section("Next Moves"),
            section("Unresolved Questions"),
        ),
    ),
    TemplateSpec(
        "taste-preference.md",
        "preference",
        "{{preference}}",
        "normal",
        ("self-atlas/taste", "self-atlas/preference"),
        (
            section("Preference"),
            section("Examples"),
            section("Why It Works"),
            section("Emotional Effect"),
            section("Related References"),
        ),
    ),
    TemplateSpec(
        "anti-taste.md",
        "preference",
        "{{anti_taste}}",
        "normal",
        ("self-atlas/taste", "self-atlas/anti-taste"),
        (
            section("Rejected Thing"),
            section("Why It Feels Wrong"),
            section("Examples"),
            section("Replacement Principle"),
            section("Related Notes"),
        ),
    ),
    TemplateSpec(
        "creative-reference.md",
        "creative_reference",
        "{{reference}}",
        "normal",
        ("self-atlas/taste", "self-atlas/reference"),
        (
            section("Reference"),
            section("Medium"),
            section("What Has Pulse"),
            section("Reusable Lesson"),
            section("Linked Projects"),
            section("Linked Taste Notes"),
        ),
    ),
    TemplateSpec(
        "music-identity.md",
        "identity",
        "{{music_identity}}",
        "private",
        ("self-atlas/music", "self-atlas/identity"),
        (
            section("Sound Palette"),
            section("Language Mix"),
            section("Influences"),
            section("Lyrical World"),
            section("Performance Identity"),
            section("Open Experiments"),
        ),
    ),
    TemplateSpec(
        "product-principle.md",
        "preference",
        "{{principle}}",
        "normal",
        ("self-atlas/product", "self-atlas/principle"),
        (
            section("Principle"),
            section("Why It Matters"),
            section("Good Examples"),
            section("Bad Examples"),
            section("Where To Apply It"),
        ),
    ),
    TemplateSpec(
        "identity.md",
        "identity",
        "{{identity}}",
        "private",
        ("self-atlas/identity",),
        (
            section("Self Concept"),
            section("Repeated Signals"),
            section("Contradictions"),
            section("How Others Misread It"),
            section("Source Evidence"),
            section("Open Questions"),
        ),
    ),
    TemplateSpec(
        "value.md",
        "value",
        "{{value}}",
        "private",
        ("self-atlas/value",),
        (
            section("Value"),
            section("Lived Evidence"),
            section("Where It Shows Up"),
            section("What Violates It"),
            section("Related Desires"),
            section("Related Tensions"),
        ),
    ),
    TemplateSpec(
        "desire.md",
        "desire",
        "{{desire}}",
        "private",
        ("self-atlas/desire",),
        (
            section("Desire"),
            section("Emotional Charge"),
            section("Indirect Moves"),
            section("Blockers"),
            section("Concrete Next Expression"),
            section("Open Questions"),
        ),
    ),
    TemplateSpec(
        "fear.md",
        "pattern",
        "{{fear}}",
        "private",
        ("self-atlas/fear", "self-atlas/pattern"),
        (
            section("Fear"),
            section("Triggers"),
            section("Avoidance Behavior"),
            section("Protective Function"),
            section("Counter Evidence"),
            section("Open Question"),
        ),
    ),
    TemplateSpec(
        "pattern.md",
        "pattern",
        "{{pattern}}",
        "private",
        ("self-atlas/pattern",),
        (
            section("Pattern"),
            section("Examples"),
            section("Likely Cause"),
            section("Cost"),
            section("Usefulness"),
            section("What Changes It"),
        ),
    ),
    TemplateSpec(
        "tension.md",
        "pattern",
        "{{tension}}",
        "private",
        ("self-atlas/tension", "self-atlas/pattern"),
        (
            section("Two True Things"),
            section("Evidence For Side A"),
            section("Evidence For Side B"),
            section("Current State"),
            section("Possible Resolution"),
            section("Open Questions"),
        ),
    ),
    TemplateSpec(
        "event.md",
        "event",
        "{{event}}",
        "normal",
        ("self-atlas/timeline", "self-atlas/event"),
        (
            section("Date"),
            section("Before"),
            section("What Happened"),
            section("People Involved"),
            section("Projects Involved"),
            section("Place"),
            section("Emotional Charge"),
            section("Why It Mattered"),
            section("After"),
            section("Source"),
        ),
        extra_frontmatter=(
            "date_start: {{date_start}}",
            "date_end:",
            "date_precision: unknown",
            "life_period:",
            "threads: []",
            "people: []",
            "projects: []",
            "places: []",
            "emotional_charge: unknown",
            "pressure_level: unknown",
            "turning_point: false",
        ),
    ),
    TemplateSpec(
        "timeline-period.md",
        "life_period",
        "{{period}}",
        "normal",
        ("self-atlas/timeline", "self-atlas/period"),
        (
            section("Period"),
            section("Start And End"),
            section("Context"),
            section("Main People"),
            section("Work Themes"),
            section("Life Themes"),
            section("Transition"),
        ),
        extra_frontmatter=(
            "date_start:",
            "date_end:",
            "date_precision: approximate",
            "life_period: {{period_slug}}",
            "threads: []",
            "people: []",
            "projects: []",
            "places: []",
            "emotional_charge: unknown",
            "pressure_level: unknown",
            "turning_point: false",
        ),
    ),
    TemplateSpec(
        "milestone.md",
        "milestone",
        "{{milestone}}",
        "normal",
        ("self-atlas/timeline", "self-atlas/milestone"),
        (
            section("Milestone"),
            section("Proof"),
            section("Emotional Meaning"),
            section("Before"),
            section("After"),
            section("Related Notes"),
        ),
        extra_frontmatter=(
            "date_start: {{date_start}}",
            "date_end:",
            "date_precision: unknown",
            "life_period:",
            "threads: []",
            "people: []",
            "projects: []",
            "places: []",
            "emotional_charge: unknown",
            "pressure_level: unknown",
            "turning_point: true",
        ),
    ),
    TemplateSpec(
        "money-context.md",
        "money_context",
        "{{money_context}}",
        "financial",
        ("self-atlas/money",),
        (
            section("Current Picture"),
            section("Income"),
            section("Recurring Costs"),
            section("Goals"),
            section("Pressure Points"),
            section("Linked Plans"),
            section("Open Questions"),
        ),
    ),
    TemplateSpec(
        "logistics-thread.md",
        "logistics_thread",
        "{{thread}}",
        "private",
        ("self-atlas/logistics",),
        (
            section("Deadline"),
            section("Current Status"),
            section("Documents Or Actions"),
            section("Blockers"),
            section("Next Step"),
            section("Related People"),
            section("Related Sources"),
        ),
    ),
    TemplateSpec(
        "health-observation.md",
        "health_observation",
        "{{observation}}",
        "health",
        ("self-atlas/health",),
        (
            section("Observation"),
            section("Date And Frequency"),
            section("Triggers"),
            section("Context"),
            section("What Changed"),
            section("Follow Up Question"),
            section("Note", "Not medical advice. This is memory context only."),
        ),
    ),
    TemplateSpec(
        "health-metric.md",
        "health_metric",
        "{{metric}}",
        "health",
        ("self-atlas/health",),
        (
            section("Metric"),
            section("Value"),
            section("Unit"),
            section("Date"),
            section("Source"),
            section("Trend"),
            section("Context"),
            section("Note", "Not medical advice. This is memory context only."),
        ),
    ),
)

def template_files(prefix: str = "00 System/Templates") -> dict[str, str]:
    return {f"{prefix}/{template.filename}": template.render() for template in TEMPLATE_LIBRARY}

def sync_template_directory(directory: Path, overwrite: bool) -> tuple[list[Path], list[Path]]:
    directory = normalized_path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    skipped = []
    for template in TEMPLATE_LIBRARY:
        path = directory / template.filename
        content = template.render()
        if path.exists() and not overwrite:
            skipped.append(path)
            continue
        if path.exists() and path.read_text(encoding="utf-8") == content:
            skipped.append(path)
            continue
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written, skipped

def list_templates() -> None:
    print("# Self Atlas Templates")
    print()
    for template in TEMPLATE_LIBRARY:
        print(f"- {template.filename}: {template.note_type}, {template.sensitivity}")
    print()
    print(f"Total: {len(TEMPLATE_LIBRARY)}")

def sync_vault_templates(vault: Path, overwrite: bool) -> None:
    vault = require_vault(vault)
    written, skipped = sync_template_directory(vault / "00 System" / "Templates", overwrite)
    print(f"Template directory: {vault / '00 System' / 'Templates'}")
    print(f"Written: {len(written)}")
    print(f"Skipped: {len(skipped)}")
    for path in written:
        print(f"- {path.relative_to(vault)}")

def write_template_assets(directory: Path, overwrite: bool) -> None:
    written, skipped = sync_template_directory(directory, overwrite)
    print(f"Template asset directory: {normalized_path(directory)}")
    print(f"Written: {len(written)}")
    print(f"Skipped: {len(skipped)}")
    for path in written:
        print(f"- {path}")
