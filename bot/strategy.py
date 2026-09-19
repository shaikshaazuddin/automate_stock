"""Uptrend, not overbought, positive 5-day momentum. Moved verbatim from the old trader.py."""


def rsi(c, n=14):
    d = [c[i] - c[i - 1] for i in range(len(c) - n, len(c))]
    gain = sum(x for x in d if x > 0) / n
    loss = -sum(x for x in d if x < 0) / n
    return 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)


class SmaRsiStrategy:
    def __init__(self, rsi_lo, rsi_hi):
        self.rsi_lo, self.rsi_hi = rsi_lo, rsi_hi

    def signal(self, c):
        if len(c) < 25:
            return False
        return c[-1] > sum(c[-20:]) / 20 and self.rsi_lo <= rsi(c) <= self.rsi_hi and c[-1] > c[-6]

    def features(self, c):
        return {"rsi": round(rsi(c), 1), "sma20": round(sum(c[-20:]) / 20, 2), "mom5": round(c[-1] / c[-6] - 1, 4)}
