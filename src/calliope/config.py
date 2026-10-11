"""Calliope settings — agentkit's AgentSettings plus journaling/ESL options."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from agentkit.config import AgentSettings


class Settings(AgentSettings):
    agent_name: str = "calliope"

    # journaling / ESL
    default_esl_level: str = "B1"  # CEFR: A1..C2
    daily_word_goal: int = 150

    @property
    def db_path(self) -> Path:
        return self.home / "calliope.db"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings"]
