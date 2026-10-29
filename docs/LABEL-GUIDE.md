# Label guide

The rules used for `evalset/labels.csv` and `evalset/urgency_holdout.csv`. Labels were set before any model
output was looked at. The same queue definitions are in `src/firstreply/labels.py` and in the LLM prompt
(`src/firstreply/llm.py`), so humans and models are judged against one rule set.

## One queue per ticket - pick the team that must act
| Queue | Use when |
|---|---|
| delivery | where is my order, late / missed / wrong-address delivery, courier problems, delivery options |
| order_change | place, change or cancel an order; change the shipping address |
| refund_return | refund, return, exchange; damaged / wrong / faulty / missing / expired item the customer wants fixed |
| billing_payment | payment fails, unknown or wrong charge, invoice, discount, price, fees, payment methods, withdrawing funds |
| account | login, password, locked / hacked / suspended, account details, SIM, plans and subscriptions |
| complaint_feedback | venting, praise or a suggestion with nothing specific for an agent to fix |
| talk_to_human | "check my DM", how do I contact you, can't get through, a vague "please help" |
| other | app or site bugs, network, streaming, stock or product questions, off-topic, can't tell |

Tie-breakers:
1. If a specific fix is asked for, choose that team over complaint_feedback, even if the tone is angry.
2. "I sent you a DM" with no topic -> talk_to_human. With a clear topic -> that topic's queue.
3. Non-English: label by meaning if it can be understood; otherwise other.

## Urgent (yes/no)
Yes when: fraud or money taken without consent, safety or health risk, locked or hacked account, a legal threat,
or the customer is stuck right now (e.g. waiting at the door, bank closing). Anger alone is **not** urgent.

## Known weaknesses
- One labeller, no second opinion, so there is no inter-annotator agreement number. A second person labelling
  50 tickets and measuring agreement is the next step.
- Small classes: order_change has 5 test tickets and 0 dev tickets. Per-class scores for it are noise.
- 23 of 400 eval tickets and 10 of 150 hold-out tickets are urgent, so urgency recall moves in big steps.
