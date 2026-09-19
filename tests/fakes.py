class FakeBroker:
    def __init__(self, fills=None):
        self.orders = []
        self.fills = fills or {}

    def place_order(self, symbol, qty, side, price):
        self.orders.append({"symbol": symbol, "qty": qty, "side": side, "price": price})
        return self.fills.get(symbol, qty)


class FakeDataProvider:
    def __init__(self, closes, ltp=None, raise_on_ltp=False):
        self._closes, self._ltp, self._raise = closes, ltp or {}, raise_on_ltp

    def get_closes(self, symbol):
        return self._closes[symbol]

    def get_ltp(self, symbols):
        if self._raise:
            raise RuntimeError("simulated LTP failure")
        return {s: self._ltp[s] for s in symbols}
