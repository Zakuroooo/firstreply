"""Turn a ticket forecast into a number of agents.

Two methods, both simple enough to do on paper:
1. Workload: agents = tickets/hour x handle time / 60 / occupancy.
2. Erlang C: the classic call-centre queue formula. Given traffic and agents, it gives the chance a
   ticket must wait, and from that the share answered within the SLA. We add agents until the target is met.
"""
import math


def workload_agents(tickets_per_hour, aht_minutes, occupancy=0.85):
    """Agents needed if each agent is busy `occupancy` of the hour."""
    return math.ceil(tickets_per_hour * aht_minutes / 60 / occupancy) if tickets_per_hour > 0 else 0


def erlang_c(agents, traffic):
    """Probability an arriving ticket has to wait (traffic = tickets/hour x AHT hours, in Erlangs)."""
    if agents <= traffic:
        return 1.0
    # sum_{k<agents} traffic^k / k!  computed iteratively to avoid huge factorials
    term, total = 1.0, 1.0
    for k in range(1, agents):
        term *= traffic / k
        total += term
    top = term * traffic / agents * agents / (agents - traffic)
    return top / (total + top)


def service_level(agents, tickets_per_hour, aht_minutes, target_minutes):
    """Share of tickets answered within target_minutes."""
    traffic = tickets_per_hour * aht_minutes / 60
    if agents <= traffic:
        return 0.0
    wait_prob = erlang_c(agents, traffic)
    return 1 - wait_prob * math.exp(-(agents - traffic) * target_minutes / aht_minutes)


def erlang_agents(tickets_per_hour, aht_minutes, target_minutes, target_share=0.9):
    """Smallest number of agents that answers target_share of tickets within target_minutes."""
    if tickets_per_hour <= 0:
        return 0
    agents = max(1, math.ceil(tickets_per_hour * aht_minutes / 60))
    while service_level(agents, tickets_per_hour, aht_minutes, target_minutes) < target_share:
        agents += 1
    return agents
