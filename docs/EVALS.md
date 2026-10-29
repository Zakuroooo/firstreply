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

## Result 2 - LLMs vs classical on the same 300 tickets
Full run on Oct 29, 2026 (every call cached in `outputs/llm_cache/`, so `make evals` reproduces it without a key).

| Model (zero-shot, same prompt) | Accuracy | 95% CI | Macro-F1 | 95% CI | Cost / 1,000 tickets | Latency p50 / p95 | Invalid JSON |
|---|---|---|---|---|---|---|---|
| TF-IDF + LR | 20.0% | 15.7-24.7 | 20.0% | 15.1-24.8 | ~$0 | <1 ms | - |
| gpt-oss-20b | 67.0% | 61.7-72.3 | 64.9% | 57.2-71.6 | $0.042 | 585 / 1,371 ms | 0% |
| gpt-oss-120b | 72.3% | 67.0-77.3 | 67.4% | 59.3-74.6 | $0.085 | 603 / 1,310 ms | 0% |

- Both LLMs beat the classical model by a wide margin; the intervals do not overlap.
- 120b vs 20b: +5 points for 2x the price, but the intervals overlap - we **cannot** say 120b is better.
- Cost is tiny either way: ~360 input + ~51 output tokens per ticket; for AmazonHelp's 12,540 tickets/week,
  triage costs about $1 a week on 120b (`numbers.json` roi). Latency (~0.6 s) is fine for a queue.
- Failure examples (`outputs/eval_failures.csv`): most LLM "errors" are borderline cases between
  complaint_feedback and refund_return or tweets with no context. Some are label ambiguity, not model error -
  a second labeller would show how much (see Limits).

## Result 3 - zero-shot vs few-shot (dev only, gpt-oss-20b, 93 tickets)
| Prompt | Accuracy | 95% CI | Cost / 1,000 | Latency p50 |
|---|---|---|---|---|
| Zero-shot | 77.4% | 69.9-85.0 | $0.043 | 624 ms |
| Few-shot (examples from dev) | 74.2% | 65.6-82.8 | $0.058 | 1,006 ms |

Adding examples did not help (intervals overlap) and cost ~35% more and was slower, so the test runs use zero-shot.
Only 93 of 100 dev tickets are scored: the 7 used as few-shot examples are left out of both rows.

## Result 4 - urgency: rules alone vs rules + "AI may raise"
| Set | Urgent tickets | Rules only: caught / flagged | Rules + 120b may raise: caught / flagged |
|---|---|---|---|
| Test split (300) | 16 | 13 / 15 (recall 81.2%) | 13 / 17 (recall 81.2%, precision 76.5%) |
| Fresh hold-out (150) | 10 | **3 / 4 (recall 30.0%)** | **7 / 8 (recall 70.0%, precision 87.5%)** |

The rules were written while reading eval-set tweets, so their test-split number is optimistic; on fresh tweets
they caught only 3 of 10. Letting the AI raise (never lower) urgency caught 4 more on the hold-out with one extra
false alarm. 10 urgent tickets is a small sample: read it as a direction, not a precise rate.

## Limits
- One labeller, no inter-annotator agreement. Several LLM "failures" are arguable.
- Small classes (order_change 5, talk_to_human 11): per-class F1 there is noise.
- 2017 English-heavy Twitter data; a few tweets are Spanish, Japanese or Hinglish-style SMS text.
- The classical model is trained on synthetic Bitext by design (ADR-3). A classical model trained on a few
  thousand labelled real tweets would do much better; that is the fair next experiment.
- Prices are Groq list prices on 2026-10-29; latency was measured from the earlier session's network.
