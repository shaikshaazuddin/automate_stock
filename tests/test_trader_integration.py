"""Golden-fixture regression for the Task 1 split: given fixed data/broker inputs, the
orchestrator's state.json/journal.jsonl output must match values computed by hand from the
same formulas the pre-split trader.py used (rsi/signal/cost math unchanged, only moved)."""
import json

import trader
from bot.journal import JsonlJournal
from bot.portfolio import JsonPortfolioStore
from bot.risk import RiskManager
from bot.strategy import SmaRsiStrategy
from tests.fakes import FakeBroker, FakeDataProvider

FLAT = [90.0] * 25
# above SMA20, rsi == 50 (9 down then +2/+2/+2/+2/+1 up over the RSI window), momentum positive
SIGNAL = [90.0] * 10 + [100, 99, 98, 97, 96, 95, 94, 93, 92, 91, 93, 95, 97, 99, 100]


def test_fresh_run_buys_the_one_symbol_with_a_signal(tmp_path):
    closes = {s: (SIGNAL if s == "TATASTEEL" else FLAT) for s in trader.CORE}
    ltp = {s: closes[s][-1] for s in trader.CORE}
    data = FakeDataProvider(closes, ltp)
    broker = FakeBroker()
    strategy = SmaRsiStrategy(trader.P["rsi_lo"], trader.P["rsi_hi"])
    risk = RiskManager(trader.CAPITAL, trader.MAX_POSITIONS, trader.P.get("max_theme_positions", 1),
                        trader.DAILY_LOSS_LIMIT)
    store = JsonPortfolioStore(str(tmp_path / "state.json"), trader.CAPITAL)
    journal = JsonlJournal(str(tmp_path / "journal.jsonl"), "paper", trader.IST)

    st = trader.run(data, broker, strategy, risk, store, journal)

    assert st["pos"] == {"TATASTEEL": {"qty": 4, "entry": 100.0, "buy_cost": 0.8, "src": "core"}}
    assert st["cash"] == 599.2
    assert broker.orders == [{"symbol": "TATASTEEL", "qty": 4, "side": "BUY", "price": 100.0}]

    lines = [json.loads(line) for line in open(tmp_path / "journal.jsonl")]
    assert len(lines) == 1
    e = lines[0]
    assert e["type"] == "BUY" and e["sym"] == "TATASTEEL" and e["src"] == "core"
    assert e["qty"] == 4 and e["price"] == 100.0
    assert e["rsi"] == 50.0 and e["sma20"] == 94.45 and e["mom5"] == 0.0989
    assert json.load(open(tmp_path / "state.json"))["cash"] == 599.2
