"""Minimal daily swing bot for Groww. PAPER mode unless LIVE_CONFIRM=YES_I_UNDERSTAND.

Run once per trading day around 3:15 PM IST:  python trader.py
Create a file named STOP in this folder to halt all new trading instantly.
"""
import datetime as dt
import json
import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from bot.broker import GrowwBroker, PaperBroker
from bot.costs import cost
from bot.data import GrowwDataProvider
from bot.groww_client import connect
from bot.journal import JsonlJournal
from bot.portfolio import JsonPortfolioStore
from bot.risk import RiskManager
from bot.strategy import SmaRsiStrategy

load_dotenv()

# ---- settings -------------------------------------------------------------
CORE = ["ITC", "SBIN", "NTPC", "ONGC", "COALINDIA", "TATASTEEL"]  # liquid NSE stocks, always scanned
CAPITAL = 1000.0            # rupees the bot may use, never more
PARAMS_FILE, JOURNAL_FILE = "memory/params.json", "memory/journal.jsonl"
P = json.load(open(PARAMS_FILE))        # tunable values live here, with bounds (see OBJECTIVE.md)
STOP_LOSS, TARGET = P["stop_loss"], P["target"]
MAX_POSITIONS = P["max_positions"]
DAILY_LOSS_LIMIT = 0.03 * CAPITAL       # no new buys once the day is down this much
STATE_FILE = "state.json"
PAPER = os.getenv("LIVE_CONFIRM") != "YES_I_UNDERSTAND"
IST = ZoneInfo("Asia/Kolkata")


def theme_symbols():
    """{symbol: theme} from themes.py output. Themes only ADD candidates; they never bypass any rule."""
    try:
        t = json.load(open("memory/themes.json"))
    except (OSError, ValueError):
        return {}
    today = dt.datetime.now(IST).strftime("%Y-%m-%d")
    return {sym: th["name"] for th in t.get("themes", []) if th["expires"] >= today for sym in th["symbols"]}


def build_dependencies(g):
    data = GrowwDataProvider(g, IST)
    broker = PaperBroker() if PAPER else GrowwBroker(g)
    strategy = SmaRsiStrategy(P["rsi_lo"], P["rsi_hi"])
    risk = RiskManager(CAPITAL, MAX_POSITIONS, P.get("max_theme_positions", 1), DAILY_LOSS_LIMIT)
    store = JsonPortfolioStore(STATE_FILE, CAPITAL)
    journal = JsonlJournal(JOURNAL_FILE, "paper" if PAPER else "live", IST)
    return data, broker, strategy, risk, store, journal


def run(data, broker, strategy, risk, store, journal):
    if risk.trading_halted():
        return print("STOP file found. Not trading.")
    st = store.load()
    themed = theme_symbols()
    cands = list(dict.fromkeys(CORE + list(themed)))
    universe = list(dict.fromkeys(cands + list(st["pos"])))   # keep pricing positions whose theme expired
    hist = {s: data.get_closes(s) for s in universe}
    ltp = {s: hist[s][-1] for s in universe}
    try:
        ltp = data.get_ltp(universe)
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
                  "trend_break" if not strategy.signal(hist[s]) else None)
        if reason:
            n = broker.place_order(s, p["qty"], "SELL", px)
            if n:
                sell_cost = cost(n * px, True)
                st["cash"] += n * px - sell_cost
                journal.record(type="SELL", sym=s, src=p.get("src", "core"), qty=n, price=round(px, 2),
                                reason=reason, pnl=round(n * (px - p["entry"]) - sell_cost - p["buy_cost"], 2),
                                **strategy.features(hist[s]))
                p["qty"] -= n
                st["log"].append(f"{today} SELL {s} x{n} @ {px:.2f}")
                if p["qty"] == 0:
                    del st["pos"][s]

    equity = st["cash"] + sum(p["qty"] * ltp[s] for s, p in st["pos"].items())
    if risk.daily_loss_limit_hit(equity, st["day_start"]):
        print("Daily loss limit hit. No new buys today.")
    else:
        for s in cands:
            if risk.max_positions_reached(st["pos"]):
                break
            if s in st["pos"] or not strategy.signal(hist[s]):
                continue
            src = f"theme:{themed[s]}" if s in themed and s not in CORE else "core"
            if risk.theme_limit_reached(st["pos"], src):
                continue
            qty = risk.position_size(st["cash"], ltp[s])
            if qty < 1:
                continue
            n = broker.place_order(s, qty, "BUY", ltp[s])
            if n:
                bc = cost(n * ltp[s], False)
                st["cash"] -= n * ltp[s] + bc
                st["pos"][s] = {"qty": n, "entry": ltp[s], "buy_cost": bc, "src": src}
                journal.record(type="BUY", sym=s, src=src, qty=n, price=round(ltp[s], 2),
                                **strategy.features(hist[s]))
                st["log"].append(f"{today} BUY {s} x{n} @ {ltp[s]:.2f}")

    equity = st["cash"] + sum(p["qty"] * ltp[s] for s, p in st["pos"].items())
    store.save(st)
    print(f"[{'PAPER' if PAPER else 'LIVE'}] equity ₹{equity:.2f} "
          f"(today {equity - st['day_start']:+.2f}, since start {equity - CAPITAL:+.2f}) "
          f"positions: {list(st['pos'])}")
    return st


def main():
    run(*build_dependencies(connect()))


if __name__ == "__main__":
    main()
