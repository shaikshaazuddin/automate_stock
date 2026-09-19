from bot.costs import cost


def test_cost_below_brokerage_cap():
    assert cost(10000, False) == 20.0  # 0.1% brokerage (10) + 0.1% txn charge (10)


def test_cost_brokerage_capped_at_20():
    assert cost(30000, False) == 50.0  # brokerage capped at 20 + 30 txn charge


def test_cost_adds_dp_charge_on_sell_only():
    assert cost(10000, True) - cost(10000, False) == 20.0
