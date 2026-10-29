# 02 - Forecasting volume and staffing

## Why forecast?
To decide how many agents to put on each hour **before** the hour arrives. Too few = breaches.
Too many = paying people to wait.

## The three baselines we tried (`src/firstreply/analytics.py`)
We train on the first 6 weeks and test on the last 2 weeks of hourly ticket counts for one brand.
1. **Seasonal naive**: "next Monday 10 am will look like last Monday 10 am." Just copy last week.
2. **Hour-of-week mean**: average of all past Mondays at 10 am.
3. **Flat**: one number for every hour = last week's average hour. This is the "no forecasting" baseline.

They are called **baselines** because any fancy model must beat them to be worth its complexity.

## WAPE (how we score a forecast)
WAPE = sum of |actual - forecast| / sum of actual.
"For every 100 tickets that arrived, how many did we get wrong?" Lower is better. We use WAPE, not average
percentage error, because quiet hours with 2 tickets would explode a percentage.

> Hinglish: WAPE batata hai ki har 100 ticket pe forecast kitne ticket se galat tha.

## AHT and occupancy (assumptions, not data)
- **AHT (average handle time)**: minutes an agent spends on one ticket. The tweets do not tell us this, so
  we ASSUME 6 minutes for a first reply. Change `AHT_MINUTES` and everything re-runs.
- **Occupancy**: share of a paid hour an agent is really working tickets. We ASSUME 85%. Nobody works 60/60.

## Two staffing methods (`src/firstreply/staffing.py`)
1. **Workload**: agents = tickets per hour x AHT / 60 / occupancy, rounded up.
   Example: 60 tickets x 6 min = 360 minutes = 6 hours of work. 6 / 0.85 = 7.06, so 8 agents.
2. **Erlang C**: the classic call-centre formula. Tickets arrive at random, so even with "enough" agents some
   tickets wait. Erlang C gives the chance a ticket waits, and from that the share answered within the SLA.
   We add agents until 90% are answered within 60 minutes.

Workload ignores randomness. Erlang C assumes tickets arrive randomly and agents take them one at a time,
which is roughly true for chat, less true for email. Showing both is honest: the real answer is in between
and must be checked in a pilot.

> Hinglish: Erlang C ek formula hai jo batata hai ki random aate tickets ke liye kitne agents chahiye taaki 90% ko time pe reply mile.

## FTE
Full-time equivalent: 40 agent-hours per week = 1 FTE. "Saves 120 hours a week" = "about 3 FTE".
