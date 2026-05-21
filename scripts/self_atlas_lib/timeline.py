from __future__ import annotations

import datetime as dt
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from .constants import EXPORT_SCHEMA_VERSION, WIKI_LINK_RE
from .models import TimelineItem, TimelinePeriod
from .vault import (
    as_list,
    as_string,
    bullet_lines,
    clean_bullet,
    computed_note_id,
    extract_section_text,
    note_inventory,
    normalized_path,
    normalized_source_key,
    require_vault,
    resolve_link_target,
    slugify,
    link_indexes,
)


MONTHS = {
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}

THREAD_KEYWORDS = {
    "love": ("tumendari", "love", "girlfriend", "wife", "romantic", "relationship"),
    "family": ("family", "father", "mother", "sister", "wife", "husband"),
    "career": ("work", "job", "career", "employer", "univision", "genie", "mstars", "startup", "swift", "swiftui"),
    "education": ("school", "grade", "class", "rafl", "university", "teacher", "typography", "gpa"),
    "creative_identity": ("design", "3d", "music", "poster", "artist", "vfx", "drawing", "figma", "taste", "typography"),
    "immigration": ("visa", "embassy", "usa", "green card", "america", "interview", "document submission"),
    "health": ("health", "nose surgery", "surgery", "body", "pain"),
    "money_pressure": ("money", "paid", "pay", "salary", "tuition", "provide", "no job", "no money", "pressure"),
    "confidence": ("potential", "confidence", "confident", "capable", "admired", "best at this work", "realized"),
    "product": ("product", "app", "prototype", "ar", "ios", "velum", "clozy", "void", "seedshare"),
}

PRESSURE_HIGH = (
    "toughest",
    "pressure",
    "painful",
    "uncomfortable",
    "failed",
    "conflict",
    "serious",
    "hated",
    "no job",
    "no money",
    "pause",
    "underage",
)

EXCLUDED_SENSITIVITIES = {"private", "health", "financial", "intimate"}

POSITIVE_CHARGE = ("loved", "love", "spark", "potential", "confident", "admired", "support", "finished", "great")
TURNING_POINT_KEYWORDS = (
    "first major",
    "began",
    "started",
    "met",
    "realized",
    "switched",
    "quit",
    "joined",
    "stopped",
    "entered",
    "created",
)


def timeline_note(note: dict[str, object]) -> bool:
    relative = str(note["relative"])
    tags = {tag.lower() for tag in as_list(note["frontmatter"].get("tags"))}
    note_type = as_string(note["frontmatter"].get("type"))
    return (
        relative.startswith("70 Timeline/")
        or "self-atlas/timeline" in tags
        or note_type in {"event", "life_period", "milestone"}
    )

def clean_timeline_text(text: str) -> str:
    text = re.sub(r"\s+Source:.*$", "", text).strip()
    text = re.sub(r"\s+Sources:.*$", "", text).strip()
    return text

def wiki_targets(text: str) -> list[str]:
    targets = []
    seen = set()
    for match in WIKI_LINK_RE.finditer(text):
        target = normalized_source_key(match.group(1))
        if target and target not in seen:
            targets.append(target)
            seen.add(target)
    return targets

def linked_targets_by_prefix(text: str, prefix: str) -> tuple[str, ...]:
    return tuple(target for target in wiki_targets(text) if target.startswith(prefix))

def source_targets(text: str, note_sources: list[str]) -> tuple[str, ...]:
    sources = [target for target in wiki_targets(text) if target.startswith("90 Sources/")]
    if not sources:
        sources.extend(note_sources)
    seen = []
    for source in sources:
        normalized = normalized_source_key(source)
        if normalized and normalized not in seen:
            seen.append(normalized)
    return tuple(seen)

