"""Structured tool/agent I/O models."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class Correction(BaseModel):
    original: str
    corrected: str
    explanation: str
    category: str  # grammar | spelling | word_choice | punctuation | style


class VocabularyItem(BaseModel):
    word: str
    meaning: str
    example: str


class WritingCritique(BaseModel):
    """Structured ESL feedback for one piece of writing."""

    summary: str = Field(description="One or two sentences of encouraging, specific feedback.")
    corrected_text: str = Field(description="The full text with corrections applied.")
    corrections: list[Correction] = Field(default_factory=list)
    vocabulary: list[VocabularyItem] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    estimated_level: str = Field(default="", description="Estimated CEFR level, e.g. B1.")


class JournalEntryRecord(BaseModel):
    id: int
    entry_date: date
    title: str = ""
    words: int = 0
    mood: int | None = None
    tags: list[str] = Field(default_factory=list)
    excerpt: str = ""


class JournalStats(BaseModel):
    total_entries: int = 0
    current_streak: int = 0
    total_words: int = 0
    words_this_week: int = 0
    avg_mood: float | None = None
    last_entry_date: date | None = None
    daily_word_goal: int = 150
