"""Convert raw/twcs/twcs.csv (2.8M tweets) to data/tweets.parquet with a proper UTC timestamp.

Done once with DuckDB, so the 500 MB CSV never sits in pandas memory.
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "raw" / "twcs" / "twcs.csv"
OUT = ROOT / "data" / "tweets.parquet"


def main():
    OUT.parent.mkdir(exist_ok=True)
    con = duckdb.connect()
    con.execute("SET memory_limit='3GB'; SET threads=4;")
    con.execute(f"""
        COPY (
            SELECT
                CAST(tweet_id AS BIGINT) AS tweet_id,
                CAST(author_id AS VARCHAR) AS author_id,
                inbound,
                -- "Tue Oct 31 22:10:47 +0000 2017" -> timestamp in UTC
                strptime(created_at, '%a %b %d %H:%M:%S %z %Y') AT TIME ZONE 'UTC' AS created_at,
                text,
                CAST(in_response_to_tweet_id AS BIGINT) AS in_response_to_tweet_id
            FROM read_csv('{SRC}', header=true, quote='"', escape='"',
                          types={{'tweet_id': 'VARCHAR', 'in_response_to_tweet_id': 'VARCHAR',
                                  'response_tweet_id': 'VARCHAR', 'inbound': 'BOOLEAN'}})
        ) TO '{OUT}' (FORMAT parquet)
    """)
    n = con.execute(f"SELECT count(*) FROM '{OUT}'").fetchone()[0]
    print(f"wrote {OUT.name}: {n:,} tweets")


if __name__ == "__main__":
    main()
