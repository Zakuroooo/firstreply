import pandas as pd

from firstreply import evals
from firstreply.labels import BITEXT_TO_QUEUE, QUEUES


def test_macro_f1_perfect_and_wrong():
    assert evals.macro_f1(["delivery", "account"], ["delivery", "account"]) > 0
    assert evals.macro_f1(["delivery"], ["account"]) == 0


def test_bootstrap_ci_contains_point_estimate():
    y = ["delivery"] * 70 + ["account"] * 30
    p = ["delivery"] * 60 + ["account"] * 40
    lo, hi = evals.bootstrap_ci(y, p, lambda a, b: (a == b).mean())
    assert lo <= 90.0 <= hi


def test_urgency_stats_rules_only():
    s = evals.urgency_stats(["my card was stolen", "parcel late"], ["billing_payment", "delivery"], [True, False])
    assert s["rules_only"]["recall_pct"] == 100.0 and "rules_plus_ai_raise" not in s


def test_failures_lists_only_wrong_answers():
    test = pd.DataFrame({"eval_id": [1, 2], "clean_text": ["a", "b"], "label": ["delivery", "account"]})
    f = evals.failures(test, {"m": ["delivery", "other"]})
    assert f.eval_id.tolist() == [2] and f.predicted.tolist() == ["other"]


def test_bitext_maps_only_to_known_queues():
    assert set(BITEXT_TO_QUEUE.values()) <= set(QUEUES) - {"other"}
