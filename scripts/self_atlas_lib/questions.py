from __future__ import annotations

import json
import datetime as dt
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .constants import DEFAULT_QUESTION_COUNT, MAX_QUESTION_BATCH, WIKI_LINK_RE
from .vault import extract_section_bullets, require_vault


QUESTION_QUEUE_RELATIVE = "00 System/Question Queue.md"
QUESTION_REFRESH_MODES = ("shuffle", "regenerate", "mixed")


@dataclass(frozen=True)
class QuestionTemplate:
    domain: str
    intent: str
    question: str
    why: str
    hint: str
    examples: tuple[str, ...]
    target_note_types: tuple[str, ...]
    sensitivity: str
    evidence_needed: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "domain": self.domain,
            "intent": self.intent,
            "question": self.question,
            "why": self.why,
            "hint": self.hint,
            "examples": list(self.examples),
            "target_note_types": list(self.target_note_types),
            "sensitivity": self.sensitivity,
            "evidence_needed": list(self.evidence_needed),
        }

@dataclass(frozen=True)
class QuestionCandidate:
    source: str
    question: str
    template: QuestionTemplate
    signature: str
    generated: bool = False

@dataclass(frozen=True)
class QuestionRefreshResult:
    mode: str
    selected: tuple[QuestionCandidate, ...]
    rotated_out: tuple[str, ...]
    existing_count: int
    generated_count: int
    queue_path: str
    applied: bool

