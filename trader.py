"""Minimal daily swing bot for Groww. PAPER mode unless LIVE_CONFIRM=YES_I_UNDERSTAND.

Run once per trading day around 3:15 PM IST:  python trader.py
Create a file named STOP in this folder to halt all new trading instantly.
"""
import json, os, datetime as dt
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from growwapi import GrowwAPI

load_dotenv()

# ---- settings -------------------------------------------------------------
CORE = ["ITC", "SBIN", "NTPC", "ONGC", "COALINDIA", "TATASTEEL"]  # liquid NSE stocks, always scanned
CAPITAL = 1000.0            # rupees the bot may use, never more
PARAMS_FILE, JOURNAL_FILE = "memory/params.json", "memory/journal.jsonl"
P = json.load(open(PARAMS_FILE))        # tunable values live here, with bounds (see OBJECTIVE.md)
STOP_LOSS, TARGET = P["stop_loss"], P["target"]
MAX_POSITIONS = P["max_positions"]
DAILY_LOSS_LIMIT = 0.03 * CAPITAL       # no new buys once the day is down this much
DP_CHARGE = 20.0            # approx. depository charge per delivery SELL; verify on Groww
STATE_FILE = "state.json"
PAPER = os.getenv("LIVE_CONFIRM") != "YES_I_UNDERSTAND"
IST = ZoneInfo("Asia/Kolkata")


# ---- strategy: uptrend, not overbought, positive 5-day momentum ------------
def rsi(c, n=14):
    d = [c[i] - c[i - 1] for i in range(len(c) - n, len(c))]
    gain = sum(x for x in d if x > 0) / n
    loss = -sum(x for x in d if x < 0) / n
    return 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)


def signal(c):
    if len(c) < 25:
        return False
    return c[-1] > sum(c[-20:]) / 20 and P["rsi_lo"] <= rsi(c) <= P["rsi_hi"] and c[-1] > c[-6]


def cost(value, sell):
    brokerage = min(20.0, 0.001 * value)
    return brokerage + 0.001 * value + (DP_CHARGE if sell else 0)  # + STT 0.1%


def theme_symbols():
    """{symbol: theme} from themes.py output. Themes only ADD candidates; they never bypass any rule."""
    try:
        t = json.load(open("memory/themes.json"))
    except (OSError, ValueError):
        return {}
    today = dt.datetime.now(IST).strftime("%Y-%m-%d")
    return {sym: th["name"] for th in t.get("themes", []) if th["expires"] >= today for sym in th["symbols"]}


def journal(**e):
    """Append one event to the memory journal. review.py learns from this file."""
    e["ts"] = dt.datetime.now(IST).isoformat(timespec="seconds")
    e["mode"] = "paper" if PAPER else "live"
    with open(JOURNAL_FILE, "a") as f:
        f.write(json.dumps(e) + "\n")


def features(c):
    return {"rsi": round(rsi(c), 1), "sma20": round(sum(c[-20:]) / 20, 2), "mom5": round(c[-1] / c[-6] - 1, 4)}


# ---- broker ------------------------------------------------------------------
def connect():
    r = GrowwAPI.get_access_token(api_key=os.environ["GROWW_API_KEY"],
                                  secret=os.environ["GROWW_API_SECRET"])
    token = r.get("token") or r.get("access_token") if isinstance(r, dict) else r
    return GrowwAPI(token)


def closes(g, sym):
    now = dt.datetime.now(IST)
    r = g.get_historical_candles(
        exchange=g.EXCHANGE_NSE, segment=g.SEGMENT_CASH, groww_symbol=f"NSE-{sym}",
        start_time=(now - dt.timedelta(days=150)).strftime("%Y-%m-%d %H:%M:%S"),
        end_time=now.strftime("%Y-%m-%d %H:%M:%S"), candle_interval=g.CANDLE_INTERVAL_DAY)
    return [c[4] for c in r["candles"]]


def order(g, sym, qty, side, price):
    """Returns filled quantity. Paper mode fills instantly at `price`."""
    if PAPER:
        return qty
    r = g.place_order(trading_symbol=sym, quantity=qty, validity=g.VALIDITY_DAY,
                      exchange=g.EXCHANGE_NSE, segment=g.SEGMENT_CASH, product=g.PRODUCT_CNC,
                      order_type=g.ORDER_TYPE_MARKET, transaction_type=side)
    s = g.get_order_status(groww_order_id=r["groww_order_id"], segment=g.SEGMENT_CASH)
    return int(s.get("filled_quantity", 0))


