import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "emails"


@pytest.fixture
def discovery_emails() -> list[dict]:
    return _load_fixtures("discovery")


@pytest.fixture
def followup_emails() -> list[dict]:
    return _load_fixtures("followup")


@pytest.fixture
def poc_emails() -> list[dict]:
    return _load_fixtures("poc")


@pytest.fixture
def proposal_emails() -> list[dict]:
    return _load_fixtures("proposal")


def _load_fixtures(phase: str) -> list[dict]:
    phase_dir = FIXTURES_DIR / phase
    if not phase_dir.exists():
        return []
    fixtures = []
    for f in sorted(phase_dir.glob("*.json")):
        fixtures.append(json.loads(f.read_text()))
    return fixtures