QUESTION_TEMPLATES = (
    QuestionTemplate(
        domain="identity",
        intent="pin-down-self-misread",
        question="What is one specific moment where someone misread you, and what did they get wrong?",
        why="This turns vague identity language into a sourced pattern with a person, scene, and correction.",
        hint="Give the person, rough date, place/context, what they assumed, and what was actually true.",
        examples=(
            "In a meeting last month, someone read intensity as arrogance, but it was urgency plus fear.",
            "A friend thought I was detached; I was actually overwhelmed and trying not to leak it everywhere.",
            "The real scene was messier: ...",
        ),
        target_note_types=("identity", "person", "pattern", "event"),
        sensitivity="private",
        evidence_needed=("person", "rough date", "specific scene", "wrong read", "true read"),
    ),
    QuestionTemplate(
        domain="identity",
        intent="make-pattern-concrete",
        question="What is a pattern you keep describing abstractly that needs one ugly little real example?",
        why="Self Atlas remembers better when a pattern has a receipt instead of floating around as poetic fog.",
        hint="Name the pattern, then give the most recent example with date-ish context, trigger, action, and cost.",
        examples=(
            "Scattering: Tuesday night, I opened five project threads instead of finishing the one obvious task.",
            "Avoidance: I delayed one email because replying made the next step real.",
            "The pattern is not cute, here it is: ...",
        ),
        target_note_types=("pattern", "identity", "event"),
        sensitivity="private",
        evidence_needed=("pattern name", "recent date", "trigger", "behavior", "cost"),
    ),
    QuestionTemplate(
        domain="identity",
        intent="capture-focus-conditions",
        question="When did focus come naturally, and what conditions made it possible?",
        why="This turns the structure/focus problem into evidence instead of self-judgment with nicer typography.",
        hint="Give the date-ish period, project/task, environment, pressure level, novelty, people, and what was absent.",
        examples=(
            "I focused when there was a visible deadline, a real user, and one obvious artifact to finish.",
            "I focused because the task had novelty, pressure, and no one interrupting the rhythm.",
            "The focus conditions were: ...",
        ),
        target_note_types=("identity", "pattern", "work", "event"),
        sensitivity="private",
        evidence_needed=("date-ish period", "task", "environment", "pressure", "novelty", "what helped", "what was absent"),
    ),
    QuestionTemplate(
        domain="work",
        intent="capture-real-role",
        question="What did you actually own at work this week, not the fake job-description version?",
        why="This sharpens role, skill, project, and career evidence without corporate cosplay.",
        hint="List the project, artifact, decision, people involved, and what would have broken without you.",
        examples=(
            "I owned the SwiftUI interaction pass for one screen; without me it would have shipped as mush.",
            "I made the product call, the UI call, and the taste call, even though only one was official.",
            "This week the real ownership was: ...",
        ),
        target_note_types=("work", "project", "skill", "person"),
        sensitivity="normal",
        evidence_needed=("date range", "project", "artifact", "people", "decision", "outcome"),
    ),
    QuestionTemplate(
        domain="work",
        intent="name-team-dynamics",
        question="Who made your work better recently, who made it harder, and what exactly happened?",
        why="People notes become useful only when they contain behavior, trust, friction, and real scenes.",
        hint="Use names, roles, the moment, what they did, and whether that changed trust.",
        examples=(
            "One teammate clarified the problem and saved me two days.",
            "One person made it harder by staying vague until the decision had already moved.",
            "The useful/frustrating people map is: ...",
        ),
        target_note_types=("person", "work", "project", "pattern"),
        sensitivity="private",
        evidence_needed=("names", "roles", "specific incident", "trust change", "follow-up"),
    ),
    QuestionTemplate(
        domain="project",
        intent="define-proof-moment",
        question="For one active project, what exact moment would prove it is working?",
        why="Projects stop being vague ambitions when the proof moment is observable.",
        hint="Name the project, the user/action/output, the feeling, and what date or build should prove it.",
        examples=(
            "The proof is someone making one thing they are proud to save, not just clicking around.",
            "The proof is an export good enough that I would show it without apologizing.",
            "For this project, the proof moment is: ...",
        ),
        target_note_types=("project", "event", "preference", "work"),
        sensitivity="normal",
        evidence_needed=("project", "observable action", "artifact", "deadline or version", "success signal"),
    ),
    QuestionTemplate(
        domain="project",
        intent="record-project-timeline",
        question="What are the real dates or phases of this project so future-you stops hand-waving the timeline?",
        why="Timelines make career and project memory legible. Vibes do not have a calendar, unfortunately.",
        hint="Give start date, pause date if any, current status, major milestone, and who was involved.",
        examples=(
            "Started around March, paused in May, revived after one prototype showed the loop could work.",
            "It had three phases: hack, ugly prototype, actual product direction.",
            "The timeline is roughly: ...",
        ),
        target_note_types=("project", "event", "work"),
        sensitivity="normal",
        evidence_needed=("start date", "major phases", "status", "people", "source/link if available"),
    ),
    QuestionTemplate(
        domain="project",
        intent="resolve-project-identity",
        question="Which project needs its real name, link, dates, and current status pinned down?",
        why="Old projects turn into ghost blobs unless the graph knows what they were called, where they lived, and whether they still matter.",
        hint="Give official name, link if it exists, rough dates, your role, current status, and emotional or strategic relevance.",
        examples=(
            "The official name was different from the nickname, and the live link is probably gone.",
            "It had two iterations with different names, and only the second one still matters.",
            "The project identity is: ...",
        ),
        target_note_types=("project", "event", "work"),
        sensitivity="normal",
        evidence_needed=("official name", "link", "rough dates", "role", "status", "relevance"),
    ),
    QuestionTemplate(
        domain="taste",
        intent="capture-live-reference",
        question="What did you see, hear, use, or touch recently that had actual pulse?",
        why="Taste gets stronger when it is pinned to specific references, not adjectives doing interpretive dance.",
        hint="Name the thing, date-ish, exact detail, emotional effect, and what rule it teaches your work.",
        examples=(
            "A transition in an app felt alive because the timing had weight, not because it was bouncy.",
            "A song worked because the vocal texture felt warm but not polished to death.",
            "The living reference is: ...",
        ),
        target_note_types=("preference", "creative_reference", "project"),
        sensitivity="normal",
        evidence_needed=("reference name", "date-ish", "medium", "exact detail", "reusable lesson"),
    ),
    QuestionTemplate(
        domain="taste",
        intent="capture-anti-taste",
        question="What specific thing made you think, no, absolutely not, get this dead little thing away from me?",
        why="Anti-taste protects the graph from generic sludge and makes product decisions faster.",
        hint="Give the app/brand/song/scene/object, the offending detail, and the better replacement principle.",
        examples=(
            "A dashboard used fake glass, fake gradients, and copy that sounded embalmed.",
            "A song had clean production but no blood in it.",
            "The thing I reject is: ...",
        ),
        target_note_types=("preference", "creative_reference", "pattern"),
        sensitivity="normal",
        evidence_needed=("specific example", "bad detail", "why it failed", "replacement principle"),
    ),
    QuestionTemplate(
        domain="taste",
        intent="capture-sonic-identity",
        question="What exact sonic world should this artist identity own?",
        why="Music identity needs sound, language, references, lyrical themes, and performance shape, not just genre soup.",
        hint="Name the language mix, songs/artists, production palette, lyrical world, and whether modes belong together or separate.",
        examples=(
            "Warm R&B vocals, native-language emotional directness, sparse drums, and lyrics about longing without melodrama.",
            "Pop hooks and hip-hop cadence can live together, but ballads may need their own lane.",
            "The sonic world is: ...",
        ),
        target_note_types=("identity", "preference", "creative_reference"),
        sensitivity="private",
        evidence_needed=("language mix", "reference songs/artists", "production palette", "lyrical themes", "modes to merge or split"),
    ),
    QuestionTemplate(
        domain="person",
        intent="de-cardboard-a-person",
        question="Pick one person note that still feels like a cardboard cutout. What is one real scene with them?",
        why="People become memorable through scenes: place, mood, action, and what changed between you.",
        hint="Give their name, rough date/age, place, what happened, and what it says about the relationship.",
        examples=(
            "We were in a car after school and they said one thing that changed how I saw ambition.",
            "At work, they handled pressure in a way I still remember.",
            "The real scene is: ...",
        ),
        target_note_types=("person", "event", "pattern"),
        sensitivity="private",
        evidence_needed=("name", "rough date", "place", "scene", "relationship meaning"),
    ),
    QuestionTemplate(
        domain="family",
        intent="capture-family-scene",
        question="What family memory has a specific room, object, smell, or age attached to it?",
        why="Family patterns are usually stored in scenes, not clean explanations.",
        hint="Start with the sensory anchor, then name who was there, what happened, and what you carried from it.",
        examples=(
            "A kitchen table memory explains why silence feels loaded.",
            "A specific object reminds me of how care was shown without being said.",
            "The memory is: ...",
        ),
        target_note_types=("person", "event", "value", "pattern"),
        sensitivity="private",
        evidence_needed=("age/date-ish", "people", "place", "sensory anchor", "meaning"),
    ),
    QuestionTemplate(
        domain="love",
        intent="capture-support-scene",
        question="What is a recent moment where support worked, failed, or almost worked?",
        why="Love notes need practical scenes, not just pretty fog and future montage music.",
        hint="Give date-ish context, what happened, what each person needed, and what should be remembered next time.",
        examples=(
            "Support worked because I shut up, made the practical thing easier, and did not turn it into a speech.",
            "Support failed because I offered strategy when the real need was softness.",
            "The moment was: ...",
        ),
        target_note_types=("person", "event", "pattern", "desire"),
        sensitivity="intimate",
        evidence_needed=("date-ish", "people", "need", "action", "lesson"),
    ),
    QuestionTemplate(
        domain="money",
        intent="capture-real-number",
        question="What is one money number you keep avoiding because it makes the plan annoyingly real?",
        why="Financial memory needs amounts, currencies, cadence, and deadlines. Otherwise it becomes mist with anxiety in it.",
        hint="Give amount, currency, monthly/one-time cadence, deadline, and what choice it affects.",
        examples=(
            "I need X per month for rent and Y by August for travel.",
            "The number I avoid is the minimum cash buffer before I can take a creative risk.",
            "The honest number is: ...",
        ),
        target_note_types=("money_context", "logistics_thread", "work", "desire"),
        sensitivity="financial",
        evidence_needed=("amount", "currency", "cadence", "deadline", "decision affected"),
    ),
    QuestionTemplate(
        domain="health",
        intent="capture-body-event",
        question="What exactly happened the last time your body gave you a weird signal?",
        why="Health notes need dates, units, frequency, triggers, and context, not ominous vibes in a trench coat.",
        hint="Give date-ish, duration, intensity, trigger, what changed, and whether you took any action.",
        examples=(
            "It happened after poor sleep, lasted ten minutes, felt sharp, and stopped when I rested.",
            "It has happened three times this month, usually after caffeine or stress.",
            "The body event was: ...",
        ),
        target_note_types=("health_observation", "health_metric", "event"),
        sensitivity="health",
        evidence_needed=("date", "duration", "frequency", "intensity", "trigger", "action taken"),
    ),
    QuestionTemplate(
        domain="logistics",
        intent="capture-dated-obligation",
        question="What upcoming obligation has a real date, required documents, and consequences if missed?",
        why="Practical life memory should be boring in the best way: dates, documents, blockers, next action.",
        hint="Give exact date/time, place, documents, current status, blocker, and next action.",
        examples=(
            "The appointment is on June 3; documents A and B are ready, C needs printing.",
            "The deadline is clear but the email confirmation is still missing.",
            "The obligation is: ...",
        ),
        target_note_types=("logistics_thread", "event"),
        sensitivity="private",
        evidence_needed=("exact date", "place", "documents", "status", "blocker", "next action"),
    ),
    QuestionTemplate(
        domain="timeline",
        intent="anchor-life-phase",
        question="What month or year separates one chapter of your life from the next?",
        why="A life graph needs time anchors, otherwise everything becomes one long soup of becoming.",
        hint="Give the date range, what ended, what started, who was around, and what changed in your behavior.",
        examples=(
            "Summer 2024 was when one work identity ended and a new product direction started.",
            "A move, breakup, job, project, or illness quietly split the timeline.",
            "The chapter break is: ...",
        ),
        target_note_types=("event", "identity", "work", "pattern"),
        sensitivity="private",
        evidence_needed=("month/year", "before state", "after state", "people", "proof event"),
    ),
    QuestionTemplate(
        domain="desire",
        intent="make-desire-actionable",
        question="What do you want badly enough that it needs a date, number, or named next move attached?",
        why="Desire without evidence turns into decorative smoke. Pretty, useless, very rude.",
        hint="Name the desire, the proof you want, the next concrete move, and when it should happen.",
        examples=(
            "I want a body change, and the proof is a metric by a date.",
            "I want a creative identity, and the proof is one released artifact.",
            "The desire that needs a receipt is: ...",
        ),
        target_note_types=("desire", "event", "value", "project"),
        sensitivity="private",
        evidence_needed=("desire", "date", "number or artifact", "next move", "blocker"),
    ),
    QuestionTemplate(
        domain="obsession",
        intent="trace-rabbit-hole",
        question="What have you kept returning to this week even though nobody assigned it to you?",
        why="Obsession is often a compass wearing a stupid disguise.",
        hint="Name the rabbit hole, when it appeared, what tabs/notes/actions prove it, and what it might connect to.",
        examples=(
            "I kept opening references for one visual style because it connects to a project I am not admitting yet.",
            "I watched three videos about the same tool because the workflow feels like future product material.",
            "The thing following me around is: ...",
        ),
        target_note_types=("creative_reference", "preference", "project", "identity"),
        sensitivity="normal",
        evidence_needed=("topic", "recent date", "proof of attention", "connected project", "next experiment"),
    ),
)

