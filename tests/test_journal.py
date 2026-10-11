from __future__ import annotations

from datetime import date, timedelta

from calliope.agents.schemas import Correction, VocabularyItem, WritingCritique
from calliope.services import journal as svc


def test_word_count():
    assert svc.word_count("hello there world") == 3
    assert svc.word_count("") == 0
    assert svc.word_count("  spaced   out  ") == 2


def test_record_and_list(repos):
    from calliope.agents.deps import Deps
    from calliope.config import Settings

    deps = Deps(settings=Settings(owner_id="owner"), repos=repos)
    entry = svc.record_entry(deps, "Today I wrote a lot of words in English.", title="Day 1", mood=4, tags=["esl"])
    assert entry.word_count == 9
    records = [svc.to_record(e) for e in svc.list_entries(deps, 10)]
    assert records[0].title == "Day 1"
    assert records[0].tags == ["esl"]
    assert records[0].mood == 4


def test_streak_and_stats(repos):
    from calliope.agents.deps import Deps
    from calliope.config import Settings

    deps = Deps(settings=Settings(owner_id="owner", daily_word_goal=100), repos=repos)
    today = date(2026, 3, 10)
    svc.record_entry(deps, "one two three", entry_date=today, mood=5)
    svc.record_entry(deps, "four five", entry_date=today - timedelta(days=1), mood=3)
    svc.record_entry(deps, "six", entry_date=today - timedelta(days=2), mood=4)
    stats = svc.journal_stats(deps, today=today)
    assert stats.total_entries == 3
    assert stats.current_streak == 3
    assert stats.total_words == 6
    assert stats.daily_word_goal == 100
    assert stats.last_entry_date == today
    assert stats.avg_mood == 4.0


def test_streak_breaks_on_gap(repos):
    from calliope.agents.deps import Deps
    from calliope.config import Settings

    deps = Deps(settings=Settings(owner_id="owner"), repos=repos)
    today = date(2026, 3, 10)
    svc.record_entry(deps, "old", entry_date=today - timedelta(days=5))
    assert svc.journal_stats(deps, today=today).current_streak == 0


def test_critique_roundtrip(repos):
    from calliope.agents.deps import Deps
    from calliope.config import Settings

    deps = Deps(settings=Settings(owner_id="owner"), repos=repos)
    submission = svc.start_submission(deps, "I goes to school yesterday.", level="A2")
    critique = WritingCritique(
        summary="Nice effort — mostly tense and verb agreement.",
        corrected_text="I went to school yesterday.",
        corrections=[
            Correction(original="goes", corrected="went", explanation="Past tense.", category="grammar")
        ],
        vocabulary=[VocabularyItem(word="yesterday", meaning="the day before today", example="I went yesterday.")],
        next_steps=["Practise the past simple."],
        estimated_level="A2",
    )
    saved = svc.save_critique(deps, submission.id, critique)
    assert saved.summary.startswith("Nice effort")
    text = svc.format_critique(critique)
    assert "Corrected version" in text
    assert "What I changed" in text
    assert "Words to try" in text
    assert "Estimated level: A2" in text


def test_audit_records_writes(repos):
    from calliope.agents.deps import Deps
    from calliope.config import Settings

    deps = Deps(settings=Settings(owner_id="owner"), repos=repos)
    svc.record_entry(deps, "hello world")
    assert repos.audit.verify() is True
    assert repos.audit.entries()[0].action == "journal.entry"
