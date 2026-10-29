"""ROI in agent-hours: what triage suggestions + draft replies could save, with every assumption stated.

Measured inputs come from outputs/numbers.json (ticket volume, model accuracy, LLM cost).
Everything else is an ASSUMPTION with a low / base / high value. The pilot (docs/MEMO.md) replaces the
assumptions with numbers from the approval log (seconds per ticket, share of drafts sent unchanged).
Run: python -m firstreply.roi   (after analytics and evals)
"""
import pandas as pd

from firstreply import db, numbers

# name: (low, base, high, what it means). "low" = the pessimistic end for savings.
ASSUMPTIONS = {
    "read_route_min": (0.5, 1.0, 1.5, "minutes an agent spends today reading a ticket and choosing the queue"),
    "write_reply_min": (2.0, 3.0, 4.0, "minutes to write a first reply from scratch today"),
    "route_time_cut": (0.3, 0.5, 0.7, "share of read+route time saved when the suggested queue is right"),
    "wrong_fix_min": (0.5, 0.25, 0.1, "extra minutes to notice and fix a wrong suggestion"),
    "draft_used_share": (0.3, 0.5, 0.7, "share of tickets where the draft is sent with only light edits"),
    "draft_time_cut": (0.4, 0.6, 0.8, "share of writing time saved when the draft is used"),
}
WEEKS_PER_YEAR = 52
FTE_HOURS_PER_WEEK = 40  # ASSUMPTION: one full-time agent


def routing_minutes(accuracy, a):
    """Minutes saved on routing one ticket. accuracy = share of correct queue suggestions (0-1)."""
    return accuracy * a["read_route_min"] * a["route_time_cut"] - (1 - accuracy) * a["wrong_fix_min"]


def drafting_minutes(a):
    """Minutes saved on writing one reply. Not measured yet: the pilot's approval log measures it."""
    return a["draft_used_share"] * a["write_reply_min"] * a["draft_time_cut"]


def minutes_saved_per_ticket(accuracy, a):
    return routing_minutes(accuracy, a) + drafting_minutes(a)


def scenario(accuracy, tickets_per_week, a, llm_cost_per_1000=0.0):
    per_ticket = minutes_saved_per_ticket(accuracy, a)
    hours_week = per_ticket * tickets_per_week / 60
    return {
        "minutes_saved_per_ticket": round(per_ticket, 2),
        "routing_only_hours_per_week": round(routing_minutes(accuracy, a) * tickets_per_week / 60, 1),
        "agent_hours_saved_per_week": round(hours_week, 1),
        "fte_saved": round(hours_week / FTE_HOURS_PER_WEEK, 2),
        "agent_hours_saved_per_year": round(hours_week * WEEKS_PER_YEAR),
        "llm_cost_per_week_usd": round(llm_cost_per_1000 * tickets_per_week / 1000, 2),
    }


def pick(level):
    i = {"low": 0, "base": 1, "high": 2}[level]
    return {k: v[i] for k, v in ASSUMPTIONS.items()}


def sensitivity(accuracy, tickets_per_week):
    """Move one assumption at a time from low to high, others at base. Biggest swing first."""
    base = pick("base")
    rows = []
    for name, (low, _, high, meaning) in ASSUMPTIONS.items():
        lo = scenario(accuracy, tickets_per_week, {**base, name: low})["agent_hours_saved_per_week"]
        hi = scenario(accuracy, tickets_per_week, {**base, name: high})["agent_hours_saved_per_week"]
        rows.append({"assumption": name, "low_value": low, "high_value": high, "hours_week_at_low": lo,
                     "hours_week_at_high": hi, "swing": round(abs(hi - lo), 1), "meaning": meaning})
    return pd.DataFrame(rows).sort_values("swing", ascending=False)


def main():
    n = numbers.load()
    sla, triage = n["sla"], n["triage"]
    models = {name: {**m, "interim": False} for name, m in triage["models"].items()}
    # While the full LLM run is missing, also show the LLMs' partial (cached-subset) accuracy, clearly marked.
    interim = triage.get("interim_cached_subset") or {}
    for name, m in interim.get("models", {}).items():
        if name not in models:
            models[f"{name} (interim, n={interim['tickets']})"] = {**m, "interim": True}
    tickets_per_week = sla["forecast_brand_tickets_per_week"]
    workload_hours = sla["staffing_agent_hours_per_week_workload"]
    out = {"brand": sla["forecast_brand"], "tickets_per_week": tickets_per_week,
           "staffed_agent_hours_per_week": workload_hours, "assumptions": ASSUMPTIONS, "by_model": {},
           "drafting_hours_per_week": {lvl: round(drafting_minutes(pick(lvl)) * tickets_per_week / 60, 1)
                                       for lvl in ("low", "base", "high")}}
    for name, m in models.items():
        acc = m["accuracy_pct"] / 100
        cost = m["cost_per_1000_usd"]
        out["by_model"][name] = {
            "accuracy_used": round(acc, 3), "interim": m["interim"],
            **{level: scenario(acc, tickets_per_week, pick(level), cost) for level in ("low", "base", "high")},
        }
        base_hours = out["by_model"][name]["base"]["agent_hours_saved_per_week"]
        out["by_model"][name]["base_share_of_staffed_hours_pct"] = round(100 * base_hours / workload_hours, 1)
    # break-even: accuracy at which routing alone saves nothing (wrong-fix cost = right-route saving)
    b = pick("base")
    out["routing_break_even_accuracy_pct"] = round(
        100 * b["wrong_fix_min"] / (b["read_route_min"] * b["route_time_cut"] + b["wrong_fix_min"]), 1)
    best = max(models, key=lambda k: models[k]["accuracy_pct"])
    sens = sensitivity(models[best]["accuracy_pct"] / 100, tickets_per_week)
    sens.to_csv(db.ROOT / "outputs" / "roi_sensitivity.csv", index=False)
    out["sensitivity_model"] = best
    out["biggest_driver"] = sens.iloc[0].assumption
    numbers.save_section("roi", out)
    for name, r in out["by_model"].items():
        print(name, {lvl: (r[lvl]["routing_only_hours_per_week"], r[lvl]["agent_hours_saved_per_week"])
                     for lvl in ("low", "base", "high")})
    print(sens.to_string(index=False))


if __name__ == "__main__":
    main()
