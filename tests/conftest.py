from __future__ import annotations

from datetime import date

import pytest
from agentkit import build_deps, build_runtime
from agentkit.runtime import Runtime, repositories

from calliope.agents.deps import Deps
from calliope.config import Settings
from calliope.db.repos import Repositories


@pytest.fixture
def runtime(tmp_path) -> Runtime:
    settings = Settings(owner_id="owner", agent_home=tmp_path)
    return build_runtime(settings, repos_factory=Repositories)


@pytest.fixture
def repos(runtime: Runtime):
    with repositories(runtime) as opened:
        yield opened


@pytest.fixture
def deps(runtime: Runtime, repos: Repositories) -> Deps:
    deps = build_deps(runtime, repos)
    return Deps(
        settings=deps.settings, repos=deps.repos, model=deps.model, clock=deps.clock
    )


@pytest.fixture
def sample_entries(repos: Repositories) -> None:
    from calliope.services import journal as svc

    deps = Deps(settings=Settings(owner_id="owner"), repos=repos)
    svc.record_entry(deps, "First day of journaling.", entry_date=date(2026, 1, 1), mood=4)
    svc.record_entry(deps, "A quiet day, mostly reading.", entry_date=date(2026, 1, 2), mood=3)
