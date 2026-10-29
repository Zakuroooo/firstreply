# 01 - Support operations basics

Read this first. Every other file uses these words.

## Ticket
A message from a customer that needs an answer. Here, one ticket = one customer tweet that **starts** a
conversation with a brand (not a reply inside an old conversation). See `sql/01_tickets.sql`.

## Queue and triage
A **queue** is a team or a pile of work: delivery team, refunds team, billing team, and so on.
**Triage** means looking at a new ticket and deciding (1) which queue it goes to and (2) how urgent it is.
Hospitals do triage too: the heart attack is seen before the sprained ankle.

> Hinglish: Triage matlab naya ticket dekh ke decide karna - kis team ko jayega aur kitna urgent hai.

## First-response time (FRT)
Minutes from the customer's tweet to the brand's **first** reply. If the brand replied three times, only the
earliest reply counts. FRT is the number customers feel most: "did anyone even see my message?"

## SLA (service-level agreement)
A promise about speed, for example "we reply first within 60 minutes". A ticket that gets its first reply
after 60 minutes **breaches** the SLA. **Breach rate** = breached tickets / answered tickets.

We chose 60 minutes ourselves (the data has no official SLA). That is why we also show the breach rate at
15 minutes and 4 hours: the choice of target changes the story a lot.

> Hinglish: SLA ek promise hai - "hum 60 minute ke andar pehla reply denge". Late hua toh breach.

## Median and p90
Put all FRTs in order from fastest to slowest.
- **Median (p50)**: the middle one. Half the customers waited less, half waited more.
- **p90**: the point where 90% waited less and 10% waited more. It shows the **bad tail**.

Why not the average? A few tickets that waited 3 days pull the average up a lot. The median shows the
normal customer; p90 shows the unlucky ones. Ops teams usually manage to p90, because angry customers live
in the tail.

> Hinglish: p90 matlab 100 mein se 90 customers isse kam wait karte hain - baaki 10 ka bura experience yahi number dikhata hai.

## Backlog
Tickets waiting for a first reply at a moment in time. We count it at the end of every hour: created before
that hour ended, first reply after it. A growing backlog means work comes in faster than agents clear it.

## Volume by hour and weekday
Tickets do not arrive evenly. Some hours are busy, some are quiet. If the team is the same size all day,
busy hours breach more. That is the whole reason staffing plans are made per hour.

## Limits of this data (say these in interviews)
- Twitter only; real support also has email, chat and phone.
- Only tickets that got a reply have an FRT. Unanswered tickets are counted but have no FRT.
- Times are UTC; brands sit in different time zones, so "4 am" is 4 am UTC, not local time.
- The data is from 2017. Patterns help us practise the method; they do not describe any brand today.