DOMAINS = {
    "identity": [
        (
            "What do people consistently misunderstand about you?",
            "This can update identity, relationships, work style, and emotional-pattern notes at once.",
            "Answer with a repeated misread, a specific person, or a moment where you felt unseen.",
        ),
        (
            "What part of you feels obvious internally but rarely visible externally?",
            "This creates useful contrast between self-image and public signal.",
            "Think temperament, ambition, sensitivity, humor, fear, or taste.",
        ),
    ],
    "family": [
        (
            "Who in your family shaped your taste, ambition, or emotional wiring the most?",
            "One answer can create people notes, influence links, values, and timeline entries.",
            "Name the person and what you inherited, copied, resisted, or still carry.",
        ),
        (
            "What family pattern do you want to keep, and what pattern do you want to break?",
            "This links family history to values, future goals, and relationship context.",
            "You can answer with behavior, money, conflict, affection, work, silence, or care.",
        ),
    ],
    "work": [
        (
            "What kind of project makes you annoyingly alive?",
            "This updates career direction, taste, energy, skills, and project-selection notes.",
            "Name a recent project, a fantasy project, or the opposite: work that deadens you.",
        ),
        (
            "What do you refuse to make, even if it would be profitable or impressive?",
            "Anti-goals are often cleaner than goals. Less motivational-poster nonsense, more signal.",
            "Think product categories, aesthetics, company vibes, user harms, or workflows.",
        ),
    ],
    "taste": [
        (
            "What do you instantly reject because it feels fake, cold, generic, or soulless?",
            "This builds anti-taste, which is weirdly one of the fastest ways to protect taste.",
            "Give examples from apps, films, brands, writing, UI, rooms, clothes, or music.",
        ),
        (
            "What recent thing made you think: yes, that has a pulse?",
            "This captures living references instead of abstract taste words floating around uselessly.",
            "It can be a product, scene, sentence, gesture, color, sound, person, or tiny detail.",
        ),
    ],
    "health": [
        (
            "What body or energy pattern should future-you remember?",
            "This can create health context without pretending to be a doctor, which would be dumb.",
            "Include date, units, triggers, sleep, appetite, pain, training, medication, or mood if relevant.",
        ),
        (
            "What health metric do you actually care about tracking, and why?",
            "Useful health notes start with meaning, not spreadsheet cosplay.",
            "Examples: weight, sleep, resting heart rate, focus, energy crashes, strength, pain, steps.",
        ),
    ],
    "desire": [
        (
            "What do you want badly but keep making weirdly indirect moves toward?",
            "This connects goals, avoidance, fear, ambition, and open threads.",
            "Answer with the desire, the detour, and what makes the direct path feel loaded.",
        ),
        (
            "What would make the next year feel like it actually belonged to you?",
            "This updates goals and values without becoming LinkedIn soup.",
            "Think craft, money, body, love, family, reputation, home, adventure, or freedom.",
        ),
    ],
    "obsession": [
        (
            "What topic, tool, style, person, or world keeps pulling your attention back?",
            "Obsession is a breadcrumb trail. Usually not random. Usually annoyingly revealing.",
            "Name the thing and what part of it hooks you.",
        ),
        (
            "What rabbit hole has been following you around lately?",
            "This captures active curiosity and can link into work, taste, and future projects.",
            "Examples: an API, director, app pattern, city, workflow, object, sport, aesthetic, theory.",
        ),
    ],
}

