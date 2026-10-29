# PRD - FirstReply

## Problem
Support teams on social channels miss first-response targets at busy hours. Agents spend the first minutes of
every ticket reading it, picking a queue and typing a similar first reply. Managers staff by gut feel and do
not know which hours breach, or whether an AI triage tool would really save time.

## Users
- **Support agent**: wants the right tickets first and a decent draft to start from, without losing control.
- **Team lead / ops manager**: wants breach rate by hour, a staffing plan, and proof before buying an AI tool.
- **Client sponsor** (consulting view): wants hours saved, risks, and a safe rollout plan.

## Goals
1. Measure today: first-response time (median, p90), breach rate against a stated SLA, backlog, by brand/hour/weekday.
2. Plan staff: forecast next week's hourly volume and turn it into agents per hour.
3. Compare triage options honestly: a classical model vs LLMs on the same real tickets, with accuracy,
   macro-F1, cost per 1,000 tickets, latency and failure examples.
4. Keep humans in charge: urgent first, suggestions only, every decision logged.
5. Turn it into a business case: hours saved with every assumption shown and a range.

## Non-goals
- Auto-sending replies. Resolving tickets end to end. Real customer data. A production deployment.

## Requirements
| # | Requirement | Where |
|---|---|---|
| R1 | FRT median/p90 and breach % by brand, hour, weekday | `sql/02-03`, `outputs/sla_*.csv` |
| R2 | Hourly backlog | `sql/04`, `outputs/backlog_hourly.csv` |
| R3 | Forecast baseline scored by WAPE; staffing per hour | `analytics.py`, `outputs/staffing_plan.csv` |
| R4 | Same held-out set for every triage model; accuracy, macro-F1 with 95% CIs, cost/1k, latency p50/p95, failures | `evals.py`, `outputs/eval_*.csv` |
| R5 | Urgency rules; AI may only raise; edge cases tested (empty, emoji, Hinglish, long, HTML) | `urgency.py`, `tests/` |
| R6 | Queue app: P1 first, suggested queue + draft, approve/edit/reject, decisions logged | `app/queue_app.py`, `hitl.py` |
| R7 | ROI in agent-hours, low/base/high, sensitivity | `roi.py`, `docs/MEMO.md` |
| R8 | One command reproduces every number; CI runs tests | `Makefile`, `.github/workflows/ci.yml` |

## Success measures (for a real pilot, not this repo)
- P1 recall on a fresh sample >= the rules-only baseline (AI can only add).
- Suggested queue kept by agents >= the break-even accuracy in the ROI model, with margin.
- Median handle seconds per ticket lower than a matched control shift.
- Breach rate at the target SLA down, with no rise in reopened or escalated tickets.

## Risks
See `docs/MEMO.md` (risks and rollout).
