import json

from bot.portfolio import JsonPortfolioStore


def test_load_default_when_file_missing(tmp_path):
    store = JsonPortfolioStore(str(tmp_path / "state.json"), capital=1000.0)
    assert store.load() == {"cash": 1000.0, "pos": {}, "day": "", "day_start": 1000.0, "log": []}


def test_save_then_load_round_trips(tmp_path):
    path = str(tmp_path / "state.json")
    store = JsonPortfolioStore(path, capital=1000.0)
    state = {"cash": 500.0, "pos": {"ITC": {"qty": 1}}, "day": "2026-09-19", "day_start": 1000.0, "log": []}
    store.save(state)
    assert store.load() == state
    assert json.load(open(path)) == state
