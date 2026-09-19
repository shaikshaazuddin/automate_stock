from bot.risk import RiskManager


def make_risk(**kw):
    defaults = dict(capital=1000.0, max_positions=2, max_theme_positions=1, daily_loss_limit=30.0)
    defaults.update(kw)
    return RiskManager(**defaults)


def test_trading_halted_false_when_no_stop_file(tmp_path):
    r = make_risk(stop_file=str(tmp_path / "STOP"))
    assert r.trading_halted() is False


def test_trading_halted_true_when_stop_file_exists(tmp_path):
    stop = tmp_path / "STOP"
    stop.write_text("halt")
    r = make_risk(stop_file=str(stop))
    assert r.trading_halted() is True


def test_daily_loss_limit_not_hit_above_boundary():
    r = make_risk(daily_loss_limit=30.0)
    assert r.daily_loss_limit_hit(equity=975.0, day_start_equity=1000.0) is False  # -25, limit -30


def test_daily_loss_limit_hit_at_exact_boundary():
    r = make_risk(daily_loss_limit=30.0)
    assert r.daily_loss_limit_hit(equity=970.0, day_start_equity=1000.0) is True  # -30 == -limit


def test_max_positions_not_reached():
    assert make_risk(max_positions=2).max_positions_reached({"ITC": {}}) is False


def test_max_positions_reached():
    assert make_risk(max_positions=2).max_positions_reached({"ITC": {}, "SBIN": {}}) is True


def test_theme_limit_never_blocks_core():
    r = make_risk(max_theme_positions=1)
    assert r.theme_limit_reached({"ITC": {"src": "theme:x"}}, "core") is False


def test_theme_limit_not_reached_under_cap():
    r = make_risk(max_theme_positions=1)
    assert r.theme_limit_reached({"ITC": {"src": "core"}}, "theme:y") is False


def test_theme_limit_reached_at_cap():
    r = make_risk(max_theme_positions=1)
    assert r.theme_limit_reached({"ITC": {"src": "theme:x"}}, "theme:y") is True


def test_position_size_capital_constrained():
    r = make_risk(capital=1000.0, max_positions=2)
    assert r.position_size(cash=1000.0, price=100.0) == 4


def test_position_size_cash_constrained():
    r = make_risk(capital=1000.0, max_positions=2)
    assert r.position_size(cash=50.0, price=100.0) == 0
