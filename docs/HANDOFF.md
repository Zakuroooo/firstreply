# Hand-over: local session → cloud session (Oct 29, 2026)

The project was started in a local session on Pranay's Mac and moved to the cloud. The cloud session must
continue from exactly this state and these decisions. Nothing else is running locally; the local folder is
frozen until the cloud work is pulled back.

## Rules the local session followed (from its git-ignored CLAUDE.md, copied here)
- Public data only: Kaggle "Customer Support on Twitter" (CC BY-NC-SA 4.0) and Bitext customer-support intents
  (CDLA-Sharing 1.0). Not any company's internal data. No real users.
- Every number in docs/README/resume comes from `outputs/numbers.json` (scripts write it). Never type numbers by hand.
- Evals: one command reproduces everything; LLM calls are cached in `outputs/llm_cache/*.jsonl` (committed),
  so results reproduce without an API key. A key is only needed for NEW calls.
- Keys only in `.env` (git-ignored). Never print them.
- Git: small commits, plain messages, NO Co-Authored-By / Claude / AI lines.
- Code must be simple enough for Pranay to explain line by line.

## Decisions already made
- Name **FirstReply**, after first-response time (the core SLA metric).
- LLM provider: **Groq**, models `openai/gpt-oss-20b` and `openai/gpt-oss-120b`, zero-shot and few-shot. Prices were
  taken from Groq's own docs; cost per ticket is tracked per call in `src/firstreply/llm.py`.
- Analytics: DuckDB SQL in `sql/01–05`; `src/firstreply/analytics.py`, `staffing.py`. Result so far: 724,846 tickets,
  8 weeks, 108 brands; SLA breach % at 15/60/240 min; backlog; seasonal-naive forecast won on WAPE (see numbers.json "sla").
- Eval set: **400 real tweets hand-labelled** by a written rule set without seeing model outputs
  (`evalset/tickets.csv`, `labels.csv`) → **100 dev / 300 test**. Few-shot examples and the classical "other"
  threshold come from dev only. A separate fresh **150-tweet urgency hold-out** (`evalset/urgency_holdout.csv`)
  tests the urgency rules on text not read while writing them.
- Classical baseline: TF-IDF + logistic regression trained on Bitext, threshold tuned on dev.
- Urgency: rules decide P1; the AI may only RAISE urgency, never lower it (same principle as his FollowUp project).
- Bootstrap 95% CIs (1,000 resamples) on accuracy and macro-F1.

## Where it stopped
- `src/firstreply/evals.py` was written; its first full run (1,200 LLM calls) did not finish — the background
  command exited 144 (killed). The cache holds ~148 + 146 calls. Finish the run: with a `GROQ_API_KEY` set in the
  cloud environment it continues from the cache; without a key, say so and stop rather than invent results.
- Not started yet: human-in-the-loop queue app (`app/` is empty), tests, CI, consulting memo, docs, LEARN/, RESUME-FACTS.

## Data in the cloud
`raw/` and `data/` are not in git. `scripts/download_data.py` uses the Kaggle CLI (needs a Kaggle token) for twcs.
If no token is available, try a public mirror of the same file; otherwise stop and say exactly what is needed.

## Status after the cloud session (Oct 29, 2026)
- Data: the cloud container could not reach Kaggle, Hugging Face or Groq. The GitHub Actions `reproduce` job
  downloads the data (Hugging Face mirror of twcs.csv), checks it (2,811,774 rows; 550/550 eval tweets match),
  runs `make all` and commits `outputs/`. SLA numbers came out identical to the local Kaggle run.
- Done: SLA analytics, classical eval (final), LLM eval (finished locally Oct 29: all 300 test tickets), urgency rules,
  HITL queue app, ROI, 60 tests + CI, deploy config (not deployed), all docs, LEARN, RESUME-FACTS.
- Still needs a `GROQ_API_KEY`: the remaining ~700 LLM calls (full 300-ticket LLM rows, few-shot ablation,
  AI-raised urgency, LLM drafts in the app). Add the repo secret and run the `reproduce` job.
