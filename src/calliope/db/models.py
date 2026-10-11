"""Domain tables for Calliope (journal entries and ESL writing feedback)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class JournalEntry(SQLModel, table=True):
    __tablename__ = "journal_entries"
    __table_args__ = (Index("ix_journal_owner_date", "owner_id", "entry_date"),)

    id: int | None = Field(default=None, primary_key=True)
    owner_id: str = Field(index=True)
    entry_date: date = Field(default_factory=date.today)
    title: str = ""
    body: str = ""
    mood: int | None = None  # 1..5
    tags: str = "[]"  # JSON list of strings
    word_count: int = 0
    created_at: datetime = Field(default_factory=_utcnow)


class WritingSubmission(SQLModel, table=True):
    __tablename__ = "writing_submissions"

    id: int | None = Field(default=None, primary_key=True)
    owner_id: str = Field(index=True)
    text: str = ""
    level: str = "B1"
    word_count: int = 0
    created_at: datetime = Field(default_factory=_utcnow)


class Critique(SQLModel, table=True):
    __tablename__ = "writing_critiques"

    id: int | None = Field(default=None, primary_key=True)
    submission_id: int = Field(index=True, foreign_key="writing_submissions.id")
    summary: str = ""
    corrected_text: str = ""
    corrections: str = "[]"  # JSON list
    vocabulary: str = "[]"  # JSON list
    next_steps: str = "[]"  # JSON list
    estimated_level: str = ""
    created_at: datetime = Field(default_factory=_utcnow)
