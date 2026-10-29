import pandas as pd
import pytest

from firstreply import hitl


def tickets():
    return pd.DataFrame({
        "eval_id": [1, 2, 3],
        "brand": ["A", "A", "A"],
        "created_at": ["2017-10-10 10:00", "2017-10-10 09:00", "2017-10-10 11:00"],
        "clean_text": ["love the new app", "parcel is late", "someone hacked my account"],
        "frt_minutes": [10.0, 90.0, None],
    })


def test_queue_puts_p1_first_then_oldest():
    q = hitl.build_queue(tickets(), ["complaint_feedback", "delivery", "account"])
    assert q.eval_id.tolist() == [3, 2, 1]
    assert q.level.tolist() == ["P1", "P2", "P3"]
    assert q.breached_in_reality.tolist() == [False, True, False]


def test_every_queue_has_a_safe_template():
    for queue in hitl.TEMPLATES:
        draft = hitl.template_draft(queue)
        assert "password" not in draft.lower() or "never your password" in draft.lower()
        assert "refund" not in draft.lower() or "options" in draft.lower()  # no refund promises
    assert hitl.template_draft("unknown") == hitl.TEMPLATES["other"]


def test_log_actions_and_stats(tmp_path):
    log = hitl.ApprovalLog(tmp_path / "a.db")
    assert log.log("x", 1, "delivery", "delivery", "draft", "draft", 20) == "approved"
    assert log.log("x", 2, "delivery", "refund_return", "draft", "draft", 30) == "edited"
    assert log.log("x", 3, "delivery", "delivery", "draft", "new text", 40) == "edited"
    assert log.log("x", 4, "delivery", "delivery", "draft", "", 10, action="rejected") == "rejected"
    s = hitl.loop_stats(log.decisions())
    assert s["decisions"] == 4 and s["approved_unchanged_pct"] == 25.0 and s["queue_kept_pct"] == 75.0
    assert log.done_ids() == {1, 2, 3, 4}
    fixed = hitl.corrected_labels(log.decisions())
    assert fixed.set_index("eval_id").loc[2, "final_queue"] == "refund_return"


def test_log_rejects_unknown_queue(tmp_path):
    with pytest.raises(ValueError):
        hitl.ApprovalLog(tmp_path / "a.db").log("x", 1, "delivery", "nope", "d", "d", 1)


def test_empty_stats():
    assert hitl.loop_stats(pd.DataFrame()) == {"decisions": 0}
