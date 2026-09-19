class PaperBroker:
    def place_order(self, symbol, qty, side, price):
        """Fills instantly at `price`."""
        return qty


class GrowwBroker:
    """Live order placement. No retry/partial-fill handling yet — that's a later hardening task."""

    def __init__(self, g):
        self.g = g

    def place_order(self, symbol, qty, side, price):
        txn = self.g.TRANSACTION_TYPE_BUY if side == "BUY" else self.g.TRANSACTION_TYPE_SELL
        r = self.g.place_order(trading_symbol=symbol, quantity=qty, validity=self.g.VALIDITY_DAY,
                               exchange=self.g.EXCHANGE_NSE, segment=self.g.SEGMENT_CASH,
                               product=self.g.PRODUCT_CNC, order_type=self.g.ORDER_TYPE_MARKET,
                               transaction_type=txn)
        s = self.g.get_order_status(groww_order_id=r["groww_order_id"], segment=self.g.SEGMENT_CASH)
        return int(s.get("filled_quantity", 0))
