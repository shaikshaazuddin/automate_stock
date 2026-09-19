import json
from zoneinfo import ZoneInfo

from bot.journal import JsonlJournal


def test_record_appends_jsonl_with_ts_and_mode(tmp_path):
    path = str(tmp_path / "journal.jsonl")
    j = JsonlJournal(path, "paper", ZoneInfo("Asia/Kolkata"))
    j.record(type="BUY", sym="ITC", qty=1)
    j.record(type="SELL", sym="ITC", qty=1)
    lines = [json.loads(line) for line in open(path)]
    assert len(lines) == 2
    assert lines[0]["type"] == "BUY" and lines[0]["mode"] == "paper" and "ts" in lines[0]
    assert lines[1]["type"] == "SELL"
