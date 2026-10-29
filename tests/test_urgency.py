import pytest

from firstreply import urgency
from firstreply.urgency import LEVELS, final_level, raise_only, rule_level


@pytest.mark.parametrize("text,reason", [
    ("Someone hacked my account and changed the email", "fraud_or_money_taken"),
    ("I never ordered this, why was I charged twice?", "fraud_or_money_taken"),
    ("my account is locked and I can't recover it", "locked_out"),
    ("the chicken made me ill, food poisoning", "safety_or_health"),
    ("I will be contacting trading standards", "legal_threat"),
    ("driver is not here, I'm waiting by the door right now", "stuck_right_now"),
])
def test_p1_rules(text, reason):
    level, reasons = rule_level(text, "other")
    assert level == "P1" and reason in reasons


def test_empty_and_none_do_not_crash():
    assert rule_level("", "other")[0] == "P3"
    assert rule_level(None, "delivery")[0] == "P2"
    assert urgency.sentiment(None) == 0.0


def test_emoji_only():
    level, _ = rule_level("😡😡😡", "complaint_feedback")
    assert level in LEVELS


def test_hinglish_without_keywords_is_not_p1_by_rules_but_ai_can_raise():
    text = "bhai mera paisa kat gaya aur order bhi nahi aaya, jaldi karo"
    assert rule_level(text, "billing_payment")[0] != "P1"
    level, reasons = final_level(text, "billing_payment", ai_urgent=True)
    assert level == "P1" and "ai_raised" in reasons


def test_very_long_text():
    text = "where is my parcel " * 3000 + " it was stolen"
    assert rule_level(text, "delivery")[0] == "P1"


def test_html_text():
    assert rule_level("<b>FRAUD</b> on my card", "billing_payment")[0] == "P1"


def test_word_boundaries_avoid_false_hits():
    # "fire" rule must not fire on "Firefox"; "sue" not on "issue"
    assert rule_level("Firefox has an issue loading the page", "other")[0] != "P1"


def test_ai_can_raise_never_lower():
    for rule in LEVELS:
        for ai in LEVELS:
            out = raise_only(rule, ai)
            assert LEVELS.index(out) <= LEVELS.index(rule)  # never less urgent than the rule
    level, _ = final_level("someone stole my card details", "billing_payment", ai_urgent=False)
    assert level == "P1"


def test_ai_not_urgent_keeps_rule_level():
    text = "parcel is late again"
    assert final_level(text, "delivery", ai_urgent=False)[0] == rule_level(text, "delivery")[0]


@pytest.mark.parametrize("text", ["my Fire Stick won't connect", "Fire TV keeps buffering", "nice suede jacket"])
def test_product_names_are_not_safety_issues(text):
    assert rule_level(text, "other")[0] != "P1"


def test_real_fire_is_still_p1():
    assert rule_level("the charger caught fire", "refund_return")[0] == "P1"
