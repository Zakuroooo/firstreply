import pytest

from firstreply import staffing


def test_workload():
    # 60 tickets/h x 6 min = 6 agent-hours of work; at 85% busy -> 7.06 -> 8 agents
    assert staffing.workload_agents(60, 6, 0.85) == 8
    assert staffing.workload_agents(0, 6) == 0


def test_erlang_c_textbook_value():
    # 2 Erlangs of traffic, 3 agents -> P(wait) = 4/9
    assert staffing.erlang_c(3, 2.0) == pytest.approx(4 / 9)
    assert staffing.erlang_c(2, 2.0) == 1.0


def test_erlang_agents_meets_target_and_is_minimal():
    n = staffing.erlang_agents(60, 6, 60, 0.9)
    assert staffing.service_level(n, 60, 6, 60) >= 0.9
    assert staffing.service_level(n - 1, 60, 6, 60) < 0.9


def test_more_tickets_never_needs_fewer_agents():
    counts = [staffing.erlang_agents(t, 6, 60) for t in range(0, 300, 10)]
    assert counts == sorted(counts)
