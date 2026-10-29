"""Check that data/tweets.parquet is the full, unchanged Kaggle dataset.

Two checks, so a mirror copy can be trusted:
1. Row count equals the Kaggle file's 2,811,774 tweets.
2. Every one of the 550 tweets in evalset/ (sampled from the original Kaggle download) is found
   with the same cleaned text.
"""
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from firstreply import db, text  # noqa: E402

EXPECTED_ROWS = 2_811_774


def main():
    con = duckdb.connect()
    n = con.execute(f"SELECT count(*) FROM '{db.TWEETS}'").fetchone()[0]
    ev = pd.concat([pd.read_csv(db.ROOT / "evalset" / "tickets.csv")[["ticket_id", "clean_text"]],
                    pd.read_csv(db.ROOT / "evalset" / "urgency_holdout.csv")[["ticket_id", "clean_text"]]])
    ids = ",".join(str(int(i)) for i in ev.ticket_id)
    found = con.execute(f"SELECT tweet_id AS ticket_id, text FROM '{db.TWEETS}' WHERE tweet_id IN ({ids})").df()
    found["now"] = found.text.map(text.clean)
    m = ev.merge(found, on="ticket_id", how="left")
    same = int((m.now == m.clean_text).sum())
    print(f"rows: {n:,} (expected {EXPECTED_ROWS:,}); evalset tweets matched: {same}/{len(ev)}")
    if n != EXPECTED_ROWS or same != len(ev):
        sys.exit("data check FAILED")
    print("data check passed")


if __name__ == "__main__":
    main()
