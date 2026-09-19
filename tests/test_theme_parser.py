import json

import themes


class FakeGroww:
    EXCHANGE_NSE, SEGMENT_CASH, CANDLE_INTERVAL_DAY = "NSE", "CASH", "DAY"
    KNOWN = {"TATASTEEL"}

    def get_historical_candles(self, groww_symbol, **kw):
        sym = groww_symbol.removeprefix("NSE-")
        if sym not in self.KNOWN:
            raise RuntimeError("unknown symbol")
        return {"candles": [[i, 100, 100, 100, 100.0, 300000.0] for i in range(25)]}


def fake_llm(lines):
    return {"themes": [
        {"name": "AI chips", "thesis": "x", "confidence": 0.8, "symbols": ["TATASTEEL", "FAKESYM"],
         "already_priced_in_risk": "low"},
        {"name": "low confidence", "thesis": "y", "confidence": 0.1, "symbols": ["ITC"]},
    ]}


def test_main_filters_by_confidence_and_tradability(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "memory").mkdir()
    themes.main(llm=fake_llm, news=lambda: ["headline"], connect=lambda: FakeGroww())
    out = json.loads((tmp_path / "memory" / "themes.json").read_text())
    assert len(out["themes"]) == 1
    assert out["themes"][0]["name"] == "AI chips"
    assert out["themes"][0]["symbols"] == ["TATASTEEL"]
    assert out["themes"][0]["dropped"] == ["FAKESYM"]


class FakeHTTPResponse:
    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body


def test_ask_llm_extracts_json_from_prose_wrapped_response(monkeypatch):
    raw = json.dumps({"choices": [{"message": {"content":
        'Sure, here is the analysis:\n```json\n{"themes": []}\n```\nHope that helps!'}}]}).encode()
    monkeypatch.setattr(themes.urllib.request, "urlopen", lambda req, timeout=None: FakeHTTPResponse(raw))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert themes.ask_llm(["some headline"]) == {"themes": []}
