from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from agentkit.db.repositories import Repositories as _BaseRepositories
from sqlalchemy import func
from sqlmodel import Session, select

from calliope.db.models import Critique, JournalEntry, WritingSubmission


class JournalRepo:
    def __init__(self, session: Session, owner_id: str) -> None:
        self.session = session
        self.owner_id = owner_id

    def add(
        self,
        *,
        body: str,
        entry_date: date,
        title: str = "",
        mood: int | None = None,
        tags: str = "[]",
        word_count: int = 0,
    ) -> JournalEntry:
        entry = JournalEntry(
            owner_id=self.owner_id,
            entry_date=entry_date,
            title=title,
            body=body,
            mood=mood,
            tags=tags,
            word_count=word_count,
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def list(self, limit: int = 20) -> list[JournalEntry]:
        return list(
            self.session.exec(
                select(JournalEntry)
                .where(JournalEntry.owner_id == self.owner_id)
                .order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc())
                .limit(limit)
            ).all()
        )

    def dates(self) -> list[date]:
        rows = self.session.exec(
            select(JournalEntry.entry_date)
            .where(JournalEntry.owner_id == self.owner_id)
            .order_by(JournalEntry.entry_date.desc())
        ).all()
        return list(rows)

    def count(self) -> int:
        return int(
            self.session.exec(
                select(func.count()).select_from(JournalEntry).where(
                    JournalEntry.owner_id == self.owner_id
                )
            ).one()
        )

    def total_words(self) -> int:
        return int(
            self.session.exec(
                select(func.coalesce(func.sum(JournalEntry.word_count), 0)).where(
                    JournalEntry.owner_id == self.owner_id
                )
            ).one()
        )

    def words_between(self, start: date, end: date) -> int:
        return int(
            self.session.exec(
                select(func.coalesce(func.sum(JournalEntry.word_count), 0)).where(
                    JournalEntry.owner_id == self.owner_id,
                    JournalEntry.entry_date >= start,
                    JournalEntry.entry_date <= end,
                )
            ).one()
        )

    def mood_average(self) -> float | None:
        value = self.session.exec(
            select(func.avg(JournalEntry.mood)).where(
                JournalEntry.owner_id == self.owner_id, JournalEntry.mood.is_not(None)
            )
        ).one()
        return float(value) if value is not None else None


class WritingRepo:
    def __init__(self, session: Session, owner_id: str) -> None:
        self.session = session
        self.owner_id = owner_id

    def add_submission(self, text: str, level: str, word_count: int) -> WritingSubmission:
        submission = WritingSubmission(
            owner_id=self.owner_id, text=text, level=level, word_count=word_count
        )
        self.session.add(submission)
        self.session.flush()
        return submission

    def add_critique(
        self,
        submission_id: int,
        *,
        summary: str,
        corrected_text: str,
        corrections: str,
        vocabulary: str,
        next_steps: str,
        estimated_level: str,
    ) -> Critique:
        critique = Critique(
            submission_id=submission_id,
            summary=summary,
            corrected_text=corrected_text,
            corrections=corrections,
            vocabulary=vocabulary,
            next_steps=next_steps,
            estimated_level=estimated_level,
        )
        self.session.add(critique)
        self.session.flush()
        return critique

    def recent_submissions(self, limit: int = 5) -> list[WritingSubmission]:
        return list(
            self.session.exec(
                select(WritingSubmission)
                .where(WritingSubmission.owner_id == self.owner_id)
                .order_by(WritingSubmission.created_at.desc())
                .limit(limit)
            ).all()
        )


@dataclass
class Repositories(_BaseRepositories):
    def __post_init__(self) -> None:
        super().__post_init__()
        self.journal = JournalRepo(self.session, self.owner_id)
        self.writing = WritingRepo(self.session, self.owner_id)
