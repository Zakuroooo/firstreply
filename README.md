# FirstReply

**Support operations intelligence**: measure first-response SLAs on real tickets, compare AI triage options
honestly (accuracy, cost, latency), keep a human approving every reply, and turn it into an ROI case a support
leader can act on.

- Real timestamps: 724,846 tickets to 108 brands (Twitter, 2017) -> first-response time, breach rate, backlog,
  forecast and staffing.
- Same exam for every model: 300 real tweets labelled with a written guide (AI-assisted; blind human re-check pending, `scripts/recheck.py`); classical TF-IDF + logistic regression vs two LLMs.
- Urgency: rules decide, the AI may only **raise** urgency, never lower it.
- Agent queue app: urgent first, suggested queue + draft, approve / edit / reject, every decision logged.
- Consulting memo: process map, staffing, ROI in agent-hours with ranges, rollout plan, risks -> [docs/MEMO.md](docs/MEMO.md).

## Findings
All from [`outputs/numbers.json`](outputs/numbers.json), rebuilt by `make all`.

| Question | Answer |
|---|---|
| How fast do brands first reply? | Median **23.7 min**, p90 **535.2 min** (~9 h) |
| How often is a 60-min SLA missed? | **35.0%** of answered tickets (58.6% at 15 min, 17.2% at 4 h) |
| When is it worst? | 04:00 UTC (43.6%) and weekends (Sat 42.1%) vs Wednesday 30.0% |
| Best forecast for staffing? | Same hour last week: WAPE **27.6%** vs 34.9% flat |
| Agents needed (AmazonHelp volume)? | 1,556 agent-hours/week, peak 15 agents (6-min handle time, 85% occupancy assumed) |
| Classical triage on tidy vs real text? | **99.9%** on Bitext -> **20.0%** on real tweets (CI 15.7-24.7) |
| LLM triage on the same 300 tweets? | 67.0% (20b) / **72.3%** (120b, CI 67.0-77.3) vs 20.0% classical |
| LLM cost and speed? | **$0.04-0.08 per 1,000 tickets**, ~0.6 s median |
| Urgency rules on fresh tweets? | Rules alone caught 3 of 10 urgent; with the AI allowed to raise urgency, **7 of 10** |
| Is routing worth it? | Break-even at 33.3% accuracy: classical loses ~21 h/week, LLM saves ~61 h/week (base) |

## Run it
```bash
pip install -r requirements.txt
make test     # 60 tests, no data needed
make all      # download + verify data, SLA analytics, evals, ROI (LLM rows from cache or GROQ_API_KEY)
make app      # agent queue on http://localhost:8501
```
No laptop? GitHub **Actions -> ci -> Run workflow** does the same and commits `outputs/`. Details and deploy
steps: [docs/RUNBOOK.md](docs/RUNBOOK.md).

## Repo map
| Path | What |
|---|---|
| `sql/` | DuckDB SQL: tickets, FRT by brand / hour, backlog, hourly volume |
| `src/firstreply/` | analytics, staffing, classical model, LLM client, evals, urgency, HITL queue, ROI |
| `evalset/` | 400 labelled tweets (100 dev / 300 test) + 150-tweet urgency hold-out |
| `outputs/` | every generated table and `numbers.json`; `llm_cache/` with real cached LLM calls |
| `app/` | Streamlit agent queue |
| `docs/` | [PRD](docs/PRD.md), [ARCHITECTURE](docs/ARCHITECTURE.md), [EVALS](docs/EVALS.md), [DECISIONS](docs/DECISIONS.md), [MEMO](docs/MEMO.md), [DATA](docs/DATA.md), [RUNBOOK](docs/RUNBOOK.md) |
| `LEARN/` | every concept from zero + 25 interview questions |

## Limits (read before quoting any number)
- LLM results are on all 300 test tickets (full run Oct 29, 2026; every call cached, so `make evals` reproduces
  them without a key). 120b vs 20b is not separable: the intervals overlap.
- One labeller, no agreement score; small classes (order_change has 5 test tickets).
- Twitter only, 2017, UTC times; the 60-minute SLA, handle time and occupancy are assumptions.
- ROI drafting savings are assumptions with a wide range until a pilot measures them.
- Data licence: the Twitter dataset is **CC BY-NC-SA 4.0 (non-commercial)**; Bitext is CDLA-Sharing 1.0.
  This is a portfolio project, not a commercial product.
