# Resume facts

Every fact below is in `outputs/numbers.json` (key shown) and was produced by `make all` in GitHub Actions on
2026-10-29. If a number changes after a re-run, update it here before using it.

## Verified facts
| Fact | Value | numbers.json key |
|---|---|---|
| Tickets analysed | 724,846 (8 weeks, 108 brands) | `sla.tickets`, `sla.brands` |
| Median / p90 first-response time | 23.7 min / 535.2 min | `sla.median_frt_min`, `sla.p90_frt_min` |
| Breach rate, 60-min SLA (assumed) | 35.0% | `sla.breach_pct` |
| Forecast error, best vs flat | WAPE 27.6% vs 34.9% | `sla.forecast_wape_pct` |
| Staffing for AmazonHelp volume | 1,556 agent-hours/week, peak 15 agents | `sla.staffing_*` |
| Classical model, tidy vs real | 99.9% Bitext -> 20.0% on 300 real tweets | `triage.models.tfidf_logreg` |
| LLM accuracy, 300 test tweets (20b / 120b) | 67.0% / 72.3% (120b CI 67.0-77.3) | `triage.models` |
| Zero-shot vs few-shot (20b, dev) | 77.4% vs 74.2% - examples did not help and cost more | `triage.few_shot_ablation_dev` |
| Urgency on fresh hold-out: rules vs rules + AI may raise | 3 of 10 -> 7 of 10 caught (precision 87.5%) | `triage.urgency.holdout` |
| LLM cost per 1,000 tickets | $0.042 / $0.084 | same |
| Urgency rules recall, fresh hold-out | 30.0% (3 of 10) | `triage.urgency.holdout` |
| Routing break-even accuracy | 33.3% | `roi.routing_break_even_accuracy_pct` |
| Routing hours saved/week, 120b base | 61.1 | `roi.by_model` |
| Tests | 60 passing in CI | `make test` |

## Resume bullets (pick 4)
1. Measured **first-response SLAs** on 724,846 support tickets: 35% missed a 1-hour target, p90 wait 9 hours
2. Showed a classifier scoring **99.9% on clean data** fell to **20% on 300 real tweets**
3. Built an eval harness comparing accuracy, **cost per 1,000 tickets** and latency; LLM triage cost under $0.10
4. Forecast hourly volume at **27.6% error** (vs 34.9% flat) and sized **staffing and ROI** in agent-hours saved

Spare: Built a **human-approval queue** where AI may only raise urgency; urgent caught rose from 3 to 7 of 10

All are under 110 characters without the `**`. No tool or vendor names.

## Before you use these - check yourself (placement rule: own it, defend it live)
- [ ] **Labels**: the hand-off says the 400 + 150 tweets were "hand-labelled". Confirm you labelled or fully
      re-checked them yourself. If an AI helped draft labels, say so if asked, and re-check 50 by hand:
      `python scripts/recheck.py score` after filling `evalset/recheck_50.csv` blind (gives agreement + kappa).
- [x] **LLM numbers are final** (full 300-ticket run, Oct 29, 2026; reproduces from cache without a key).
- [ ] Re-run `make all` yourself once and see the same numbers.
- [ ] Be able to explain, without notes: p90, WAPE, TF-IDF, logistic regression, macro-F1, bootstrap CI,
      Erlang C, break-even accuracy, "AI may only raise urgency" (see `LEARN/`).
- [ ] Know the weak spots (EVALS.md "Limits") and say them before the interviewer does.
