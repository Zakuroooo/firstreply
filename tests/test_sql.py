"""Run the real SQL files on a tiny hand-made set of tweets where the right answers are known."""
from datetime import datetime

import pandas as pd
import pytest

from firstreply import db

T0 = datetime(2017, 10, 9, 10, 0, 0)


def ts(minutes):
    return T0 + pd.Timedelta(minutes=minutes)


@pytest.fixture
def con(tmp_path, monkeypatch):
    rows = [
        # tweet_id, author_id, inbound, created_at, text, in_response_to_tweet_id
        (1, "c1", True, ts(0), "where is my parcel", None),        # ticket A
        (2, "BrandX", False, ts(30), "sorry, DM us", 1),           # first reply to A after 30 min
        (3, "BrandX", False, ts(90), "any update?", 1),            # later reply: must be ignored
        (4, "c1", True, ts(95), "still waiting", 2),               # customer follow-up: not a ticket
        (5, "c2", True, ts(10), "refund please", None),            # ticket B, answered after 120 min
        (6, "BrandX", False, ts(130), "we can help", 5),
        (7, "c3", True, ts(20), "hello?", None),                   # ticket C, never answered
        (8, "c4", True, datetime(2017, 10, 1), "too early", None),  # outside the window
    ]
    df = pd.DataFrame(rows, columns=["tweet_id", "author_id", "inbound", "created_at", "text",
                                     "in_response_to_tweet_id"]).astype({"in_response_to_tweet_id": "Int64"})
    path = tmp_path / "tweets.parquet"
    df.to_parquet(path)
    monkeypatch.setattr(db, "TWEETS", path)
    c = db.connect(sla_minutes=60)
    db.run(c, "01_tickets")
    return c


def test_tickets_and_first_response(con):
    t = con.sql("SELECT ticket_id, brand, frt_minutes FROM tickets ORDER BY ticket_id").df()
    assert t.ticket_id.tolist() == [1, 5, 7]          # follow-ups and out-of-window tweets excluded
    assert t.frt_minutes.tolist()[:2] == [30.0, 120.0]  # earliest reply wins
    assert pd.isna(t.frt_minutes.iloc[2])               # unanswered
    assert t.brand.tolist()[:2] == ["BrandX", "BrandX"]


def test_breach_by_hour(con):
    r = db.run(con, "03_frt_by_hour_weekday")
    assert r.tickets.sum() == 2
    assert r.breach_pct.iloc[0] == 50.0                 # one of two answered tickets is over 60 min


def test_backlog_counts_waiting_tickets(con):
    b = db.run(con, "04_backlog").set_index("hour_end")
    # at 11:00 ticket A is answered (10:30) but B is still waiting (answered 12:10)
    assert b.loc[pd.Timestamp("2017-10-09 11:00:00"), "waiting"] == 1
    assert b.loc[pd.Timestamp("2017-10-09 13:00:00"), "waiting"] == 0


def test_hourly_volume_fills_empty_hours(con):
    con.execute("SET VARIABLE brand = 'BrandX'")
    v = db.run(con, "05_hourly_volume")
    assert len(v) == 8 * 7 * 24                          # every hour of the 8-week window
    assert v.tickets.sum() == 2
