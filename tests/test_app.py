"""Smoke test: the queue app loads, shows a P1 ticket first, and logs an approval."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from firstreply import db

APP = str(Path(__file__).resolve().parents[1] / "app" / "queue_app.py")
pytestmark = pytest.mark.skipif(not (db.ROOT / "outputs" / "eval_predictions.csv").exists(),
                                reason="needs outputs/eval_predictions.csv (make evals)")


def test_queue_app_approve_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("FIRSTREPLY_DB", str(tmp_path / "a.db"))
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    waiting, p1, handled = (int(m.value) for m in at.metric)
    assert handled == 0 and p1 > 0
    assert at.subheader[0].value.startswith(":red[P1]")   # urgent tickets come first
    at.button[0].click().run()                             # approve the draft as is
    assert [int(m.value) for m in at.metric] == [waiting - 1, p1 - 1, 1]