QUESTION_EXAMPLES = {
    "What do people consistently misunderstand about you?": {
        "single": "People mistake my intensity for arrogance.",
        "multiple": "Intensity, sensitivity, ambition, and weird taste all get flattened.",
        "custom": "I will write the real version myself.",
    },
    "What part of you feels obvious internally but rarely visible externally?": {
        "single": "My inner life is much warmer and more emotional than I look.",
        "multiple": "Ambition, softness, fear, humor, and taste are all quieter on the outside.",
        "custom": "I will describe the hidden part myself.",
    },
    "Who in your family shaped your taste, ambition, or emotional wiring the most?": {
        "single": "One person shaped me the most, and I can name what I inherited.",
        "multiple": "Different people shaped my taste, ambition, emotional habits, and fears.",
        "custom": "I will tell the family story in my own words.",
    },
    "What family pattern do you want to keep, and what pattern do you want to break?": {
        "single": "I know one pattern I want to keep and one I want to break.",
        "multiple": "There are several patterns around care, money, conflict, silence, and work.",
        "custom": "I will explain the pattern properly.",
    },
    "What kind of project makes you annoyingly alive?": {
        "single": "A crafted product with taste, motion, and real emotional usefulness.",
        "multiple": "Design, code, storytelling, systems, and visible polish all need to be alive.",
        "custom": "I will name the project type myself.",
    },
    "What do you refuse to make, even if it would be profitable or impressive?": {
        "single": "I refuse soulless productivity software dressed up as innovation.",
        "multiple": "I reject generic AI wrappers, manipulative products, bland dashboards, and fake polish.",
        "custom": "I will define my anti-goals myself.",
    },
    "What do you instantly reject because it feels fake, cold, generic, or soulless?": {
        "single": "Generic startup language and lifeless UI make me reject things instantly.",
        "multiple": "Cold copy, fake polish, template layouts, weak motion, and safe taste all bother me.",
        "custom": "I will list the things I reject myself.",
    },
    "What recent thing made you think: yes, that has a pulse?": {
        "single": "A recent product, scene, or detail felt alive enough to remember.",
        "multiple": "Several things had a pulse: visual rhythm, interaction, tone, material, and emotion.",
        "custom": "I will name the living reference myself.",
    },
    "What body or energy pattern should future-you remember?": {
        "single": "There is one recurring energy pattern I should track.",
        "multiple": "Sleep, food, focus, stress, pain, movement, and mood all seem connected.",
        "custom": "I will describe the health pattern myself.",
    },
    "What health metric do you actually care about tracking, and why?": {
        "single": "One metric matters most because it changes how I feel day to day.",
        "multiple": "Weight, sleep, focus, energy crashes, strength, pain, and mood all matter together.",
        "custom": "I will define the metric and reason myself.",
    },
    "What do you want badly but keep making weirdly indirect moves toward?": {
        "single": "There is one desire I keep circling instead of naming directly.",
        "multiple": "Desire, fear, money, reputation, body, love, and creative ambition are tangled.",
        "custom": "I will say what I want in my own words.",
    },
    "What would make the next year feel like it actually belonged to you?": {
        "single": "A year centered on craft, freedom, and momentum would feel like mine.",
        "multiple": "Craft, money, body, love, family, home, reputation, and adventure all matter.",
        "custom": "I will describe the year myself.",
    },
    "What topic, tool, style, person, or world keeps pulling your attention back?": {
        "single": "One obsession keeps coming back because it feels connected to who I am becoming.",
        "multiple": "Several obsessions are linked through taste, work, identity, and future projects.",
        "custom": "I will name the obsession myself.",
    },
    "What rabbit hole has been following you around lately?": {
        "single": "One rabbit hole keeps showing up in my tabs, notes, or conversations.",
        "multiple": "A few rabbit holes are connected and probably pointing at the same deeper interest.",
        "custom": "I will describe the rabbit hole myself.",
    },
}

