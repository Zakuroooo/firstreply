# Evals

Every number here is copied from `outputs/numbers.json` (section `triage`), produced by `make evals`
(GitHub Actions `reproduce` job, 2026-10-29). Re-run it and the numbers must match.

## Setup
- **Test set**: 300 real opening tweets to 12 retail / delivery / payments / telecom brands, labelled into
  8 queues before any model was run (`evalset/`, `docs/LABEL-GUIDE.md`). Label mix: complaint_feedback 95,
  other 66, delivery 49, billing_payment 28, refund_return 25, account 21, talk_to_human 11, order_change 5.
- **Dev set**: 100 more tweets, used only for the classical "other" threshold and the few-shot examples.
- **Same input for all**: one cleaning function (`text.clean`); same 300 tickets; same scoring code.
- **Metrics**: accuracy and macro-F1 with bootstrap 95% intervals (1,000 resamples), cost per 1,000 tickets,
  latency p50/p95, invalid-output rate, failure examples.

## Result 1 - classical baseline on all 300 test tickets (final)
| Model | Accuracy | 95% CI | Macro-F1 | Cost / 1,000 | Latency p50 / p95 |
|---|---|---|---|---|---|
| TF-IDF + logistic regression (trained on Bitext) | **20.0%** | 15.7-24.7 | 20.0% | ~$0 (CPU) | 0.7 / 0.8 ms |

- Same model on held-out **Bitext**: **99.9%**. On real tweets: **20.0%**. That gap is domain shift.
- Only on the 6 queues Bitext covers (no complaint_feedback / other): **30.2%**. So the drop is not only a
  taxonomy problem; the model also fails on real wording.
- Without the "other" threshold (tuned on dev to 0.35): 16.3%.
- Why it fails (`outputs/eval_confusion_tfidf.csv`): unfamiliar text falls into `account`, the biggest mapped
  Bitext class; 48 of 95 complaint tweets go there. Delivery is its best queue (F1 42.9%).

## Result 2 - LLMs vs classical on the same 154 tickets (INTERIM)
The full LLM run needs a Groq key, which this build environment did not have. The earlier session made real
calls for 154 of the 300 test tickets (cached in `outputs/llm_cache/`). All three models are scored on exactly
those 154 tickets. **This is a partial result** - treat it as a direction, not a final number.

| Model (zero-shot, same prompt) | Accuracy | 95% CI | Macro-F1 | Covered-queue acc. | Cost / 1,000 tickets | Latency p50 / p95 | Invalid JSON |
|---|---|---|---|---|---|---|---|
| TF-IDF + LR | 22.7% | 16.2-29.2 | 23.5% | 33.3% | ~$0 | <1 ms | - |
| gpt-oss-20b | 66.2% | 59.1-73.4 | 61.4% | 73.9% | $0.042 | 549 / 1,086 ms | 0% |
| gpt-oss-120b | 71.4% | 64.3-78.6 | 67.2% | 82.6% | $0.084 | 589 / 1,186 ms | 0% |

- Both LLMs beat the classical model by a wide margin; the intervals do not overlap.
- 120b vs 20b: +5 points for 2x the price, but the intervals overlap a lot - on 154 tickets we **cannot** say
  120b is better.
- Cost is tiny either way: ~360 input + ~51 output tokens per ticket; for AmazonHelp's 12,540 tickets/week,
  triage costs about $1 a week on 120b (`numbers.json` roi). Latency (~0.6 s) is fine for a queue, not for
  per-keystroke use.
- Failure examples (`outputs/eval_failures_interim_llm.csv`): most LLM "errors" are borderline cases between
  complaint_feedback and refund_return ("store is selling expired milk") or tweets with no context ("The affected
  number is 0902..."). Some of these are label ambiguity, not model error - a second labeller would show how
  much (see Limits).

## Result 3 - urgency rules (final for rules-only)
| Set | Urgent tickets | Rules recall | Rules precision |
|---|---|---|---|
| Test split (300) | 16 | 81.2% (13/16) | 86.7% (13/15) |
| Fresh hold-out (150) | 10 | **30.0% (3/10)** | 75.0% (3/4) |

The rules were written while reading eval-set tweets, so the test-split number is optimistic. On fresh tweets
they caught only 3 of 10 urgent ones. That is the case for letting the AI **raise** urgency. The
"rules + AI may raise" rows are computed automatically once the LLM run is complete (`urgency` in numbers.json).

## Not run yet (needs `GROQ_API_KEY`)
- LLM rows on all 300 test tickets; few-shot vs zero-shot ablation on dev; AI-raise urgency on test and hold-out.
- How: add the key (`.env` locally, or the `GROQ_API_KEY` repo secret) and run `make evals` or the CI
  `reproduce` job. Cached calls are reused; only missing ones are made (about 700 calls, ~400 tokens each, which should
  fit Groq's free limit of 200K tokens per model per day). The interim table above is replaced by the full one automatically.

## Limits
- One labeller, no inter-annotator agreement. Several LLM "failures" are arguable.
- Small classes (order_change 5, talk_to_human 11): per-class F1 there is noise.
- 2017 English-heavy Twitter data; a few tweets are Spanish, Japanese or Hinglish-style SMS text.
- The classical model is trained on synthetic Bitext by design (ADR-3). A classical model trained on a few
  thousand labelled real tweets would do much better; that is the fair next experiment.
- Prices are Groq list prices on 2026-10-29; latency was measured from the earlier session's network.