def infer_threads(text: str, note: dict[str, object]) -> tuple[str, ...]:
    lowered = text.lower()
    tags = " ".join(as_list(note["frontmatter"].get("tags"))).lower()
    threads = []
    for thread, keywords in THREAD_KEYWORDS.items():
        if any(keyword_matches(lowered, keyword) or keyword_matches(tags, keyword) for keyword in keywords):
            threads.append(thread)
    if not threads:
        threads.append("life")
    return tuple(threads)

def keyword_matches(text: str, keyword: str) -> bool:
    if " " in keyword:
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None

def infer_places(text: str) -> tuple[str, ...]:
    places = []
    for match in re.finditer(r"\b(?:in|at|from|to|near)\s+([A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*){0,2})", text):
        place = match.group(1).strip()
        if place not in places:
            places.append(place)
    return tuple(places)

def infer_pressure_level(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in PRESSURE_HIGH):
        return "high"
    if any(keyword in lowered for keyword in ("comfortable", "stable", "easy")):
        return "low"
    return "unknown"

def infer_emotional_charge(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in PRESSURE_HIGH):
        return "heavy"
    if any(keyword in lowered for keyword in POSITIVE_CHARGE):
        return "positive"
    return "unknown"

def infer_turning_point(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in TURNING_POINT_KEYWORDS)

def infer_life_period(text: str, threads: tuple[str, ...]) -> str | None:
    lowered = text.lower()
    if "1st school" in lowered or "grade" in lowered or "middle" in lowered or "high school" in lowered:
        return "school-era"
    if "raffles" in lowered or "university" in lowered:
        return "raffles-university-era"
    if "mstars" in lowered:
        return "mstars-startup-era"
    if "univision" in lowered:
        return "univision-era"
    if "post-univision" in lowered or "no job and no money" in lowered:
        return "post-univision-pressure-era"
    if "genie" in lowered:
        return "genie-runway-era"
    if "visa" in lowered or "embassy" in lowered or "usa" in lowered:
        return "usa-immigration-era"
    if "education" in threads:
        return "education-era"
    if "career" in threads:
        return "career-era"
    return None

def date_from_iso_match(text: str) -> tuple[str, str, str, str] | None:
    match = re.search(r"\b(20\d{2}|19\d{2})-(\d{2})-(\d{2})\b", text)
    if not match:
        return None
    value = match.group(0)
    return value, value, "exact", value

def date_from_month_year(text: str) -> tuple[str, str, str, str] | None:
    match = re.search(r"\b(" + "|".join(MONTHS) + r")\s+(20\d{2}|19\d{2})\b", text, re.I)
    if not match:
        return None
    month = MONTHS[match.group(1).lower()]
    year = match.group(2)
    value = f"{year}-{month}"
    return value, value, "month", match.group(0)

def date_from_year(text: str) -> tuple[str, str, str, str] | None:
    match = re.search(r"\b(?:around|in|as of)?\s*((?:20|19)\d{2})\b", text, re.I)
    if not match:
        return None
    year = match.group(1)
    precision = "approximate" if re.search(r"\baround\b", match.group(0), re.I) else "year"
    return year, year, precision, match.group(0).strip()

def date_from_age_or_grade(text: str) -> tuple[str | None, str, str, str] | None:
    age_match = re.search(r"\bage\s+(\d{1,2})\b", text, re.I)
    if age_match:
        label = f"age {age_match.group(1)}"
        return None, f"age:{int(age_match.group(1)):02d}", "approximate", label
    grade_match = re.search(r"\b(\d+)(?:st|nd|rd|th)\s+grade\b", text, re.I)
    if grade_match:
        label = f"{ordinal(int(grade_match.group(1)))} grade"
        return None, f"grade:{int(grade_match.group(1)):02d}", "approximate", label
    return None

def ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"

