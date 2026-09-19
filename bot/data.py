import datetime as dt


class GrowwDataProvider:
    def __init__(self, g, tz):
        self.g, self.tz = g, tz

    def get_closes(self, symbol):
        now = dt.datetime.now(self.tz)
        r = self.g.get_historical_candles(
            exchange=self.g.EXCHANGE_NSE, segment=self.g.SEGMENT_CASH, groww_symbol=f"NSE-{symbol}",
            start_time=(now - dt.timedelta(days=150)).strftime("%Y-%m-%d %H:%M:%S"),
            end_time=now.strftime("%Y-%m-%d %H:%M:%S"), candle_interval=self.g.CANDLE_INTERVAL_DAY)
        return [c[4] for c in r["candles"]]

    def get_ltp(self, symbols):
        symbols = list(symbols)
        live = self.g.get_ltp(exchange_trading_symbols=tuple(f"NSE_{s}" for s in symbols),
                              segment=self.g.SEGMENT_CASH)
        return {s: float(live[f"NSE_{s}"]) for s in symbols}
