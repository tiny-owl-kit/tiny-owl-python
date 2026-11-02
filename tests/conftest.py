from __future__ import annotations

import pytest
from fakes import FakeClient


@pytest.fixture
def fake_client() -> FakeClient:
    return FakeClient()
