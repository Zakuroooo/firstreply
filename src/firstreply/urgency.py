"""Urgency = rules first, then the AI may RAISE it, never lower it.

Why: missing an urgent ticket (fraud, safety, locked out) costs far more than reviewing a few extra ones,
so we want high recall. Rules are predictable and testable; the model catches what the keywords miss.
Levels: P1 urgent, P2 normal, P3 low.
"""
import re

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

LEVELS = ["P1", "P2", "P3"]  # index 0 is most urgent

# Each rule: name -> regex. Any match makes the ticket P1.
P1_RULES = {
    "fraud_or_money_taken": r"\b(fraud|scam|stolen|stole|unauthori[sz]ed|hack(ed|er)?|phishing|didn'?t (make|order|buy)|"
                            r"never (ordered|bought)|haven'?t (ordered|purchased)|taking (my )?(money|credits?)|"
                            r"money (out of|taken|disappear\w*|keeps disappearing)|deducted|charged twice|payment disappeared)",
    "locked_out": r"\b(locked( out)?|suspended|blocked access|cancel+ed my account|can'?t recover|account (was )?(closed|blocked))",
    "safety_or_health": r"\b(made me (ill|sick)|food poisoning|allerg\w*|injur\w*|unsafe|dangerous|fire(?!\s*(tv|stick|tablet|hd|\d))|smoke|"
                        r"plastic in|glass in|hospital)",
    "legal_threat": r"\b(lawyer|solicitor|sue|legal action|letter before action|trading standards|small claims)",
    "stuck_right_now": r"\b(bank(s)? (is |are )?about to close|waiting (at|by) the door|right now|stranded)",
}
# Each pattern starts with \b; the closing \b below stops "fire" matching "Firefox" or "sue" matching "suede".
_compiled = {name: re.compile(rf"{rx}\b", re.IGNORECASE) for name, rx in P1_RULES.items()}
_vader = SentimentIntensityAnalyzer()

NON_ACTION_QUEUES = {"complaint_feedback", "other"}


def sentiment(text):
    """VADER compound score from -1 (very negative) to +1 (very positive)."""
    return _vader.polarity_scores(text or "")["compound"]


def rule_level(text, queue):
    """Return (level, reasons) from rules only."""
    reasons = [name for name, rx in _compiled.items() if rx.search(text or "")]
    if reasons:
        return "P1", reasons
    score = sentiment(text)
    if queue in NON_ACTION_QUEUES and score >= -0.6:
        return "P3", ["no_action_needed"]
    return "P2", ["very_negative"] if score < -0.6 else ["default"]


def raise_only(rule, ai):
    """Combine: the more urgent of the two. The AI can move P2 -> P1, never P1 -> P2."""
    return rule if LEVELS.index(rule) <= LEVELS.index(ai) else ai


def final_level(text, queue, ai_urgent):
    level, reasons = rule_level(text, queue)
    ai = "P1" if ai_urgent else "P3"  # "not urgent" from the AI carries no power to lower anything
    combined = raise_only(level, ai)
    if combined != level:
        reasons = reasons + ["ai_raised"]
    return combined, reasons
