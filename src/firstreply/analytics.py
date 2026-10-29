"""SLA analytics: first-response time, breach rate, backlog, volume forecast and staffing.

Writes CSVs to outputs/ and an "sla" section to outputs/numbers.json.
Run: python -m firstreply.analytics   (needs data/tweets.parquet; see scripts/)
"""
import numpy as np
import pandas as pd

from firstreply import db, numbers, staffing

OUT = db.ROOT / "outputs"
FORECAST_BRAND = "AmazonHelp"  # largest brand; e-commerce, same domain as the Bitext intents
AHT_MINUTES = 6.0  # ASSUMPTION: agent minutes to read, check and send a first reply (not in the data)
OCCUPANCY = 0.85  # ASSUMPTION: share of a paid hour an agent spends on tickets


def overall(con):
    row = con.sql(f"""
        SELECT count(*) AS tickets,
               count(*) FILTER (WHERE frt_minutes IS NOT NULL) AS answered,
               count(DISTINCT brand) AS brands,
               median(frt_minutes) AS median_frt,
               quantile_cont(frt_minutes, 0.9) AS p90_frt,
               avg((frt_minutes > {db.SLA_MINUTES})::INT) AS breach
        FROM tickets
    """).df().iloc[0]
    return {
        "tickets": int(row.tickets),
        "answered": int(row.answered),
        "answered_pct": round(100 * row.answered / row.tickets, 1),
        "brands": int(row.brands),
        "median_frt_min": round(float(row.median_frt), 1),
        "p90_frt_min": round(float(row.p90_frt), 1),
        "breach_pct": round(100 * float(row.breach), 1),
    }


def sla_sensitivity(con):
    """Breach rate if the SLA were 15 min, 1 h or 4 h - shows how much the target choice matters."""
    out = {}
    for minutes in (15, 60, 240):
        share = con.execute(f"SELECT avg((frt_minutes > {minutes})::INT) FROM tickets WHERE frt_minutes IS NOT NULL").fetchone()[0]
        out[f"breach_pct_at_{minutes}min"] = round(100 * share, 1)
    return out


def forecast(volume):
    """Forecast the last 2 weeks of hourly volume from the first 6 with three simple baselines.

    WAPE = sum(|actual - forecast|) / sum(actual). Lower is better.
    """
    v = volume.set_index("hour_start")["tickets"].astype(float)
    split = v.index.min() + pd.Timedelta(weeks=6)
    train, test = v[v.index < split], v[v.index >= split]
    hour_of_week = lambda idx: idx.day_of_week * 24 + idx.hour  # noqa: E731

    by_how = train.groupby(hour_of_week(train.index)).mean()
    preds = {
        # same hour, one week earlier (uses the real value from last week)
        "seasonal_naive": v.shift(24 * 7)[test.index],
        # average of the same hour-of-week across the 6 training weeks
        "hour_of_week_mean": pd.Series(by_how.loc[hour_of_week(test.index)].values, index=test.index),
        # flat: average hour in the last training week
        "flat_last_week_mean": pd.Series(train[-24 * 7:].mean(), index=test.index),
    }
    wape = {name: round(100 * float((test - p).abs().sum() / test.sum()), 1) for name, p in preds.items()}
    best = min(wape, key=wape.get)
    frame = pd.DataFrame({"actual": test, **preds})
    # Next-week forecast for staffing = the winning method (seasonal naive): last observed week, by hour-of-week.
    last_week = v[-24 * 7:]
    next_week = pd.Series(last_week.values, index=hour_of_week(last_week.index))
    return wape, best, frame, next_week


def staffing_plan(next_week):
    """Agents per hour-of-week for the forecast brand, by both methods."""
    rows = []
    for how, tph in next_week.items():
        rows.append({
            "hour_of_week": int(how),
            "weekday": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][how // 24],
            "hour_utc": int(how % 24),
            "forecast_tickets": round(float(tph), 1),
            "agents_workload": staffing.workload_agents(tph, AHT_MINUTES, OCCUPANCY),
            "agents_erlang": staffing.erlang_agents(tph, AHT_MINUTES, db.SLA_MINUTES, 0.9),
        })
    return pd.DataFrame(rows)


def main():
    con = db.connect()
    db.run(con, "01_tickets")
    OUT.mkdir(exist_ok=True)

    by_brand = db.run(con, "02_frt_by_brand")
    by_brand.to_csv(OUT / "sla_by_brand.csv", index=False)
    by_time = db.run(con, "03_frt_by_hour_weekday")
    by_time.to_csv(OUT / "sla_by_hour_weekday.csv", index=False)
    backlog = db.run(con, "04_backlog")
    backlog.to_csv(OUT / "backlog_hourly.csv", index=False)

    con.execute(f"SET VARIABLE brand = '{FORECAST_BRAND}'")
    volume = db.run(con, "05_hourly_volume")
    wape, best, fc, next_week = forecast(volume)
    fc.to_csv(OUT / "forecast_test_weeks.csv")
    plan = staffing_plan(next_week)
    plan.to_csv(OUT / "staffing_plan.csv", index=False)

    worst_hour = by_time.groupby("hour_utc").apply(
        lambda g: np.average(g.breach_pct, weights=g.tickets), include_groups=False)
    by_day = by_time.groupby("weekday").apply(
        lambda g: np.average(g.breach_pct, weights=g.tickets), include_groups=False)
    fb = by_brand.set_index("brand").loc[FORECAST_BRAND]
    fast = by_brand.sort_values("median_frt_min").iloc[0]
    slow = by_brand.sort_values("median_frt_min").iloc[-1]
    stats = {
        **overall(con),
        **sla_sensitivity(con),
        "sla_minutes": db.SLA_MINUTES,
        "window": f"{db.WINDOW_START[:10]} to 2017-12-03",
        "brands_with_1000_plus": int(len(by_brand)),
        "fastest_brand": fast.brand, "fastest_brand_median_min": float(fast.median_frt_min),
        "slowest_brand": slow.brand, "slowest_brand_median_min": float(slow.median_frt_min),
        "breach_pct_by_weekday": {d: round(float(v), 1) for d, v in by_day.items()},
        "forecast_brand_median_frt_min": float(fb.median_frt_min),
        "forecast_brand_p90_frt_min": float(fb.p90_frt_min),
        "forecast_brand_breach_pct": float(fb.breach_pct),
        "worst_hour_utc": int(worst_hour.idxmax()), "worst_hour_breach_pct": round(float(worst_hour.max()), 1),
        "best_hour_utc": int(worst_hour.idxmin()), "best_hour_breach_pct": round(float(worst_hour.min()), 1),
        "backlog_peak": int(backlog.waiting.max()),
        "backlog_median": int(backlog.waiting.median()),
        "forecast_brand": FORECAST_BRAND,
        "forecast_wape_pct": wape,
        "forecast_best_method": best,
        "forecast_brand_tickets_per_week": int(next_week.sum()),
        "staffing_aht_min": AHT_MINUTES,
        "staffing_occupancy": OCCUPANCY,
        "staffing_peak_agents_workload": int(plan.agents_workload.max()),
        "staffing_peak_agents_erlang": int(plan.agents_erlang.max()),
        "staffing_agent_hours_per_week_workload": int(plan.agents_workload.sum()),
        "staffing_agent_hours_per_week_erlang": int(plan.agents_erlang.sum()),
    }
    numbers.save_section("sla", stats)
    for k, v in stats.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