def infer_date(text: str) -> tuple[str | None, str | None, str | None, str, str]:
    candidates: list[tuple[int, str | None, str, str, str]] = []
    for match in re.finditer(r"\b(20\d{2}|19\d{2})-(\d{2})-(\d{2})\b", text):
        value = match.group(0)
        candidates.append((match.start(), value, value, "exact", value))
    for match in re.finditer(r"\b(" + "|".join(MONTHS) + r")\s+(20\d{2}|19\d{2})\b", text, re.I):
        month = MONTHS[match.group(1).lower()]
        year = match.group(2)
        value = f"{year}-{month}"
        candidates.append((match.start(), value, value, "month", match.group(0)))
    for match in re.finditer(r"\b(?:around|in|as of)?\s*((?:20|19)\d{2})\b", text, re.I):
        start, end = match.span(1)
        if (start > 0 and text[start - 1] == "-") or (end < len(text) and text[end : end + 1] == "-"):
            continue
        year = match.group(1)
        precision = "approximate" if re.search(r"\baround\b", match.group(0), re.I) else "year"
        candidates.append((match.start(), year, year, precision, match.group(0).strip()))
    for match in re.finditer(r"\bage\s+(\d{1,2})\b", text, re.I):
        label = f"age {match.group(1)}"
        candidates.append((match.start(), None, f"age:{int(match.group(1)):02d}", "approximate", label))
    for match in re.finditer(r"\b(\d+)(?:st|nd|rd|th)\s+grade\b", text, re.I):
        label = f"{ordinal(int(match.group(1)))} grade"
        candidates.append((match.start(), None, f"grade:{int(match.group(1)):02d}", "approximate", label))
    if candidates:
        _, date_start, sort_key, precision, label = sorted(candidates, key=lambda item: item[0])[0]
        return date_start, None, label, precision, sort_key
    return None, None, None, "unknown", "unknown"

def item_title(text: str) -> str:
    cleaned = clean_bullet(text)
    words = cleaned.split()
    if not words:
        return "Timeline Item"
    return " ".join(word.capitalize() for word in words[:8])

def timeline_item_id(source_key: str, text: str, index: int) -> str:
    return f"timeline:{slugify(source_key)}:{index:03d}:{slugify(clean_bullet(text)[:60])}"

def filtered_targets(
    targets: tuple[str, ...],
    by_key: dict[str, dict[str, object]],
    by_base: dict[str, list[dict[str, object]]],
    visible_keys: set[str],
) -> tuple[str, ...]:
    visible = []
    for target in targets:
        target_note, ambiguous = resolve_link_target(target, by_key, by_base)
        if ambiguous or not target_note:
            continue
        if str(target_note["key"]) in visible_keys:
            visible.append(target)
    return tuple(visible)

def hidden_or_unresolved_targets(
    text: str,
    by_key: dict[str, dict[str, object]],
    by_base: dict[str, list[dict[str, object]]],
    visible_keys: set[str],
) -> bool:
    for target in wiki_targets(text):
        target_note, ambiguous = resolve_link_target(target, by_key, by_base)
        if ambiguous or not target_note:
            return True
        if str(target_note["key"]) not in visible_keys:
            return True
    return False

def item_from_bullet(
    note: dict[str, object],
    section_name: str,
    bullet: str,
    index: int,
    by_key: dict[str, dict[str, object]],
    by_base: dict[str, list[dict[str, object]]],
    visible_keys: set[str],
) -> TimelineItem:
    source_key = str(note["key"])
    text = clean_timeline_text(bullet)
    links = filtered_targets(tuple(wiki_targets(bullet)), by_key, by_base, visible_keys)
    people = filtered_targets(
        linked_targets_by_prefix(bullet, "20 People/") + linked_targets_by_prefix(bullet, "25 Love/"),
        by_key,
        by_base,
        visible_keys,
    )
    projects = filtered_targets(
        linked_targets_by_prefix(bullet, "30 Work/Projects/") + linked_targets_by_prefix(bullet, "30 Work/Employers/"),
        by_key,
        by_base,
        visible_keys,
    )
    threads = infer_threads(text, note)
    date_start, date_end, date_label, date_precision, sort_key = infer_date(text)
    if sort_key == "unknown":
        sort_key = f"z:{source_key}:{index:03d}"
    return TimelineItem(
        id=timeline_item_id(source_key, text, index),
        title=item_title(text),
        text=text,
        source_note=f"{source_key}.md",
        source_section=section_name,
        date_label=date_label,
        date_start=date_start,
        date_end=date_end,
        date_precision=date_precision,
        sort_key=sort_key,
        life_period=infer_life_period(text, threads),
        threads=threads,
        people=people,
        projects=projects,
        places=infer_places(text),
        emotional_charge=infer_emotional_charge(text),
        pressure_level=infer_pressure_level(text),
        turning_point=infer_turning_point(text),
        confidence=as_string(note["frontmatter"].get("confidence"), "confirmed"),
        sensitivity=as_string(note["frontmatter"].get("sensitivity"), "normal"),
        links=links,
        sources=filtered_targets(source_targets(bullet, as_list(note["frontmatter"].get("sources"))), by_key, by_base, visible_keys),
    )