# ---- main --------------------------------------------------------------------
def main():
    if os.path.exists("STOP"):
        return print("STOP file found. Not trading.")
    st = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else \
        {"cash": CAPITAL, "pos": {}, "day": "", "day_start": CAPITAL, "log": []}
    g = connect()
    themed = theme_symbols()
    cands = list(dict.fromkeys(CORE + list(themed)))
    universe = list(dict.fromkeys(cands + list(st["pos"])))   # keep pricing positions whose theme expired
    hist = {s: closes(g, s) for s in universe}
    ltp = {s: hist[s][-1] for s in universe}
    try:
        live = g.get_ltp(exchange_trading_symbols=tuple(f"NSE_{s}" for s in universe),
                         segment=g.SEGMENT_CASH)
        ltp = {s: float(live[f"NSE_{s}"]) for s in universe}
    except Exception as e:
        print("LTP fetch failed, using last daily close:", e)

    equity = st["cash"] + sum(p["qty"] * ltp[s] for s, p in st["pos"].items())
    today = dt.datetime.now(IST).strftime("%Y-%m-%d")
    if st["day"] != today:
        st["day"], st["day_start"] = today, equity

    for s, p in list(st["pos"].items()):                        # exits first
        px = ltp[s]
        reason = ("stop" if px <= p["entry"] * (1 - STOP_LOSS) else
                  "target" if px >= p["entry"] * (1 + TARGET) else
                  "trend_break" if not signal(hist[s]) else None)
        if reason:
            n = order(g, s, p["qty"], g.TRANSACTION_TYPE_SELL, px)
            if n:
                sell_cost = cost(n * px, True)
                st["cash"] += n * px - sell_cost
                journal(type="SELL", sym=s, src=p.get("src", "core"), qty=n, price=round(px, 2), reason=reason,
                        pnl=round(n * (px - p["entry"]) - sell_cost - p["buy_cost"], 2),
                        **features(hist[s]))
                p["qty"] -= n
                st["log"].append(f"{today} SELL {s} x{n} @ {px:.2f}")
                if p["qty"] == 0:
                    del st["pos"][s]

    equity = st["cash"] + sum(p["qty"] * ltp[s] for s, p in st["pos"].items())
    if equity - st["day_start"] <= -DAILY_LOSS_LIMIT:
        print("Daily loss limit hit. No new buys today.")
    else:
        for s in cands:
            if len(st["pos"]) >= MAX_POSITIONS:
                break
            if s in st["pos"] or not signal(hist[s]):
                continue
            src = f"theme:{themed[s]}" if s in themed and s not in CORE else "core"
            if src != "core" and sum(p.get("src", "core") != "core" for p in st["pos"].values()) \
                    >= P.get("max_theme_positions", 1):
                continue
            budget = min(st["cash"], CAPITAL / MAX_POSITIONS)
            qty = int((budget - cost(budget, False)) // ltp[s])
            if qty < 1:
                continue
            n = order(g, s, qty, g.TRANSACTION_TYPE_BUY, ltp[s])
            if n:
                bc = cost(n * ltp[s], False)
                st["cash"] -= n * ltp[s] + bc
                st["pos"][s] = {"qty": n, "entry": ltp[s], "buy_cost": bc, "src": src}
                journal(type="BUY", sym=s, src=src, qty=n, price=round(ltp[s], 2), **features(hist[s]))
                st["log"].append(f"{today} BUY {s} x{n} @ {ltp[s]:.2f}")

    equity = st["cash"] + sum(p["qty"] * ltp[s] for s, p in st["pos"].items())
    json.dump(st, open(STATE_FILE, "w"), indent=2)
    print(f"[{'PAPER' if PAPER else 'LIVE'}] equity ₹{equity:.2f} "
          f"(today {equity - st['day_start']:+.2f}, since start {equity - CAPITAL:+.2f}) "
          f"positions: {list(st['pos'])}")


if __name__ == "__main__":
    main()
