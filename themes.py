"""News -> themes -> candidate NSE stocks. Run before trader.py (e.g. 8:30 AM IST, once a day).

    python themes.py

Needs OPENAI_API_KEY (billed per use, a few rupees per run) plus the Groww credentials.
Output: memory/themes.json, read by trader.py.

Prompt rules live in config.yaml, not here — edit that file to change analyst behavior.

News PROPOSES. Price CONFIRMS (trader.signal must still pass). The risk gate DISPOSES.
"""
import datetime as dt, json, os, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
import yaml
from dotenv import load_dotenv
import trader

load_dotenv()

FEEDS = [f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=en-IN&gl=IN&ceid=IN:en" for q in [
    "India stock market sectors rally when:2d",
    "semiconductor memory chip prices AI demand when:3d",
    "commodity prices surge OR slump India when:2d",
    "government policy India industry PLI OR tariff OR budget when:3d",
    "data center power demand AI infrastructure India when:3d"]]
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_THEMES, MAX_SYMBOLS, MIN_CONFIDENCE, LIFETIME_DAYS = 3, 4, 0.6, 10
MIN_DAILY_VALUE = 2e7        # skip stocks trading under ~₹2 crore/day: illiquid, easy to get trapped in

with open(os.path.join(os.path.dirname(__file__), "config.yaml")) as f:
    PROMPT = yaml.safe_load(f)["theme_research"]["template"]


def headlines():
    seen, out = set(), []
    for url in FEEDS:
        try:
            root = ET.fromstring(urllib.request.urlopen(url, timeout=15).read())
        except Exception as e:
            print("feed failed:", e)
            continue
        for it in root.iter("item"):
            t = (it.findtext("title") or "").strip()
            if t and t not in seen:
                seen.add(t)
                out.append(t)
    return out[:80]


def ask_llm(lines):
    body = json.dumps({"model": MODEL, "max_tokens": 1500, "messages": [
        {"role": "user", "content": PROMPT.format(n=MAX_THEMES, headlines="\n".join(f"- {l}" for l in lines))}]})
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", body.encode(), {
        "content-type": "application/json",
        "authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
    text = json.load(urllib.request.urlopen(req, timeout=90))["choices"][0]["message"]["content"]
    return json.loads(text[text.index("{"): text.rindex("}") + 1])


def tradable(g, sym):
    """Real symbol, enough history for the signal, and liquid enough. Drops hallucinated tickers."""
    try:
        now = dt.datetime.now(trader.IST)
        r = g.get_historical_candles(
            exchange=g.EXCHANGE_NSE, segment=g.SEGMENT_CASH, groww_symbol=f"NSE-{sym}",
            start_time=(now - dt.timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S"),
            end_time=now.strftime("%Y-%m-%d %H:%M:%S"), candle_interval=g.CANDLE_INTERVAL_DAY)
        c = r["candles"][-20:]
        return len(r["candles"]) >= 25 and sum(x[4] * x[5] for x in c) / len(c) >= MIN_DAILY_VALUE
    except Exception:
        return False


def main(llm=ask_llm, news=headlines, connect=trader.connect):
    lines = news()
    print(f"{len(lines)} headlines")
    if not lines:
        return print("No news fetched. Keeping previous themes.")
    g, today = connect(), dt.date.today()
    out = []
    for th in llm(lines).get("themes", [])[:MAX_THEMES]:
        syms = [s.strip().upper() for s in th.get("symbols", [])][:MAX_SYMBOLS]
        ok = [s for s in syms if tradable(g, s)]
        if th.get("confidence", 0) >= MIN_CONFIDENCE and ok:
            out.append({"name": th["name"], "thesis": th["thesis"], "confidence": th["confidence"],
                        "priced_in_risk": th.get("already_priced_in_risk", "unknown"),
                        "symbols": ok, "dropped": [s for s in syms if s not in ok],
                        "expires": str(today + dt.timedelta(days=LIFETIME_DAYS))})
    json.dump({"asof": str(today), "themes": out}, open("memory/themes.json", "w"), indent=2)
    with open("memory/lessons.md", "a") as f:
        for t in out:
            f.write(f"\n{today} | theme '{t['name']}' proposed {t['symbols']} (conf {t['confidence']}) | "
                    f"thesis: {t['thesis']} | outcome: pending (see journal src=theme:{t['name']})\n")
    print(json.dumps(out, indent=2) if out else "No actionable themes today.")


if __name__ == "__main__":
    main()
