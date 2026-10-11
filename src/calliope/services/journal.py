"""Journal + writing-coach operations used by agent tools and the CLI."""

from __future__ import annotations

import json
from datetime import date, timedelta

from calliope.agents.deps import Deps
from calliope.agents.schemas import JournalEntryRecord, JournalStats, WritingCritique
from calliope.db.models import Critique, JournalEntry, WritingSubmission


def word_count(text: str) -> int:
    return len([word for word in (text or "").split() if word.strip()])


def parse_date(value: str | date | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    from datetime import datetime

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognized date: {value!r}")


def normalize_tags(tags: list[str] | str | None) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, str):
        return [tag.strip() for tag in tags.split(",") if tag.strip()]
    return [str(tag).strip() for tag in tags if str(tag).strip()]


def record_entry(
    deps: Deps,
    body: str,
    *,
    title: str | None = None,
    mood: int | None = None,
    tags: list[str] | str | None = None,
    entry_date: str | date | None = None,
) -> JournalEntry:
    """Record one journal entry (audited)."""
    when = parse_date(entry_date)
    entry = deps.repos.journal.add(
        body=body,
        entry_date=when,
        title=title or "",
        mood=mood,
        tags=json.dumps(normalize_tags(tags)),
        word_count=word_count(body),
    )
    deps.repos.audit.append(
        "journal.entry",
        target=f"journal:{entry.id}",
        detail={"date": when.isoformat(), "words": entry.word_count},
        actor=deps.owner_id,
    )
    return entry


def list_entries(deps: Deps, limit: int = 10) -> list[JournalEntry]:
    return deps.repos.journal.list(limit)


def _current_streak(dates: list[date], today: date) -> int:
    unique = sorted(set(dates), reverse=True)
    if not unique:
        return 0
    if unique[0] == today:
        cursor = today
    elif unique[0] == today - timedelta(days=1):
        cursor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    present = set(unique)
    while cursor in present:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def journal_stats(deps: Deps, *, today: date | None = None) -> JournalStats:
    today = today or date.today()
    journal = deps.repos.journal
    dates = journal.dates()
    week_start = today - timedelta(days=today.weekday())
    return JournalStats(
        total_entries=journal.count(),
        current_streak=_current_streak(dates, today),
        total_words=journal.total_words(),
        words_this_week=journal.words_between(week_start, today),
        avg_mood=journal.mood_average(),
        last_entry_date=dates[0] if dates else None,
        daily_word_goal=deps.settings.daily_word_goal,
    )


def to_record(entry: JournalEntry) -> JournalEntryRecord:
    excerpt = (entry.body or "").strip().replace("\n", " ")
    if len(excerpt) > 120:
        excerpt = excerpt[:117] + "..."
    return JournalEntryRecord(
        id=entry.id or 0,
        entry_date=entry.entry_date,
        title=entry.title,
        words=entry.word_count,
        mood=entry.mood,
        tags=json.loads(entry.tags or "[]"),
        excerpt=excerpt,
    )


def start_submission(deps: Deps, text: str, level: str | None = None) -> WritingSubmission:
    return deps.repos.writing.add_submission(
        text=text, level=level or deps.settings.default_esl_level, word_count=word_count(text)
    )


def save_critique(deps: Deps, submission_id: int, critique: WritingCritique) -> Critique:
    saved = deps.repos.writing.add_critique(
        submission_id,
        summary=critique.summary,
        corrected_text=critique.corrected_text,
        corrections=json.dumps([c.model_dump() for c in critique.corrections]),
        vocabulary=json.dumps([v.model_dump() for v in critique.vocabulary]),
        next_steps=json.dumps(critique.next_steps),
        estimated_level=critique.estimated_level,
    )
    deps.repos.audit.append(
        "writing.critique",
        target=f"submission:{submission_id}",
        detail={"corrections": len(critique.corrections)},
        actor=deps.owner_id,
    )
    return saved


def format_critique(critique: WritingCritique) -> str:
    lines = [critique.summary, ""]
    if critique.corrected_text.strip():
        lines += ["**Corrected version**", "", critique.corrected_text, ""]
    if critique.corrections:
        lines.append("**What I changed**")
        for change in critique.corrections:
            lines.append(f"- {change.original} → {change.corrected} — {change.explanation} ({change.category})")
        lines.append("")
    if critique.vocabulary:
        lines.append("**Words to try**")
        for item in critique.vocabulary:
            lines.append(f"- {item.word}: {item.meaning} — e.g. {item.example}")
        lines.append("")
    if critique.next_steps:
        lines.append("**Next steps**")
        lines += [f"- {step}" for step in critique.next_steps]
        lines.append("")
    if critique.estimated_level:
        lines.append(f"Estimated level: {critique.estimated_level}")
    return "\n".join(lines).strip()