def infer_question_domain(question: str) -> str:
    lowered = question.lower()
    domain_keywords = [
        ("logistics", ("visa", "appointment", "document", "documents", "deadline", "immigration", "relocation", "checklist", "submission")),
        ("health", ("health", "heart", "body", "medical", "sleep", "pain", "energy")),
        ("money", ("money", "financial", "income", "saving", "rent", "travel", "spreadsheet")),
        ("love", ("love", "girlfriend", "boyfriend", "partner", "spouse", "relationship", "support")),
        ("family", ("family", "father", "mother", "sister", "parent", "brother")),
        ("timeline", ("timeline", "years", "year", "month", "date", "phase", "chapter", "attend", "attended")),
        ("project", ("project", "prototype", "proof", "interaction", "gallery", "build", "app", "startup", "startups", "tool", "platform")),
        ("work", ("work", "role", "responsibility", "responsibilities", "job", "career", "team", "teammate", "teammates", "colleague")),
        ("person", ("person", "people", "friend", "mentor", "colleague", "collaborator", "names", "roles")),
        ("taste", ("taste", "ui", "design", "music", "film", "reference", "sonic", "artist", "r&b", "hip-hop", "ballad", "production palette", "lyrical")),
        ("desire", ("desire", "want", "goal", "badly", "future", "next year")),
        ("obsession", ("obsession", "rabbit hole", "kept returning", "tabs")),
        ("identity", ("misunderstand", "identity", "feel like yourself", "future", "alive", "pattern", "focus", "focused", "conditions")),
    ]
    for domain, keywords in domain_keywords:
        if has_any_keyword(lowered, keywords):
            return domain
    return "identity"

def has_any_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    for keyword in keywords:
        pattern = rf"(?<![A-Za-z0-9_]){re.escape(keyword.lower())}(?![A-Za-z0-9_])"
        if re.search(pattern, lowered):
            return True
    return False

def question_domains() -> list[str]:
    return sorted({template.domain for template in QUESTION_TEMPLATES})

def question_templates_for_domain(domain: str | None = None) -> list[QuestionTemplate]:
    if domain is None:
        return list(QUESTION_TEMPLATES)
    return [template for template in QUESTION_TEMPLATES if template.domain == domain]

def question_template_batch(domain: str | None, limit: int) -> list[QuestionTemplate]:
    if domain:
        return question_templates_for_domain(domain)[:limit]

    grouped: dict[str, list[QuestionTemplate]] = defaultdict(list)
    for template in QUESTION_TEMPLATES:
        grouped[template.domain].append(template)

    selected = []
    index = 0
    while len(selected) < limit:
        added = False
        for templates in grouped.values():
            if index < len(templates):
                selected.append(templates[index])
                added = True
                if len(selected) >= limit:
                    break
        if not added:
            break
        index += 1
    return selected

def default_question_template(domain: str) -> QuestionTemplate:
    templates = question_templates_for_domain(domain)
    if templates:
        return templates[0]
    return question_templates_for_domain("identity")[0]

def clamped_question_count(count: int) -> int:
    return min(MAX_QUESTION_BATCH, max(1, count))

def clean_queued_question(question: str) -> str:
    question = re.sub(r"\s*Source:\s*\[\[.*$", "", question).strip()
    question = re.sub(r"\s+", " ", question)
    return question

def question_signature(question: str) -> str:
    normalized = WIKI_LINK_RE.sub(lambda match: match.group(1).split("/")[-1], question)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", normalized).lower()
    words = [word for word in normalized.split() if len(word) > 2]
    return " ".join(words[:18])

def evidence_needed_for_question(question: str, template: QuestionTemplate) -> tuple[str, ...]:
    evidence = list(template.evidence_needed)
    lowered = question.lower()
    additions = []
    if has_any_keyword(lowered, ("date", "dates", "year", "years", "month", "week", "when", "appointment", "deadline")):
        additions.append("exact date or rough date range")
    if has_any_keyword(lowered, ("name", "names", "who", "people", "roles", "teammates")):
        additions.append("names and roles")
    if has_any_keyword(lowered, ("money", "number", "amount", "cost", "rent", "income", "savings", "budget")):
        additions.append("amount, currency, and cadence")
    if has_any_keyword(lowered, ("document", "documents", "email", "checklist", "submission")):
        additions.append("required documents and current status")
    if has_any_keyword(lowered, ("heart", "pain", "body", "health", "sleep", "energy")):
        additions.append("duration, frequency, intensity, and trigger")
    if has_any_keyword(lowered, ("specific", "example", "scene", "moment", "felt", "feeling")):
        additions.append("specific scene or artifact")
    stopwords = {"and", "or", "the", "a", "an", "of", "to", "if", "with", "current"}
    for item in additions:
        item_words = {word for word in item.split() if word not in stopwords}
        evidence_words = {word for word in " ".join(evidence).split() if word not in stopwords}
        if item not in evidence and not item_words.intersection(evidence_words):
            evidence.append(item)
    return tuple(evidence[:8])

