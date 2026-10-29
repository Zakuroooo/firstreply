"""Human-in-the-loop queue: order tickets, attach a suggestion, and log what the agent decided.

Nothing is sent without a person. The agent approves, edits or rejects each suggestion, and every
decision is stored in SQLite. Those decisions are the live eval loop: how often the suggested queue
was kept, how often the draft was sent unchanged, and which corrected labels to add to the eval set.
"""
import sqlite3
from datetime import datetime, timezone

import pandas as pd

from firstreply import urgency
from firstreply.labels import QUEUES

ACTIONS = ("approved", "edited", "rejected")

# Safe fallback drafts when no LLM is available. Same rules as the LLM prompt: no promises, no passwords.
TEMPLATES = {
    "delivery": "Sorry your order hasn't arrived as expected. Please send us a DM with your order number and we'll check where it is.",
    "order_change": "Happy to help with your order. Please DM us the order number and the change you need, and we'll see what's possible.",
    "refund_return": "Sorry about the problem with your item. Please DM us your order number and a short description, and we'll look at the options.",
    "billing_payment": "Sorry for the trouble with this payment. Please DM us the date and amount (never your full card number) so we can look into it.",
    "account": "Sorry you're having trouble with your account. Please DM us the email on the account - never your password - and we'll help.",
    "complaint_feedback": "Thank you for telling us, and sorry this wasn't a good experience. We've passed your feedback to the team.",
    "talk_to_human": "Thanks for reaching out - a member of our team will reply to your DM as soon as possible.",
    "other": "Thanks for getting in touch. Could you DM us a few more details so we can point you to the right team?",
}


def template_draft(queue):
    return TEMPLATES.get(queue, TEMPLATES["other"])


def build_queue(tickets, suggested_queue, sla_minutes=60):
    """tickets: DataFrame with eval_id, brand, created_at, clean_text, frt_minutes.
    suggested_queue: one model queue per row. Returns the queue sorted P1 first, then oldest first."""
    q = tickets.copy().reset_index(drop=True)
    q["suggested_queue"] = list(suggested_queue)
    levels = [urgency.rule_level(t, s) for t, s in zip(q.clean_text, q.suggested_queue)]
    q["level"] = [lvl for lvl, _ in levels]
    q["reasons"] = [", ".join(r) for _, r in levels]
    q["sentiment"] = q.clean_text.map(urgency.sentiment).round(2)
    q["breached_in_reality"] = q.frt_minutes > sla_minutes
    q["_rank"] = q.level.map(urgency.LEVELS.index)
    return q.sort_values(["_rank", "created_at"]).drop(columns="_rank").reset_index(drop=True)


class ApprovalLog:
    """SQLite log of agent decisions. One row per decision."""

    def __init__(self, path):
        self.con = sqlite3.connect(str(path), check_same_thread=False)
        self.con.execute("""CREATE TABLE IF NOT EXISTS decisions (
            ts TEXT, agent TEXT, eval_id INTEGER, suggested_queue TEXT, final_queue TEXT,
            suggested_draft TEXT, final_reply TEXT, action TEXT, seconds REAL)""")
        self.con.commit()

    def log(self, agent, eval_id, suggested_queue, final_queue, suggested_draft, final_reply, seconds, action=None):
        """Store one decision. action is worked out from what changed unless the agent rejected the draft."""
        if final_queue not in QUEUES:
            raise ValueError(f"unknown queue: {final_queue}")
        if action is not None and action not in ACTIONS:
            raise ValueError(f"unknown action: {action}")
        if action is None:
            if not final_reply.strip():
                action = "rejected"
            elif final_reply.strip() == suggested_draft.strip() and final_queue == suggested_queue:
                action = "approved"
            else:
                action = "edited"
        self.con.execute("INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?,?)", (
            datetime.now(timezone.utc).isoformat(timespec="seconds"), agent, int(eval_id), suggested_queue,
            final_queue, suggested_draft, final_reply, action, float(seconds)))
        self.con.commit()
        return action

    def decisions(self):
        return pd.read_sql("SELECT * FROM decisions", self.con)

    def done_ids(self):
        return {r[0] for r in self.con.execute("SELECT DISTINCT eval_id FROM decisions")}


def loop_stats(decisions):
    """The eval loop: what agents kept, changed and threw away."""
    if decisions.empty:
        return {"decisions": 0}
    d = decisions
    return {
        "decisions": len(d),
        "approved_unchanged_pct": round(100 * (d.action == "approved").mean(), 1),
        "edited_pct": round(100 * (d.action == "edited").mean(), 1),
        "rejected_pct": round(100 * (d.action == "rejected").mean(), 1),
        "queue_kept_pct": round(100 * (d.suggested_queue == d.final_queue).mean(), 1),
        "median_seconds": round(float(d.seconds.median()), 1),
    }


def corrected_labels(decisions):
    """Agent-chosen queues, ready to be reviewed and added to the eval set as new labelled examples."""
    return decisions.sort_values("ts").groupby("eval_id").tail(1)[["eval_id", "suggested_queue", "final_queue"]]
