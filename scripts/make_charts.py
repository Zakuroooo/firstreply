"""Draw the README charts from the committed outputs/ tables. No data download needed.

    python scripts/make_charts.py   # writes docs/images/*.png
"""
import json
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
IMG = ROOT / "docs" / "images"
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"
SOURCE = "Source: Customer Support on Twitter (Kaggle, CC BY-NC-SA 4.0), Oct 9 - Dec 3 2017, UTC."

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
})


def finish(fig, name, note):
    fig.text(0.01, 0.01, note, fontsize=8.5, color=MUTED)
    fig.savefig(IMG / f"{name}.png", dpi=110)
    plt.close(fig)


def triage(numbers):
    m = numbers["triage"]["models"]
    rows = [("TF-IDF + logistic regression", m["tfidf_logreg"]), ("gpt-oss-20b (zero-shot)", m["gpt-oss-20b"]),
            ("gpt-oss-120b (zero-shot)", m["gpt-oss-120b"])]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    for i, (name, r) in enumerate(rows):
        lo, hi = r["accuracy_ci95"]
        colour = MUTED if i == 0 else BLUE
        ax.plot([lo, hi], [i, i], color=colour, lw=2, solid_capstyle="round")
        ax.plot(r["accuracy_pct"], i, "o", ms=9, color=colour, mec=SURFACE, mew=2)
        ax.text(r["accuracy_pct"], i + 0.28, f"{r['accuracy_pct']:.1f}%  (95% CI {lo:.1f}-{hi:.1f})",
                ha="center", fontsize=10)
    ax.set_yticks(range(len(rows)), [n for n, _ in rows])
    ax.set_ylim(-0.4, len(rows) - 0.3)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Accuracy on the same 300 held-out real tweets (%)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Ticket triage accuracy, 8 queues", loc="left", fontweight="bold")
    fig.subplots_adjust(left=0.27, right=0.97, top=0.88, bottom=0.27)
    finish(fig, "triage-accuracy", "Labels: one AI-assisted labelling pass, not yet independently re-checked. "
                                   "CIs: bootstrap. Source: outputs/numbers.json")


def breach_heatmap(numbers):
    d = pd.read_csv(OUT / "sla_by_hour_weekday.csv")
    grid = d.pivot(index="weekday", columns="hour_utc", values="breach_pct")
    order = d.drop_duplicates("weekday").sort_values("dow").weekday
    grid = grid.loc[order]
    fig, ax = plt.subplots(figsize=(11, 3.9))
    im = ax.imshow(grid.values, cmap="Blues", aspect="auto", vmin=0, vmax=50)
    ax.set_xticks(range(0, 24, 2), [f"{h:02d}" for h in range(0, 24, 2)])
    ax.set_yticks(range(len(order)), [w[:3] for w in order])
    ax.set_xlabel("Hour the ticket arrived (UTC)")
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, pad=0.01)
    cb.set_label("% answered tickets with first reply > 60 min")
    cb.outline.set_visible(False)
    s = numbers["sla"]
    ax.set_title(f"60-min SLA breach rate by weekday and hour (overall {s['breach_pct']}%, "
                 f"worst hour {s['worst_hour_utc']:02d}:00 = {s['worst_hour_breach_pct']}%)",
                 loc="left", fontweight="bold")
    fig.subplots_adjust(left=0.05, right=1.0, top=0.88, bottom=0.22)
    finish(fig, "sla-breach-heatmap", SOURCE + " Table: outputs/sla_by_hour_weekday.csv")


def forecast(numbers):
    f = pd.read_csv(OUT / "forecast_test_weeks.csv", parse_dates=["hour_start"])
    w = numbers["sla"]["forecast_wape_pct"]
    fig, ax = plt.subplots(figsize=(11, 3.9))
    ax.plot(f.hour_start, f.actual, color=MUTED, lw=1.4, label="Actual tickets per hour")
    ax.plot(f.hour_start, f.seasonal_naive, color=BLUE, lw=1.4,
            label=f"Forecast: same hour last week (WAPE {w['seasonal_naive']}%)")
    ax.set_ylabel("Tickets per hour")
    ax.legend(loc="upper left", frameon=False, fontsize=10, ncols=2)
    ax.set_ylim(0, f[["actual", "seasonal_naive"]].max().max() * 1.25)
    ax.set_title(f"{numbers['sla']['forecast_brand']} hourly volume, 2 test weeks "
                 f"(flat baseline WAPE {w['flat_last_week_mean']}%)", loc="left", fontweight="bold")
    fig.subplots_adjust(left=0.07, right=0.98, top=0.88, bottom=0.2)
    finish(fig, "forecast-test-weeks", "The forecast copies the same hour a week earlier, so a near-empty stretch a "
                                       "week before shows up as the Nov 24-25 dip. Table: outputs/forecast_test_weeks.csv")


def staffing(numbers):
    p = pd.read_csv(OUT / "staffing_plan.csv")
    s = numbers["sla"]
    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.step(p.hour_of_week, p.agents_workload, where="mid", color=BLUE, lw=2,
            label=f"Workload formula (peak {s['staffing_peak_agents_workload']}, "
                  f"{s['staffing_agent_hours_per_week_workload']:,} agent-h/week)")
    ax.step(p.hour_of_week, p.agents_erlang, where="mid", color=ORANGE, lw=2,
            label=f"Erlang C (peak {s['staffing_peak_agents_erlang']}, "
                  f"{s['staffing_agent_hours_per_week_erlang']:,} agent-h/week)")
    days = p.drop_duplicates("weekday")
    ax.set_xticks(days.hour_of_week + 12, days.weekday)
    for x in days.hour_of_week[1:]:
        ax.axvline(x - 0.5, color=GRID, lw=1)
    ax.grid(axis="x", visible=False)
    ax.set_xlim(-0.5, 167.5)
    ax.set_ylim(0, max(p.agents_workload.max(), p.agents_erlang.max()) + 4)
    ax.set_ylabel("Agents on shift")
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.legend(loc="upper left", frameon=False, fontsize=10, ncols=2)
    ax.set_title(f"{s['forecast_brand']} staffing plan by hour of week (UTC)", loc="left", fontweight="bold")
    fig.subplots_adjust(left=0.07, right=0.98, top=0.88, bottom=0.17)
    finish(fig, "staffing-plan", f"Assumed: {s['staffing_aht_min']:.0f}-min handle time, "
                                 f"{s['staffing_occupancy']:.0%} occupancy. Table: outputs/staffing_plan.csv")


if __name__ == "__main__":
    IMG.mkdir(parents=True, exist_ok=True)
    nums = json.loads((OUT / "numbers.json").read_text())
    triage(nums)
    breach_heatmap(nums)
    forecast(nums)
    staffing(nums)
    print("wrote", ", ".join(sorted(p.name for p in IMG.glob("*.png"))))
