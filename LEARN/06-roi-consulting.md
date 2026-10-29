# 06 - ROI and the consulting side

## ROI (return on investment)
What you get back compared with what you spend. Here we measure the "get back" in **agent-hours saved per
week**, because hours are what a support manager controls. Money = hours x hourly cost, and that cost
differs by country, so we leave it as a simple multiply for the client.

> Hinglish: ROI matlab jo lagaya uske badle kitna wapas mila - yahan hum agent ke ghante bachne mein naapte hain.

## Our ROI formula (`src/firstreply/roi.py`)
Per ticket, minutes saved =
- **routing**: accuracy x (read+route minutes x share saved) - (1 - accuracy) x minutes to fix a wrong suggestion
- **drafting**: share of drafts used x write minutes x share of writing saved
Hours per week = minutes per ticket x tickets per week / 60.

Measured inputs: tickets per week (from the forecast), accuracy (from the eval), LLM cost (from the eval).
Everything else is an **assumption** with a low, base and high value, written in the code.

## Break-even
If suggestions are wrong too often, agents waste time fixing them and routing saves nothing - or costs time.
The break-even accuracy is where the two cancel out. A model below it should not be switched on.

## Sensitivity analysis
Change one assumption at a time from low to high, keep the others at base, and see how much the answer moves.
The assumption with the biggest swing is the one to measure first in a pilot. This is how a consultant
says "I am not sure, but I know exactly what I am not sure about".

> Hinglish: Sensitivity analysis batata hai kaunsa assumption galat hua toh result sabse zyada badlega - pilot mein pehle wahi naapo.

## Process map
A picture of the steps a ticket goes through, today (current state) and after the change (future state).
It shows where time goes and where the tool fits. See `docs/MEMO.md`.

## Rollout plan
Never switch on for everyone at once:
1. **Shadow**: model runs, agents do not see it, we compare.
2. **Assist**: agents see suggestions for one queue or one shift; every decision is logged.
3. **Scale**: widen only if the logged numbers beat the agreed bar.
Each step has a clear "stop" rule.

## Risks to always name
Wrong routing, a bad draft sent in a hurry, privacy (customer data sent to an API), cost creep, agents
trusting the tool too much, and the data being old or from a different channel.
