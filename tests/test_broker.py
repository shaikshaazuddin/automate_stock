from bot.broker import GrowwBroker, PaperBroker


def test_paper_broker_fills_full_quantity_instantly():
    b = PaperBroker()
    assert b.place_order("ITC", 5, "BUY", 123.45) == 5
    assert b.place_order("ITC", 5, "SELL", 100.0) == 5


class FakeGroww:
    EXCHANGE_NSE, SEGMENT_CASH, PRODUCT_CNC = "NSE", "CASH", "CNC"
    ORDER_TYPE_MARKET, VALIDITY_DAY = "MARKET", "DAY"
    TRANSACTION_TYPE_BUY, TRANSACTION_TYPE_SELL = "BUY", "SELL"

    def place_order(self, **kw):
        self.last_order = kw
        return {"groww_order_id": "abc123"}

    def get_order_status(self, **kw):
        return {"filled_quantity": 3}


def test_groww_broker_places_order_and_returns_filled_quantity():
    g = FakeGroww()
    filled = GrowwBroker(g).place_order("ITC", 5, "BUY", 100.0)
    assert filled == 3
    assert g.last_order["transaction_type"] == "BUY"