def timeline_items_from_note(
    note: dict[str, object],
    by_key: dict[str, dict[str, object]],
    by_base: dict[str, list[dict[str, object]]],
    visible_keys: set[str],
    skip_hidden_targets: bool,
) -> list[TimelineItem]:
    if note["is_template"] or note["is_source"] or not timeline_note(note):
        return []
    items = []
    body = str(note["body"])
    section_candidates = ("What We Know", "Events", "Milestones", "Timeline")
    index = 1
    for section_name in section_candidates:
        section_text = extract_section_text(body, section_name)
        if not section_text:
            continue
        for bullet in bullet_lines(section_text):
            if not bullet.strip():
                continue
            if skip_hidden_targets and hidden_or_unresolved_targets(bullet, by_key, by_base, visible_keys):
                continue
            items.append(item_from_bullet(note, section_name, bullet, index, by_key, by_base, visible_keys))
            index += 1
    if items:
        return items
    for bullet in bullet_lines(body):
        if skip_hidden_targets and hidden_or_unresolved_targets(bullet, by_key, by_base, visible_keys):
            continue
        items.append(item_from_bullet(note, "Body", bullet, index, by_key, by_base, visible_keys))
        index += 1
    return items

def item_sort_value(item: TimelineItem) -> tuple[int, str]:
    if item.sort_key.startswith("age:"):
        return (1, item.sort_key)
    if item.sort_key.startswith("grade:"):
        return (0, item.sort_key)
    if re.match(r"^\d{4}", item.sort_key):
        return (2, item.sort_key)
    return (9, item.sort_key)

def build_periods(items: list[TimelineItem]) -> list[TimelinePeriod]:
    grouped: dict[str, list[TimelineItem]] = defaultdict(list)
    for item in items:
        if item.life_period:
            grouped[item.life_period].append(item)
    periods = []
    for period_id, period_items in sorted(grouped.items()):
        dates = [item.date_start for item in period_items if item.date_start]
        thread_counts = Counter(thread for item in period_items for thread in item.threads)
        people_counts = Counter(person for item in period_items for person in item.people)
        project_counts = Counter(project for item in period_items for project in item.projects)
        pressure_counts = Counter(item.pressure_level for item in period_items)
        emotional_counts = Counter(item.emotional_charge for item in period_items)
        periods.append(
            TimelinePeriod(
                id=f"period:{period_id}",
                title=period_id.replace("-", " ").title(),
                start=min(dates) if dates else None,
                end=max(dates) if dates else None,
                date_precision="derived",
                theme=period_id.replace("-", " "),
                active_threads=tuple(thread for thread, _ in thread_counts.most_common(6)),
                main_people=tuple(person for person, _ in people_counts.most_common(6)),
                main_projects=tuple(project for project, _ in project_counts.most_common(6)),
                pressure_level=pressure_counts.most_common(1)[0][0] if pressure_counts else "unknown",
                emotional_charge=emotional_counts.most_common(1)[0][0] if emotional_counts else "unknown",
                source_note=", ".join(sorted({item.source_note for item in period_items})),
            )
        )
    return periods

