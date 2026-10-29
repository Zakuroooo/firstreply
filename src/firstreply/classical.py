"""Classical baseline: TF-IDF features + logistic regression, trained on Bitext.

Bitext has no "other" class, so the model says "other" when its top probability is below a threshold
chosen on the dev split of real tweets.
"""
import time

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline

from firstreply import db, text
from firstreply.labels import BITEXT_TO_QUEUE

SEED = 7


def load_bitext():
    df = pd.read_csv(db.ROOT / "raw" / "bitext" / "bitext.csv")
    df["queue"] = df.intent.map(BITEXT_TO_QUEUE)
    df = df.dropna(subset=["queue"])
    df["clean_text"] = df.instruction.map(text.clean)
    return df


def make_model():
    return make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, lowercase=True),
        LogisticRegression(C=10, max_iter=2000),
    )


def train_bitext():
    """Fit on 80% of Bitext; return the model and its accuracy on the other 20% (tidy, in-domain text)."""
    df = load_bitext()
    tr, te = train_test_split(df, test_size=0.2, random_state=SEED, stratify=df.queue)
    model = make_model().fit(tr.clean_text, tr.queue)
    in_domain_acc = float((model.predict(te.clean_text) == te.queue).mean())
    return model, in_domain_acc, len(tr)


def predict_with_threshold(model, texts, threshold):
    """Top class, or "other" when the model is not confident enough. Also returns ms per ticket."""
    start = time.perf_counter()
    proba = model.predict_proba(list(texts))
    ms = (time.perf_counter() - start) * 1000 / max(len(texts), 1)
    top = proba.argmax(axis=1)
    preds = np.where(proba.max(axis=1) >= threshold, model.classes_[top], "other")
    return list(preds), proba.max(axis=1), ms


def single_ticket_latency_ms(model, texts):
    """Time each ticket on its own, the way a live queue would call the model (one ticket at a time)."""
    out = []
    for t in texts:
        start = time.perf_counter()
        model.predict_proba([t])
        out.append((time.perf_counter() - start) * 1000)
    return out


def tune_threshold(model, dev_texts, dev_labels, metric):
    """Pick the threshold (0.0-0.95) that gives the best metric on the dev split."""
    best_t, best_score = 0.0, -1.0
    for t in np.arange(0.0, 0.96, 0.05):
        preds, _, _ = predict_with_threshold(model, dev_texts, t)
        score = metric(dev_labels, preds)
        if score > best_score:
            best_t, best_score = round(float(t), 2), score
    return best_t
