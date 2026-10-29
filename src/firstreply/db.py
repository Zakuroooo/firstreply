"""Small helpers to run the numbered SQL files in sql/ against the tweets Parquet file."""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
SQL = ROOT / "sql"
TWEETS = ROOT / "data" / "tweets.parquet"

# Analysis window: 8 full weeks (Mon 9 Oct - Sun 3 Dec 2017, UTC). Days before 9 Oct are thin (scrape ramp-up).
WINDOW_START = "2017-10-09 00:00:00"
WINDOW_END = "2017-12-04 00:00:00"
SLA_MINUTES = 60  # assumed first-response target for social support; change here, everything re-runs


def connect(sla_minutes=SLA_MINUTES, brand=None):
    con = duckdb.connect()
    con.execute("SET memory_limit='3GB'; SET threads=4;")
    con.execute(f"CREATE VIEW tweets AS SELECT * FROM '{TWEETS}'")
    con.execute(f"SET VARIABLE window_start = TIMESTAMP '{WINDOW_START}'")
    con.execute(f"SET VARIABLE window_end = TIMESTAMP '{WINDOW_END}'")
    con.execute(f"SET VARIABLE sla_minutes = {float(sla_minutes)}")
    con.execute(f"SET VARIABLE brand = '{brand or ''}'")
    return con


def run(con, name):
    """Run sql/<name>.sql and return a DataFrame (or None for CREATE statements)."""
    rel = con.sql((SQL / f"{name}.sql").read_text())
    return rel.df() if rel is not None else None
