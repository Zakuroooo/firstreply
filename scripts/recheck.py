"""Second-labeller check: you label 50 test tweets blind, then compare with evalset/labels.csv.

    python scripts/recheck.py sheet   # writes evalset/recheck_50.csv with empty my_queue / my_urgent columns
    python scripts/recheck.py score   # after you fill it in: agreement %, Cohen's kappa, every disagreement

Label with docs/LABEL-GUIDE.md open. Do not look at labels.csv while filling the sheet.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SHEET = ROOT / "evalset" / "recheck_50.csv"
QUEUES = ["delivery", "order_change", "refund_return", "billing_payment", "account",
          "complaint_feedback", "talk_to_human", "other"]


def make_sheet():
    if SHEET.exists():
        sys.exit(f"{SHEET.name} already exists - delete it first if you really want a new sample")
    tickets = pd.read_csv(ROOT / "evalset" / "tickets.csv")
    test = tickets[tickets["split"] == "test"]
    sample = test.sample(n=50, random_state=7)[["eval_id", "brand", "clean_text"]]
    sample["my_queue"] = ""
    sample["my_urgent"] = ""
    sample.to_csv(SHEET, index=False)
    print(f"wrote {SHEET} - queues: {', '.join(QUEUES)}; urgent: yes/no")


def kappa(a, b):
    # Cohen's kappa: agreement beyond what two random labellers with the same label mix would reach
    observed = (a == b).mean()
    labels = set(a) | set(b)
    expected = sum((a == k).mean() * (b == k).mean() for k in labels)
    return (observed - expected) / (1 - expected) if expected < 1 else 1.0


def score():
    mine = pd.read_csv(SHEET, dtype=str).fillna("")
    if (mine["my_queue"] == "").any() or (mine["my_urgent"] == "").any():
        sys.exit("fill every my_queue and my_urgent cell first")
    bad = set(mine["my_queue"]) - set(QUEUES)
    if bad:
        sys.exit(f"unknown queue names: {bad}")
    gold = pd.read_csv(ROOT / "evalset" / "labels.csv", dtype=str)
    df = mine.merge(gold, on="eval_id")
    df["my_urgent"] = df["my_urgent"].str.lower().isin(["yes", "true", "y", "1"])
    df["urgent"] = df["urgent"] == "True"

    q_agree = (df["my_queue"] == df["label"]).mean()
    u_agree = (df["my_urgent"] == df["urgent"]).mean()
    print(f"queue  agreement {q_agree:.0%}  kappa {kappa(df['my_queue'], df['label']):.2f}")
    print(f"urgent agreement {u_agree:.0%}  kappa {kappa(df['my_urgent'], df['urgent']):.2f}")
    diff = df[(df["my_queue"] != df["label"]) | (df["my_urgent"] != df["urgent"])]
    print(f"\n{len(diff)} disagreements (decide who is right using LABEL-GUIDE.md, fix labels.csv if it was wrong):")
    for _, r in diff.iterrows():
        print(f"- #{r['eval_id']} you={r['my_queue']}/{r['my_urgent']} file={r['label']}/{r['urgent']}: {r['clean_text'][:90]}")


if __name__ == "__main__":
    {"sheet": make_sheet, "score": score}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
