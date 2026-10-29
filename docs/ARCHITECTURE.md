# Architecture

```
raw/ (downloaded, git-ignored)          data/tweets.parquet (git-ignored)
  twcs/twcs.csv  --scripts/to_parquet.py-->      |
  bitext/bitext.csv                              v
       |                         sql/01_tickets.sql  -> tickets table (DuckDB, in memory)
       |                         sql/02-05           -> FRT by brand / hour, backlog, hourly volume
       |                                 |
       |                     firstreply.analytics -> outputs/sla_*.csv, backlog, forecast, staffing_plan
       v
 firstreply.classical (TF-IDF + LR)  \
 firstreply.llm (Groq, cached)        >-- firstreply.evals --> outputs/eval_*.csv
 evalset/ (400 labelled + 150 hold-out)/                          |
                                                                  v
 firstreply.urgency (rules, AI may raise)          firstreply.roi -> outputs/roi_sensitivity.csv
                                                                  |
                       every script writes its own section of outputs/numbers.json
                                                                  |
                                     docs/ README / MEMO / RESUME-FACTS quote only numbers.json

 app/queue_app.py (Streamlit) -- firstreply.hitl --> app/approvals.db (SQLite decision log)
```

## Modules (`src/firstreply/`)
| File | Job |
|---|---|
| `db.py` | DuckDB connection, analysis window, SLA setting, runs `sql/*.sql` |
| `analytics.py` | FRT median/p90, breach %, backlog, 3 forecast baselines (WAPE), staffing plan |
| `staffing.py` | workload formula and Erlang C |
| `text.py` | one cleaning function for every model (HTML, links, @handles) |
| `labels.py` | 8 queues and the Bitext -> queue map |
| `classical.py` | TF-IDF + logistic regression, "other" threshold, per-ticket latency |
| `llm.py` | Groq client, prompt, JSON parsing, token cost, disk cache, draft replies |
| `evals.py` | runs every model on the same test set; accuracy, macro-F1, bootstrap CIs, cost, latency, failures, urgency |
| `urgency.py` | VADER sentiment, P1 rules, raise-only combine |
| `hitl.py` | queue ordering, template drafts, SQLite approval log, loop stats |
| `roi.py` | agent-hours saved, low/base/high, sensitivity, break-even |
| `numbers.py` | read/write `outputs/numbers.json` |

## Design rules
- **One source of truth for numbers**: scripts write `numbers.json`; docs quote it.
- **Same input for every model**: `text.clean` runs once; all models see identical text.
- **No key, no problem**: LLM calls are cached; without key or cache the LLM rows are skipped, not guessed.
- **Plain tools**: SQL for aggregation, pandas/scikit-learn for modelling, SQLite for the log. No framework a
  reviewer has to learn first.

## Runtime
- Analytics: ~2.8M tweets in DuckDB with a 3 GB memory cap; a few minutes on a laptop or CI runner.
- Classical model: trains in seconds; well under a millisecond per ticket.
- LLM: one HTTPS call per ticket; latency and cost are measured per call (see EVALS.md).