def template_for_question_text(question: str, domain: str | None = None) -> QuestionTemplate:
    inferred = domain or infer_question_domain(question)
    lowered = question.lower()
    templates = question_templates_for_domain(inferred)
    if not templates:
        return default_question_template(inferred)

    keyword_by_intent = (
        ("anchor-life-phase", ("years", "timeline", "date ranges", "date range", "phase", "chapter", "attend", "attended")),
        ("resolve-project-identity", ("official name", "name/link", "link", "real shape", "iterations", "startup", "startups", "nft")),
        ("capture-real-number", ("money", "number", "weekly", "cost", "rent", "savings")),
        ("capture-dated-obligation", ("appointment", "documents", "checklist", "email", "deadline", "submission")),
        ("capture-body-event", ("heart", "pain", "body", "health", "sleep", "energy")),
        ("record-project-timeline", ("phases", "start", "started", "status")),
        ("capture-focus-conditions", ("focus", "focused", "conditions", "structure")),
        ("capture-real-role", ("responsible", "responsibilities", "role", "work", "own", "under")),
        ("name-team-dynamics", ("teammates", "people", "roles", "names", "better", "frustrating")),
        ("define-proof-moment", ("prove", "prototype", "interaction", "first", "gallery", "works")),
        ("capture-sonic-identity", ("sonic", "artist identity", "r&b", "hip-hop", "ballads", "production palette", "lyrical")),
        ("capture-live-reference", ("sonic", "world", "artist", "identity", "music", "reference")),
        ("de-cardboard-a-person", ("person", "friend", "family", "relationship", "remember beyond")),
    )
    for intent, keywords in keyword_by_intent:
        if any(keyword in lowered for keyword in keywords):
            for template in templates:
                if template.intent == intent:
                    return template
    return templates[0]

def print_question_prompt(
    question: str,
    source: str,
    template: QuestionTemplate,
    with_examples: bool,
    index: int | None = None,
) -> None:
    prefix = f"## Question {index}" if index is not None else "## Question"
    print(prefix)
    print(f"Source: {source}")
    print(f"Domain: {template.domain}")
    print(f"Intent: {template.intent}")
    print(f"Sensitivity: {template.sensitivity}")
    print(f"Target notes: {', '.join(template.target_note_types)}")
    print()
    print(f"Question: {question}")
    print(f"Why it matters: {template.why}")
    print(f"Hint: {template.hint}")
    evidence = evidence_needed_for_question(question, template)
    if evidence:
        print("Evidence needed:")
        for item in evidence:
            print(f"- {item}")
    if with_examples:
        print("Examples, if useful:")
        for example_index, example in enumerate(template.examples, start=1):
            print(f"{example_index}. {example}")
    print()

def question_guidance(domain: str) -> tuple[str, str, tuple[str, str, str]]:
    guidance = {
        "health": (
            "This can update health context, open threads, body notes, and practical follow-up without pretending to diagnose anything.",
            "Answer with date, frequency, triggers, intensity, and what changed recently if relevant.",
            (
                "It happens rarely, with a clear trigger.",
                "It connects to sleep, stress, posture, food, movement, or mood.",
                "The real pattern is not obvious yet: ...",
            ),
        ),
        "money": (
            "This can update money context, USA planning, work goals, and practical constraints.",
            "Answer with current numbers, recurring costs, savings goals, and what would make the plan feel humane.",
            (
                "I need a simple monthly plan around rent, travel, and savings.",
                "Money, relocation plans, a partner's creative work, and creative freedom are tangled.",
                "The honest money picture is: ...",
            ),
        ),
        "work": (
            "This can update career, skills, current identity, project direction, and future job notes.",
            "Answer with daily work, ownership, what people rely on you for, and what feels alive or draining.",
            (
                "I mostly own product/interface craft and prototype direction.",
                "I do a mixed role: design, SwiftUI, product thinking, AI/context ideas, and taste feedback.",
                "The official role and the real role are different: ...",
            ),
        ),
        "love": (
            "This can update love, desires, future-life texture, support patterns, and emotional anchors.",
            "Answer with what support looks like in practice, not just the nice movie-trailer version.",
            (
                "She needs emotional safety and steady support most.",
                "Support means production help, editing/design help, career strategy, and space.",
                "The real answer is more delicate: ...",
            ),
        ),
        "family": (
            "This can update family, values, emotional patterns, and future-parent notes.",
            "Answer with a person, pattern, repeated moment, or what you want to keep or break.",
            (
                "One family pattern shaped me the most.",
                "Different people shaped ambition, taste, fear, and care in different ways.",
                "The real family pattern is: ...",
            ),
        ),
        "logistics": (
            "This can update timeline, open threads, immigration context, and practical next actions.",
            "Answer with dates, documents, confirmations, blockers, and what is already done.",
            (
                "The appointment/documents situation is mostly handled.",
                "Some pieces are done, but medical/email/documents still need cleanup.",
                "The real current status is: ...",
            ),
        ),
        "taste": (
            "This can update taste, anti-taste, references, product standards, and creative direction.",
            "Answer with concrete examples: apps, films, songs, interfaces, objects, or moments.",
            (
                "One recent reference felt alive enough to matter.",
                "Several references connect through warmth, rhythm, motion, and emotional clarity.",
                "The real taste signal is stranger: ...",
            ),
        ),
        "identity": (
            "This can update identity, values, tensions, desires, and recurring patterns.",
            "Answer with a moment, repeated pattern, person, project, or contradiction.",
            (
                "One clear pattern explains a lot.",
                "Several things are true at once, which is annoying but useful.",
                "The real answer is messier: ...",
            ),
        ),
    }
    return guidance.get(domain, guidance["identity"])

