# 25 consulting / FDE interview questions - with answers

Say answers out loud. Short sentences. Number first, then why, then the limit.
Numbers come from `outputs/numbers.json`.

## The project in one go
**1. Tell me about FirstReply in one minute.**
I took 724,846 real support tickets from Twitter and measured how fast brands first reply. Median is about
24 minutes, but 35% miss a one-hour target and the slowest 10% wait about 9 hours. Then I asked: would AI
triage help? I tested a classical model and two LLMs on the same 300 hand-labelled tweets, with cost and
latency. The classical model fell from 99.9% on clean data to 20% on real tweets. LLMs reached 67-72% on
the same 300 tweets, for under 10 cents per 1,000 tickets. I wrote it up as a memo: what to pilot, how many
hours it may save, and how to roll it out safely with a human approving every reply.

**2. Why this project and not another classifier?**
Because a classifier score alone does not help a support leader decide anything. They need: where are we
slow, how many people do we need, what does the tool cost, and how much time does it really save. So I built
the SLA analysis and the business case around the model, not just the model.

## SLA and analytics
**3. What is an SLA, and how did you choose 60 minutes?**
A promise about speed - here, first reply within 60 minutes. The data has no official SLA, so I assumed 60,
common for social support. Because it is my choice, I also show 15 minutes (58.6% breach) and 4 hours (17.2%).

**4. Why median and p90, not the average?**
A few tickets wait days and pull the average up. The median shows a normal customer (23.7 min). p90 shows the
bad tail (535 min). Managers fix the tail, because that is where angry customers are.

**5. How did you define a ticket and first response?**
A ticket is a customer tweet that starts a conversation, not a reply. First response is the earliest brand
tweet that replies directly to it. I tested this SQL on a tiny hand-made dataset where I knew the right answer.

**6. What did the hour and weekday analysis show?**
Breach is worst at 04:00 UTC (43.6%) and on weekends (Saturday 42.1%) and best on Wednesday (30%). Staffing does
not follow demand. Caveat: times are UTC, so "4 am" is not local time for every brand.

**7. How did you forecast volume?**
I compared three simple baselines on the last 2 weeks: same hour last week, average of that hour-of-week,
and a flat number. Same-hour-last-week won with 27.6% WAPE vs 34.9% flat. I started simple on purpose: a fancy
model must beat this to be worth it.

**8. How did you get from forecast to agents?**
Two ways. Workload: tickets x handle time / occupancy - 1,556 agent-hours a week, peak 15 agents. Erlang C,
which models random arrivals: 1,381 hours, peak 13. Handle time 6 minutes and 85% occupancy are assumptions,
so in a real project I would measure them first.

## Models and evals
**9. Why did the classical model drop from 99.9% to 20%?**
Domain shift. It learned from tidy synthetic questions; real tweets have slang, sarcasm, emoji, other languages.
Also more than half of real tweets are complaints or "other", which the training data barely has. Even on the
6 queues the training data covers, it got only 30%. Unknown text fell into the biggest training class.

**10. Isn't that an unfair test for the classical model?**
Partly, and I say so. It is the realistic test for "train on public data, deploy on real tickets", which is
what many teams try first. The fair next test is a classical model trained on a few thousand of the team's own
labelled tickets. If it reaches LLM accuracy, I would choose it - near-zero cost and fully explainable.

**11. How did you make the comparison fair?**
Same 300 test tickets, same cleaning, same scoring code, labels written before any model ran. Threshold and
few-shot examples chosen on a separate dev set. LLM calls cached so anyone gets the same numbers.

**12. Why report macro-F1 and confidence intervals?**
Accuracy hides small classes. Macro-F1 gives every queue equal weight. And 300 tickets is small, so I
bootstrap a 95% interval. Example: 120b at 72.3% vs 20b at 67.0% - the intervals overlap, so I do not claim 120b is
better. Classical vs LLM intervals do not overlap, so that gap is real.

**13. Were the LLM numbers always on all 300 tickets?**
No. At first only 154 of 300 calls were cached, so I scored every model on exactly those 154 and labelled it
interim instead of filling the gap with estimates. Then I finished the run: 20b 67.0%, 120b 72.3% on all 300.
Every call is cached, so anyone can re-run it without an API key.

**14. What do cost and latency look like?**
About 360 input and 51 output tokens per ticket. That is $0.04 per 1,000 tickets on the small model and $0.08 on
the large one, about $1 a week for a team with 12,540 tickets. Median latency about 0.6 seconds, fine for a queue.

**15. What kinds of mistakes do the LLMs make?**
Mostly borderline cases: "your store sells expired milk" - complaint or refund? And tweets with no context, like
just a phone number. Some of these are label ambiguity, which is why the next step is a second labeller and an
agreement score.

## Urgency and human-in-the-loop
**16. Why can the AI only raise urgency, never lower it?**
Missing a fraud or safety ticket is expensive and public; a false alarm costs an agent 30 seconds. So rules set
the floor and the AI can only add. Recall can only go up. Precision may drop, and I measure that.

**17. How good are your urgency rules?**
On the tweets I read while writing them: 13 of 16 urgent caught. On 150 fresh tweets: only 3 of 10. That drop
is exactly why the AI-may-raise layer exists. I report the fresh number as the real one.

**18. What did your edge-case tests find?**
Empty text, emoji only, Hinglish, very long and HTML text all run without crashing. One test found a real bug:
the word "fire" matched "Firefox" and Amazon "Fire Stick", making them urgent. I added word boundaries and wrote
down that the fix came before any hold-out scoring.

**19. How does the human-in-the-loop queue work?**
Urgent tickets first, then oldest. Each ticket shows a suggested team and a draft. The agent approves, edits or
rejects - nothing is sent without that. Every decision goes into a log: was the team kept, was the draft edited,
how many seconds. That log is a live eval: it measures accuracy and time saved with real agents.

## Business case and delivery
**20. How did you calculate ROI?**
In agent-hours, because that is what a support lead controls. Routing saves time when the suggestion is right
and costs time when it is wrong. Drafts save writing time when used. Measured inputs: volume and accuracy.
Everything else is an assumption with a low, base and high value, written in the code.

**21. What is the most important number in the ROI?**
The break-even: 33% routing accuracy. Below it, suggestions waste time. The classical model at 20% would cost
about 21 hours a week. The LLM at 72% saves about 61 hours a week from routing at base.

**22. Which assumption worries you most?**
How often agents actually use the draft. It swings the answer by about 150 hours a week. So the pilot's first
job is to measure draft usage and seconds per ticket from the approval log.

**23. How would you roll this out at a client?**
Week 1: two people label the same 200 recent tickets, check agreement, finish the full eval. Then 2 weeks
shadow mode - the model runs silently and we compare. Then 4 weeks assist mode on one queue and one shift, with a
control shift. Scale only if logged numbers beat the bar. Each phase has a stop rule.

**24. What are the biggest risks?**
A bad draft sent in a hurry, a missed urgent ticket, customer data going to an API, agents trusting it blindly,
and cost creep. Controls: agent must click, rules own P1, mask personal data or self-host, track edit rate,
log cost per call.

**25. What would you do differently, or next?**
Get a second labeller and an agreement score. Finish the full LLM run. Train a classical model on real labelled
tickets as a fairer baseline. Measure real handle times instead of assuming 6 minutes. And test on email and
chat, not only Twitter.
