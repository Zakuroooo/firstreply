"""Run triage models on the SAME 300 held-out real tweets and write outputs/eval_*.csv + numbers.json.

What runs where (chosen to fit Groq's free tier: 200K tokens per model per day):
- test split (300): classical TF-IDF + logistic regression vs gpt-oss-20b and gpt-oss-120b, same zero-shot prompt
- dev split (100): zero-shot vs few-shot ablation on gpt-oss-20b (few-shot examples come from dev and are left out)
- urgency holdout (150 fresh tweets): rules vs rules + AI-may-raise, using gpt-oss-120b
Run: python -m firstreply.evals   (LLM results come from outputs/llm_cache/; a key is only needed for new calls)
With no key and an incomplete cache, the LLM rows are skipped and the reason is written to numbers.json.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

from firstreply import classical, db, llm, numbers, urgency
from firstreply.labels import QUEUES

OUT = db.ROOT / "outputs"
SMALL, LARGE = "openai/gpt-oss-20b", "openai/gpt-oss-120b"
BOOTSTRAPS = 1000


def load_evalset():
    t = pd.read_csv(db.ROOT / "evalset" / "tickets.csv").merge(pd.read_csv(db.ROOT / "evalset" / "labels.csv"))
    return t[t.split == "dev"].reset_index(drop=True), t[t.split == "test"].reset_index(drop=True)


def load_holdout():
    return pd.read_csv(db.ROOT / "evalset" / "urgency_holdout.csv")


def macro_f1(y_true, y_pred):
    return f1_score(y_true, y_pred, labels=QUEUES, average="macro", zero_division=0)


def bootstrap_ci(y_true, y_pred, metric, seed=0):
    """95% confidence interval by resampling the tickets with replacement 1,000 times."""
    rng = np.random.default_rng(seed)
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    scores = []
    for _ in range(BOOTSTRAPS):
        idx = rng.integers(0, len(y_true), len(y_true))
        scores.append(metric(y_true[idx], y_pred[idx]))
    return [round(100 * float(np.percentile(scores, 2.5)), 1), round(100 * float(np.percentile(scores, 97.5)), 1)]


def few_shot_examples(dev):
    """One dev example per queue (lowest eval_id), so the prompt shows every queue once."""
    rows = dev.sort_values("eval_id").groupby("label").head(1)
    return [(r.clean_text, r.label, bool(r.urgent)) for r in rows.itertuples()], set(rows.eval_id)


def score(name, labels, preds, cost_per_ticket, latencies, extra=None):
    row = {
        "model": name,
        "n": len(labels),
        "accuracy_pct": round(100 * accuracy_score(labels, preds), 1),
        "accuracy_ci95": bootstrap_ci(labels, preds, accuracy_score),
        "macro_f1_pct": round(100 * macro_f1(labels, preds), 1),
        "macro_f1_ci95": bootstrap_ci(labels, preds, macro_f1),
        "cost_per_1000_usd": round(1000 * cost_per_ticket, 4),
        "latency_p50_ms": round(float(np.percentile(latencies, 50)), 1),
        "latency_p95_ms": round(float(np.percentile(latencies, 95)), 1),
    }
    row.update(extra or {})
    per_class = f1_score(labels, preds, labels=QUEUES, average=None, zero_division=0)
    row["per_class_f1"] = {q: round(100 * float(s), 1) for q, s in zip(QUEUES, per_class)}
    return row


COVERED = ["delivery", "order_change", "refund_return", "billing_payment", "account", "talk_to_human"]


def covered_accuracy(labels, preds):
    """Accuracy only on tickets whose true queue has Bitext training data (no complaint_feedback / other)."""
    pairs = [(t, p) for t, p in zip(labels, preds) if t in COVERED]
    return round(100 * sum(t == p for t, p in pairs) / max(len(pairs), 1), 1)


def run_classical(dev, test, holdout):
    model, in_domain_acc, n_train = classical.train_bitext()
    threshold = classical.tune_threshold(model, dev.clean_text, dev.label.tolist(), macro_f1)
    preds, _, _ = classical.predict_with_threshold(model, test.clean_text, threshold)
    no_threshold, _, _ = classical.predict_with_threshold(model, test.clean_text, 0.0)
    latencies = classical.single_ticket_latency_ms(model, test.clean_text)
    row = score("tfidf_logreg", test.label.tolist(), preds, 0.0, latencies, {
        "bitext_in_domain_accuracy_pct": round(100 * in_domain_acc, 1),
        "bitext_train_rows": n_train,
        "other_threshold": threshold,
        "accuracy_without_threshold_pct": round(100 * accuracy_score(test.label, no_threshold), 1),
        "covered_queues_accuracy_pct": covered_accuracy(test.label, preds),
    })
    holdout_preds, _, _ = classical.predict_with_threshold(model, holdout.clean_text, threshold)
    return row, preds, holdout_preds


def llm_ready(model_name, texts, examples=()):
    """An LLM can be scored only if a key is set or every call is already cached. Returns (ready, cached)."""
    cached = sum(llm.is_cached(model_name, llm.triage_messages(t, examples)) for t in texts)
    return llm.has_key() or cached == len(texts), cached


def llm_results(model_name, texts, examples=()):
    return [llm.triage(model_name, t, examples) for t in texts]


def run_llm(name, model_name, frame, examples=()):
    results = llm_results(model_name, frame.clean_text, examples)
    preds = [r["queue"] for r in results]
    row = score(name, frame.label.tolist(), preds, float(np.mean([r["cost_usd"] for r in results])),
                [r["latency_ms"] for r in results], {
                    "invalid_output_pct": round(100 * float(np.mean([not r["valid_json"] for r in results])), 1),
                    "avg_input_tokens": round(float(np.mean([r["input_tokens"] for r in results]))),
                    "avg_output_tokens": round(float(np.mean([r["output_tokens"] for r in results]))),
                })
    return row, preds, [r["urgent"] for r in results]


def urgency_stats(texts, queues, truth, ai_urgent=None):
    """Recall/precision of P1 for rules alone, and for rules + AI-may-raise when AI flags are given."""
    truth = np.array(truth, dtype=bool)
    rules = np.array([urgency.rule_level(t, q)[0] == "P1" for t, q in zip(texts, queues)])

    def stats(pred):
        tp = int((pred & truth).sum())
        return {"recall_pct": round(100 * tp / max(truth.sum(), 1), 1),
                "precision_pct": round(100 * tp / max(pred.sum(), 1), 1),
                "flagged": int(pred.sum()), "caught": tp}
    out = {"urgent": int(truth.sum()), "tickets": len(truth), "rules_only": stats(rules)}
    if ai_urgent is not None:
        both = np.array([urgency.final_level(t, q, a)[0] == "P1" for t, q, a in zip(texts, queues, ai_urgent)])
        out["rules_plus_ai_raise"] = stats(both)
    return out


def interim_cached_subset(test, classical_preds):
    """Score every model on the test tickets that BOTH LLMs already have cached answers for.

    Only used while the full LLM run is missing. It is a partial result: fewer tickets, wider intervals.
    """
    mask = [llm.is_cached(SMALL, llm.triage_messages(t)) and llm.is_cached(LARGE, llm.triage_messages(t))
            for t in test.clean_text]
    sub = test[mask].reset_index(drop=True)
    if len(sub) < 30:
        return None
    cls = [p for p, m in zip(classical_preds, mask) if m]
    rows = [score("tfidf_logreg", sub.label.tolist(), cls, 0.0, [0.0], {"covered_queues_accuracy_pct":
                                                                      covered_accuracy(sub.label, cls)})]
    for name, model in (("gpt-oss-20b", SMALL), ("gpt-oss-120b", LARGE)):
        row, preds, _ = run_llm(name, model, sub)
        row["covered_queues_accuracy_pct"] = covered_accuracy(sub.label, preds)
        rows.append(row)
    rows[0]["latency_p50_ms"] = rows[0]["latency_p95_ms"] = None  # measured on the full set instead
    return {"interim": True, "tickets": len(sub), "eval_ids": sub.eval_id.tolist(),
            "note": "partial: only test tickets with cached answers from both LLMs; not the headline result",
            "models": {r["model"]: r for r in rows}}


def failures(test, preds, per_model=15):
    """Wrong answers per model (first `per_model` by eval_id) so a human can read what goes wrong."""
    rows = []
    for name, p in preds.items():
        wrong = test.assign(pred=p)[lambda d: d.pred != d.label].sort_values("eval_id").head(per_model)
        rows += [{"model": name, "eval_id": r.eval_id, "text": r.clean_text, "truth": r.label, "predicted": r.pred}
                 for r in wrong.itertuples()]
    return pd.DataFrame(rows)


def main():
    dev, test = load_evalset()
    holdout = load_holdout()
    examples, example_ids = few_shot_examples(dev)
    dev_rest = dev[~dev.eval_id.isin(example_ids)].reset_index(drop=True)
    rows, ablation, preds, urgent_flags, skipped = [], [], {}, {}, {}

    row, preds["tfidf_logreg"], holdout_classical = run_classical(dev, test, holdout)
    rows.append(row)
    for name, model in (("gpt-oss-20b", SMALL), ("gpt-oss-120b", LARGE)):
        ready, cached = llm_ready(model, test.clean_text)
        if not ready:
            skipped[name] = f"not run: no GROQ_API_KEY and only {cached}/{len(test)} calls cached"
            continue
        row, preds[name], urgent_flags[name] = run_llm(name, model, test)
        rows.append(row)

    # few-shot ablation on dev (examples removed from the dev rows they would leak into)
    if llm_ready(SMALL, dev_rest.clean_text)[0] and llm_ready(SMALL, dev_rest.clean_text, examples)[0]:
        ablation = [run_llm("gpt-oss-20b zero-shot", SMALL, dev_rest)[0],
                    run_llm("gpt-oss-20b few-shot", SMALL, dev_rest, examples)[0]]
    else:
        skipped["few_shot_ablation"] = "not run: needs GROQ_API_KEY or a full cache"

    # urgency on the test split and on the fresh holdout (rules frozen before the holdout was drawn)
    urg = {"test": {"rules_with_tfidf_queue": urgency_stats(test.clean_text, preds["tfidf_logreg"], test.urgent)},
           "holdout": {"rules_with_tfidf_queue": urgency_stats(holdout.clean_text, holdout_classical, holdout.urgent)}}
    for name in urgent_flags:
        urg["test"][name] = urgency_stats(test.clean_text, preds[name], test.urgent, urgent_flags[name])
    interim = interim_cached_subset(test, preds["tfidf_logreg"]) if skipped.get("gpt-oss-20b") else None
    if llm_ready(LARGE, holdout.clean_text)[0]:
        hold = llm_results(LARGE, holdout.clean_text)
        urg["holdout"]["gpt-oss-120b"] = urgency_stats(holdout.clean_text, [r["queue"] for r in hold],
                                                       holdout.urgent, [r["urgent"] for r in hold])

    flat = pd.DataFrame(rows + ablation).drop(columns=["per_class_f1"])
    flat.to_csv(OUT / "eval_triage.csv", index=False)
    detail = test[["eval_id", "brand", "clean_text", "label", "urgent"]].copy()
    for name, p in preds.items():
        detail[name] = p
    detail.to_csv(OUT / "eval_predictions.csv", index=False)
    failures(test, preds).to_csv(OUT / "eval_failures.csv", index=False)
    pd.crosstab(test.label, pd.Series(preds["tfidf_logreg"], name="predicted")).to_csv(
        OUT / "eval_confusion_tfidf.csv")

    numbers.save_section("triage", {
        "test_tickets": len(test), "dev_tickets": len(dev), "holdout_tickets": len(holdout),
        "label_counts_test": test.label.value_counts().to_dict(),
        "models": {r["model"]: r for r in rows},
        "few_shot_ablation_dev": {r["model"]: r for r in ablation},
        "skipped": skipped,
        "interim_cached_subset": interim,
        "urgency": urg,
    })
    print(flat.to_string())
    print(urg)
    for name, why in skipped.items():
        print(name, "->", why)
    if interim:
        print("INTERIM (partial) on", interim["tickets"], "cached tickets:")
        print(pd.DataFrame(interim["models"].values()).drop(columns=["per_class_f1"]).to_string())


if __name__ == "__main__":
    main()