def queued_question_candidates(vault: Path) -> list[QuestionCandidate]:
    queued = extract_section_bullets(vault, QUESTION_QUEUE_RELATIVE, "Next Questions")
    return prepare_question_candidates(queued, "Question Queue")

def prepare_question_candidates(raw_questions: list[str], source: str, generated: bool = False) -> list[QuestionCandidate]:
    candidates = []
    seen = set()
    for raw_question in raw_questions:
        question = clean_queued_question(raw_question)
        if not question:
            continue
        signature = question_signature(question)
        if not signature or signature in seen:
            continue
        seen.add(signature)
        inferred_domain = infer_question_domain(question)
        template = template_for_question_text(question, inferred_domain)
        candidates.append(QuestionCandidate(source, question, template, signature, generated))
    return candidates

def varied_question_sample(
    candidates: list[QuestionCandidate],
    limit: int,
    rng: random.Random,
) -> list[QuestionCandidate]:
    grouped: dict[str, list[QuestionCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.template.domain].append(candidate)
    for grouped_items in grouped.values():
        rng.shuffle(grouped_items)
    domains = list(grouped)
    rng.shuffle(domains)

    selected = []
    index = 0
    while len(selected) < limit:
        added = False
        for domain in domains:
            grouped_items = grouped[domain]
            if index < len(grouped_items):
                selected.append(grouped_items[index])
                added = True
                if len(selected) >= limit:
                    break
        if not added:
            break
        index += 1
    return selected

def question_concept(candidate: QuestionCandidate) -> tuple[str, str]:
    return (candidate.template.domain, candidate.template.intent)

def generated_question_candidates(
    existing_signatures: set[str],
    rng: random.Random,
    blocked_concepts: set[tuple[str, str]] | None = None,
) -> list[QuestionCandidate]:
    templates = list(QUESTION_TEMPLATES)
    rng.shuffle(templates)
    candidates = []
    seen = set(existing_signatures)
    blocked_concepts = blocked_concepts or set()
    for template in templates:
        signature = question_signature(template.question)
        concept = (template.domain, template.intent)
        if signature in seen or concept in blocked_concepts:
            continue
        seen.add(signature)
        candidates.append(
            QuestionCandidate(
                "Template Refresh",
                template.question,
                template,
                signature,
                generated=True,
            )
        )
    return candidates

def build_question_refresh(vault: Path, count: int, mode: str = "mixed", seed: int | None = None) -> QuestionRefreshResult:
    vault = require_vault(vault)
    if mode not in QUESTION_REFRESH_MODES:
        known = ", ".join(QUESTION_REFRESH_MODES)
        raise SystemExit(f"Unknown refresh mode '{mode}'. Known modes: {known}")

    limit = clamped_question_count(count)
    rng = random.Random(seed)
    existing = queued_question_candidates(vault)
    existing_signatures = {candidate.signature for candidate in existing}
    existing_concepts = {question_concept(candidate) for candidate in existing}
    selected: list[QuestionCandidate] = []

    if mode == "shuffle":
        selected = varied_question_sample(existing, limit, rng)
    elif mode == "regenerate":
        fresh = generated_question_candidates(existing_signatures, rng, existing_concepts)
        selected = varied_question_sample(fresh, limit, rng)
        if len(selected) < limit:
            selected.extend(varied_question_sample(existing, limit - len(selected), rng))
    else:
        existing_limit = min(len(existing), max(1, limit // 2))
        selected.extend(varied_question_sample(existing, existing_limit, rng))
        selected_signatures = {candidate.signature for candidate in selected}
        selected_concepts = {question_concept(candidate) for candidate in selected}
        fresh = generated_question_candidates(existing_signatures | selected_signatures, rng, existing_concepts | selected_concepts)
        selected.extend(varied_question_sample(fresh, limit - len(selected), rng))
        selected_signatures = {candidate.signature for candidate in selected}
        if len(selected) < limit:
            remaining_existing = [candidate for candidate in existing if candidate.signature not in selected_signatures]
            selected.extend(varied_question_sample(remaining_existing, limit - len(selected), rng))
        selected = varied_question_sample(selected, limit, rng)

    selected = selected[:limit]
    selected_signatures = {candidate.signature for candidate in selected}
    rotated_out = tuple(candidate.question for candidate in existing if candidate.signature not in selected_signatures)
    generated_count = sum(1 for candidate in selected if candidate.generated)
    return QuestionRefreshResult(
        mode=mode,
        selected=tuple(selected),
        rotated_out=rotated_out,
        existing_count=len(existing),
        generated_count=generated_count,
        queue_path=QUESTION_QUEUE_RELATIVE,
        applied=False,
    )

def question_refresh_history_entry(result: QuestionRefreshResult) -> str:
    timestamp = dt.datetime.now().isoformat(timespec="seconds")
    lines = [
        f"### {timestamp}",
        "",
        f"- Mode: {result.mode}",
        f"- Previous queue: {result.existing_count}",
        f"- New queue: {len(result.selected)}",
        f"- Generated: {result.generated_count}",
    ]
    if result.rotated_out:
        lines.extend(["", "Rotated out:"])
        lines.extend(f"- {question}" for question in result.rotated_out)
    return "\n".join(lines).rstrip() + "\n"

def replace_next_questions_section(text: str, result: QuestionRefreshResult) -> str:
    marker = "## Next Questions"
    bullets = "\n".join(f"- {candidate.question}" for candidate in result.selected)
    new_section = f"{marker}\n\n{bullets}\n"

    if marker in text:
        start = text.index(marker)
        next_heading = text.find("\n## ", start + len(marker))
        before = text[:start].rstrip()
        after = "" if next_heading == -1 else text[next_heading:].lstrip("\n")
        text = f"{before}\n\n{new_section}\n{after}".rstrip() + "\n"
    else:
        text = f"{text.rstrip()}\n\n{new_section}"

    text = re.sub(r"(?m)^updated:\s*.*$", f"updated: {dt.date.today().isoformat()}", text, count=1)
    history = question_refresh_history_entry(result)
    history_marker = "## Question Refresh History"
    if history_marker in text:
        start = text.index(history_marker) + len(history_marker)
        return f"{text[:start].rstrip()}\n\n{history}{text[start:].lstrip()}".rstrip() + "\n"
    return f"{text.rstrip()}\n\n{history_marker}\n\n{history}"

def refresh_questions(
    vault: Path,
    count: int,
    mode: str,
    with_examples: bool,
    apply: bool,
    seed: int | None,
) -> QuestionRefreshResult:
    vault = require_vault(vault)
    result = build_question_refresh(vault, count, mode, seed)

    if apply:
        queue_path = vault / QUESTION_QUEUE_RELATIVE
        text = queue_path.read_text(encoding="utf-8") if queue_path.exists() else "# Question Queue\n"
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        queue_path.write_text(replace_next_questions_section(text, result), encoding="utf-8")
        result = QuestionRefreshResult(
            mode=result.mode,
            selected=result.selected,
            rotated_out=result.rotated_out,
            existing_count=result.existing_count,
            generated_count=result.generated_count,
            queue_path=result.queue_path,
            applied=True,
        )

    print("# Refreshed Question Queue")
    print()
    print(f"Vault: {vault}")
    print(f"Queue: {result.queue_path}")
    print(f"Mode: {result.mode}")
    print(f"Count: {len(result.selected)}")
    print(f"Existing queued: {result.existing_count}")
    print(f"Generated: {result.generated_count}")
    rotated_label = "Rotated out" if result.applied else "Rotated out if applied"
    print(f"{rotated_label}: {len(result.rotated_out)}")
    print(f"Applied: {'yes' if result.applied else 'no'}")
    if not result.applied:
        print("Preview only. Re-run with --apply to rewrite the queue.")
    print()
    for index, candidate in enumerate(result.selected, start=1):
        print_question_prompt(candidate.question, candidate.source, candidate.template, with_examples, index)
    return result

def print_questions(domain: str | None, count: int, with_examples: bool) -> None:
    if domain and domain not in question_domains():
        known = ", ".join(question_domains())
        raise SystemExit(f"Unknown domain '{domain}'. Known domains: {known}")
    limit = clamped_question_count(count)
    templates = question_template_batch(domain, limit)
    for index, template in enumerate(templates[:limit], start=1):
        print_question_prompt(template.question, "Template Library", template, with_examples, index if limit > 1 else None)

def list_question_templates(json_output: bool) -> None:
    if json_output:
        print(json.dumps([template.to_json() for template in QUESTION_TEMPLATES], ensure_ascii=False, indent=2))
        return

    print("# Self Atlas Question Templates")
    print()
    for template in QUESTION_TEMPLATES:
        print(f"- {template.domain}/{template.intent}: {template.question}")
        print(f"  Target notes: {', '.join(template.target_note_types)}")
        print(f"  Evidence: {', '.join(template.evidence_needed)}")
    print()
    print(f"Total: {len(QUESTION_TEMPLATES)}")

def suggest_question(vault: Path, domain: str | None, count: int, with_examples: bool) -> None:
    vault = require_vault(vault)
    queued = extract_section_bullets(vault, "00 System/Question Queue.md", "Next Questions")
    open_threads = extract_section_bullets(vault, "00 System/Open Threads.md", "Active Threads")
    candidates = [("Question Queue", item) for item in queued] + [("Open Threads", item) for item in open_threads]
    limit = clamped_question_count(count)

    if domain:
        requested = domain.lower()
        if requested not in question_domains():
            known = ", ".join(question_domains())
            raise SystemExit(f"Unknown domain '{requested}'. Known domains: {known}")
        candidates = [(source, item) for source, item in candidates if infer_question_domain(item) == requested]

    seen = set()
    prepared = []
    for source, raw_question in candidates:
        question = clean_queued_question(raw_question)
        if not question:
            continue
        signature = question_signature(question)
        if signature in seen:
            continue
        seen.add(signature)
        inferred_domain = infer_question_domain(question)
        template = template_for_question_text(question, inferred_domain)
        prepared.append((source, question, template))

    selected_questions = []
    if domain:
        selected_questions = prepared[:limit]
    else:
        grouped: dict[str, list[tuple[str, str, QuestionTemplate]]] = defaultdict(list)
        for item in prepared:
            grouped[item[2].domain].append(item)
        index = 0
        while len(selected_questions) < limit:
            added = False
            for grouped_items in grouped.values():
                if index < len(grouped_items):
                    selected_questions.append(grouped_items[index])
                    added = True
                    if len(selected_questions) >= limit:
                        break
            if not added:
                break
            index += 1

    if len(selected_questions) < limit:
        for template in question_template_batch(domain, limit):
            signature = question_signature(template.question)
            if signature in seen:
                continue
            selected_questions.append(("Template Library", template.question, template))
            seen.add(signature)
            if len(selected_questions) >= limit:
                break

    print("# Suggested Questions")
    print()
    print(f"Vault: {vault}")
    print(f"Count: {len(selected_questions)}")
    print(f"Max batch: {MAX_QUESTION_BATCH}")
    print()
    for index, (source, question, template) in enumerate(selected_questions, start=1):
        print_question_prompt(question, source, template, with_examples, index)
