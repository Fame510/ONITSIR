"""Shared fixtures."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from onitsir.roster import Roster  # noqa: E402

DATA = ROOT / "data" / "roster.json"


@pytest.fixture(scope="session")
def roster() -> Roster:
    return Roster.load(DATA)
