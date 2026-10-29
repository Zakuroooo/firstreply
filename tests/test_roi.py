from firstreply import roi


def test_more_accuracy_saves_more():
    a = roi.pick("base")
    assert roi.minutes_saved_per_ticket(0.9, a) > roi.minutes_saved_per_ticket(0.5, a)


def test_break_even_routing():
    a = roi.pick("base")
    # base: right route saves 1.0 x 0.5 = 0.5 min, wrong costs 0.25 -> break-even at 1/3 accuracy
    assert abs(roi.routing_minutes(1 / 3, a)) < 1e-9


def test_low_is_below_high():
    lo = roi.scenario(0.6, 10_000, roi.pick("low"))["agent_hours_saved_per_week"]
    hi = roi.scenario(0.6, 10_000, roi.pick("high"))["agent_hours_saved_per_week"]
    assert lo < hi


def test_sensitivity_has_every_assumption():
    s = roi.sensitivity(0.6, 10_000)
    assert set(s.assumption) == set(roi.ASSUMPTIONS)
    assert s.swing.is_monotonic_decreasing
