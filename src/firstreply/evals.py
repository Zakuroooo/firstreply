"""Run triage models on the SAME 300 held-out real tweets and write outputs/eval_*.csv + numbers.json.

What runs where (chosen to fit Groq's free tier: 200K tokens per model per day):
- test split (300): classical TF-IDF + logistic regression vs gpt-oss-20b and gpt-oss-120b, same zero-shot prompt
- dev split (100): zero-shot vs few-shot ablation on gpt-oss-20b (few-shot examples come from dev and are left out)
- urgency holdout (150 fresh tweets): rules vs rules + AI-may-raise, using gpt-oss-120b
Run: python -m firstreply.evals   (LLM results come from outputs/llm_cache/; a key is only needed for new calls)
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


def run_classical(dev, test):
    model, in_domain_acc, n_train = classical.train_bitext()
    threshold = classical.tune_threshold(model, dev.clean_text, dev.label.tolist(), macro_f1)
    preds, _, ms = classical.predict_with_threshold(model, test.clean_text, threshold)
    no_threshold, _, _ = classical.predict_with_threshold(model, test.clean_text, 0.0)
    row = score("tfidf_logreg", test.label.tolist(), preds, 0.0, [ms], {
        "bitext_in_domain_accuracy_pct": round(100 * in_domain_acc, 1),
        "bitext_train_rows": n_train,
        "other_threshold": threshold,
        "accuracy_without_threshold_pct": round(100 * accuracy_score(test.label, no_threshold), 1),
    })
    return row, preds


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


def urgency_stats(texts, queues, ai_urgent, truth):
    """Recall/precision of P1 for rules alone vs rules + AI-may-raise."""
    truth = np.array(truth, dtype=bool)
    rules = np.array([urgency.rule_level(t, q)[0] == "P1" for t, q in zip(texts, queues)])
    both = np.array([urgency.final_level(t, q, a)[0] == "P1" for t, q, a in zip(texts, queues, ai_urgent)])

    def stats(pred):
        tp = int((pred & truth).sum())
        return {"recall_pct": round(100 * tp / max(truth.sum(), 1), 1),
                "precision_pct": round(100 * tp / max(pred.sum(), 1), 1),
                "flagged": int(pred.sum()), "caught": tp}
    return {"urgent": int(truth.sum()), "tickets": len(truth), "rules_only": stats(rules),
            "rules_plus_ai_raise": stats(both)}


def main():
    dev, test = load_evalset()
    examples, example_ids = few_shot_examples(dev)
    rows, preds, urgent_flags = [], {}, {}

    row, preds["tfidf_logreg"] = run_classical(dev, test)
    rows.append(row)
    for name, model in (("gpt-oss-20b", SMALL), ("gpt-oss-120b", LARGE)):
        row, preds[name], urgent_flags[name] = run_llm(name, model, test)
        rows.append(row)

    # few-shot ablation on dev (examples removed from the dev rows they would leak into)
    dev_rest = dev[~dev.eval_id.isin(example_ids)].reset_index(drop=True)
    ablation = [run_llm("gpt-oss-20b zero-shot", SMALL, dev_rest)[0],
                run_llm("gpt-oss-20b few-shot", SMALL, dev_rest, examples)[0]]

    # urgency on the test split and on the fresh holdout (rules frozen before the holdout was drawn)
    holdout = load_holdout()
    hold = llm_results(LARGE, holdout.clean_text)
    urg = {
        "test": {name: urgency_stats(test.clean_text, preds[name], urgent_flags[name], test.urgent)
                 for name in urgent_flags},
        "holdout_gpt-oss-120b": urgency_stats(holdout.clean_text, [r["queue"] for r in hold],
                                              [r["urgent"] for r in hold], holdout.urgent),
    }

    flat = pd.DataFrame(rows + ablation).drop(columns=["per_class_f1"])
    flat.to_csv(OUT / "eval_triage.csv", index=False)
    detail = test[["eval_id", "brand", "clean_text", "label", "urgent"]].copy()
    for name, p in preds.items():
        detail[name] = p
    detail.to_csv(OUT / "eval_predictions.csv", index=False)

    numbers.save_section("triage", {
        "test_tickets": len(test), "dev_tickets": len(dev), "holdout_tickets": len(holdout),
        "label_counts_test": test.label.value_counts().to_dict(),
        "models": {r["model"]: r for r in rows},
        "few_shot_ablation_dev": {r["model"]: r for r in ablation},
        "urgency": urg,
    })
    print(flat.to_string())
    print(urg)


if __name__ == "__main__":
    main()
