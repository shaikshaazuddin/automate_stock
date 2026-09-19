from bot.strategy import SmaRsiStrategy, rsi


def test_rsi_all_gains_is_100():
    assert rsi(list(range(100, 130))) == 100.0


def test_rsi_all_losses_is_0():
    assert rsi(list(range(130, 100, -1))) == 0.0


def test_signal_false_short_history():
    assert SmaRsiStrategy(0, 100).signal(list(range(100, 120))) is False  # only 20 closes, need 25


def test_signal_false_below_sma20():
    c = list(range(130, 100, -1)) + [100]  # falling, last close is the series minimum
    assert SmaRsiStrategy(0, 100).signal(c) is False


def test_signal_false_rsi_out_of_band():
    c = list(range(100, 130))  # purely rising: RSI == 100, outside a tight band
    assert SmaRsiStrategy(40, 65).signal(c) is False


def test_signal_false_non_positive_momentum():
    c = [90] * 19 + [110, 108, 106, 104, 102, 100]  # above SMA20 but last 6 days declining
    assert SmaRsiStrategy(0, 100).signal(c) is False


def test_signal_true_all_conditions_pass():
    c = [90] * 19 + [100, 102, 104, 106, 108, 110]  # above SMA20, rising last 6 days
    assert SmaRsiStrategy(0, 100).signal(c) is True
