import pytest

import torke


@pytest.fixture(autouse=True)
def warning_gate_off(monkeypatch):
    """The other tests aren't about the warning gate, so it's off for them. test_gate.py turns it on."""
    monkeypatch.setattr(torke, "REQUIRE_WARNING", False)
