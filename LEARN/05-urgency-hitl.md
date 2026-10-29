# 05 - Sentiment, urgency rules and human-in-the-loop

## Sentiment (VADER)
VADER gives a score from -1 (very negative) to +1 (very positive) using a word list built for social media
(it understands "!!!", CAPS and many emoji). It does not understand sarcasm or Hinglish well. We use it only
as a small signal: a very negative ticket is never put in the low-priority P3 bucket.

## Urgency levels
- **P1** urgent: fraud or money taken, locked/hacked account, safety or health risk, legal threat, stuck right now.
- **P2** normal: needs action.
- **P3** low: feedback or "other" with no strong negative tone.

## Rules first (`src/firstreply/urgency.py`)
P1 is decided by written rules (regular expressions). Rules are predictable: you can read them, test them,
and explain to a manager exactly why a ticket became P1. Their weakness: they miss wording they do not know
("mera paisa kat gaya" has no English keyword).

## The AI may only RAISE urgency, never lower it
The LLM also says urgent yes/no. We combine them as "take the more urgent of the two":
- rules P2 + AI urgent -> P1 (AI caught what keywords missed)
- rules P1 + AI not urgent -> still P1 (AI cannot hide a fraud ticket)
Why: missing an urgent ticket is expensive and public; an extra P1 costs an agent 30 seconds. This makes the
AI a safety net, not a gatekeeper. Same idea as my FollowUp project.

> Hinglish: AI urgency badha sakta hai, kam nahi kar sakta - taaki fraud wala ticket kabhi chhup na jaaye.

## Human-in-the-loop (HITL)
The model **suggests**; a person **decides**. In the queue app (`app/queue_app.py`):
1. Tickets are sorted P1 first, then oldest first.
2. Each shows a suggested queue and a draft reply.
3. The agent approves, edits, or rejects. Nothing is sent without that click.

> Hinglish: Human-in-the-loop matlab AI sirf suggest karta hai, final faisla insaan ka hota hai.

## The approval log is an eval loop
Every decision is saved (SQLite): suggested queue, final queue, draft, final reply, seconds spent. From it:
- **approved unchanged %** = how often the draft was good enough as is,
- **queue kept %** = live routing accuracy, measured by real agents,
- **median seconds** = real handle time (this replaces the ROI assumptions in a pilot),
- **corrected labels** = new labelled tickets to add to the eval set.
So the system gets measured every day it is used, not only once in a notebook.