def build_timeline(vault: Path, exclude_sensitive: bool = False) -> dict[str, object]:
    vault = require_vault(vault)
    notes = note_inventory(vault)
    by_key, by_base = link_indexes(notes)
    visible_keys = {
        str(note["key"])
        for note in notes
        if not (
            exclude_sensitive
            and as_string(note["frontmatter"].get("sensitivity"), "normal") in EXCLUDED_SENSITIVITIES
        )
    }
    items = []
    for note in notes:
        if str(note["key"]) not in visible_keys:
            continue
        items.extend(timeline_items_from_note(note, by_key, by_base, visible_keys, exclude_sensitive))
    deduped = {}
    for item in items:
        key = clean_bullet(item.text)
        deduped.setdefault(key, item)
    sorted_items = sorted(deduped.values(), key=item_sort_value)
    periods = build_periods(sorted_items)
    thread_counts = Counter(thread for item in sorted_items for thread in item.threads)
    precision_counts = Counter(item.date_precision for item in sorted_items)
    pressure_counts = Counter(item.pressure_level for item in sorted_items)
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "vault": str(vault),
        "counts": {
            "items": len(sorted_items),
            "periods": len(periods),
            "threads": len(thread_counts),
            "turning_points": sum(1 for item in sorted_items if item.turning_point),
            "unknown_dates": precision_counts.get("unknown", 0),
            "excluded_sensitive": len(notes) - len(visible_keys),
            "date_precision": dict(sorted(precision_counts.items())),
            "pressure_levels": dict(sorted(pressure_counts.items())),
        },
        "threads": [
            {"id": thread, "title": thread.replace("_", " ").title(), "item_count": count}
            for thread, count in sorted(thread_counts.items())
        ],
        "periods": [period.to_json() for period in periods],
        "items": [item.to_json() for item in sorted_items],
    }

def timeline_report(vault: Path, max_items: int, exclude_sensitive: bool = False) -> None:
    data = build_timeline(vault, exclude_sensitive=exclude_sensitive)
    print("# Life Timeline")
    print()
    print(f"Vault: {data['vault']}")
    print()
    print("## Summary")
    counts = data["counts"]
    print(f"- Timeline items: {counts['items']}")
    print(f"- Periods: {counts['periods']}")
    print(f"- Threads: {counts['threads']}")
    print(f"- Turning points: {counts['turning_points']}")
    print(f"- Unknown dates: {counts['unknown_dates']}")
    print(f"- Excluded sensitive notes: {counts['excluded_sensitive']}")
    print()
    print("## Threads")
    for thread in data["threads"]:
        print(f"- {thread['title']}: {thread['item_count']}")
    print()
    print("## Periods")
    for period in data["periods"]:
        dates = "unknown dates"
        if period["start"] or period["end"]:
            dates = f"{period['start'] or '?'} -> {period['end'] or '?'}"
        print(f"- {period['title']}: {dates} ({', '.join(period['active_threads']) or 'no threads'})")
    print()
    print("## Timeline Items")
    for item in data["items"][:max_items]:
        date = item["date_label"] or item["date_start"] or item["sort_key"]
        threads = ", ".join(item["threads"])
        print(f"- {date}: {item['text']}")
        print(f"  Threads: {threads}; pressure: {item['pressure_level']}; source: {item['source_note']}")
    if len(data["items"]) > max_items:
        print(f"- ... {len(data['items']) - max_items} more")

def timeline_export(vault: Path, out: Path | None, pretty: bool, exclude_sensitive: bool = False) -> None:
    data = build_timeline(vault, exclude_sensitive=exclude_sensitive)
    indent = 2 if pretty else None
    payload = json.dumps(data, ensure_ascii=False, indent=indent)
    if pretty:
        payload += "\n"
    if out:
        out = normalized_path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")
        print(out)
    else:
        print(payload)
