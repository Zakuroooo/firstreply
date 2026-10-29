# Decisions (ADRs)

Short records of choices that shape the results. Format: context, decision, consequence.

## ADR-1: Real Twitter timestamps for SLA, not synthetic tickets
- **Context**: Most ticket datasets (Bitext included) have no times, so no response-time metric is possible.
- **Decision**: Build tickets from Kaggle's Twitter support data, where every tweet has a timestamp and a reply link.
- **Consequence**: Real FRT, backlog and volume. But Twitter-only, 2017, UTC, and non-commercial licence.

## ADR-2: Route to 8 team queues, not Bitext's 27 intents
- **Context**: Real tweets do not split cleanly into 27 intents, and an ops team routes to teams, not intents.
- **Decision**: 8 queues (`src/firstreply/labels.py`), with Bitext intents mapped onto them and an explicit
  `other`. `newsletter_subscription` is dropped (real "subscription" tweets are about paid plans).
- **Consequence**: Labels match how work is actually split. Bitext has no `other` and no
  `complaint_feedback`-style venting, so the classical model needs a confidence threshold for `other`.

## ADR-3: Train classical on Bitext, test everything on real tweets
- **Context**: We want an honest test of "tidy training data -> messy reality".
- **Decision**: TF-IDF + logistic regression trained on Bitext; all models scored on the same 300 real test tweets.
  We also report its accuracy on held-out Bitext, so the gap is visible.
- **Consequence**: The classical score is lower than a "99% on Bitext" headline, and that gap is the finding.

## ADR-4: Groq-hosted open-weight models, cached calls
- **Context**: Free tier, OpenAI-compatible API, published per-token prices, two model sizes.
- **Decision**: `openai/gpt-oss-20b` and `openai/gpt-oss-120b`, temperature 0, JSON output. Every call is cached
  in `outputs/llm_cache/` keyed by model + prompt, so evals re-run without a key.
- **Consequence**: Reproducible and cheap. Prices are Groq's list prices on 2026-10-29 and will change.
  If no key and no full cache exist, LLM rows are skipped and the reason is recorded - never estimated.

## ADR-5: Urgency = rules first, AI may only raise
- **Context**: Missing an urgent ticket is much worse than an extra one. Rules are explainable; AI catches odd wording.
- **Decision**: Regex rules decide P1. The LLM's urgent flag can move P2/P3 -> P1, never P1 down.
- **Consequence**: Recall can only go up when AI is added; precision may go down. Both are reported.
- **Change log**: On 2026-10-29 the rules got a closing word boundary (so "Firefox" and "Fire Stick" no longer
  match "fire"). This came from a unit test, before any urgency score on the hold-out had been computed.

## ADR-6: Human approves every reply
- **Context**: A wrong public reply hurts the brand; LLM drafts can be wrong or invent policy.
- **Decision**: The queue app only suggests. An agent approves, edits or rejects; nothing is sent automatically.
  Without an LLM, a fixed safe template per queue is shown and labelled as a template.
- **Consequence**: Savings are smaller than full automation, but risk is controlled and every decision is logged
  as live eval data.

## ADR-7: 60-minute first-response SLA (assumed)
- **Context**: The data has no SLA.
- **Decision**: 60 minutes, a common target for social support, set in one place (`db.SLA_MINUTES`). Breach rates
  at 15 min and 4 h are reported too.
- **Consequence**: Breach numbers depend on this choice; we show how much.

## ADR-8: Data downloads through CI when the dev box is offline
- **Context**: The cloud dev container could not reach Hugging Face, Kaggle or Groq.
- **Decision**: `make all` runs in a manual GitHub Actions job (`reproduce`) that downloads the data, checks it
  with `verify_data.py`, rebuilds every output and commits `outputs/`.
- **Consequence**: Every committed number is produced by a script on a clean machine. Anyone with repo access can
  re-run it with one click.
