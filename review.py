"""Learn from memory/journal.jsonl. Writes memory/review_report.md for the LLM to read.

    python review.py            # report only
    python review.py --apply    # also halts trading (creates STOP) if the edge is proven negative
"""
import json, os, sys, datetime as dt
from collections import defaultdict

MIN_TRADES = 30   # below this, results are noise: no conclusions, no parameter changes


def load():
    if not os.path.exists("memory/journal.jsonl"):
        return []
    return [json.loads(l) for l in open("memory/journal.jsonl") if l.strip()]


def summarize(rows):
    pnl = [r["pnl"] for r in rows]
    wins = [x for x in pnl if x > 0]
    losses = [x for x in pnl if x <= 0]
    n = len(pnl)
    return {"n": n, "total": round(sum(pnl), 2), "win_rate": round(len(wins) / n, 2) if n else 0,
            "avg_win": round(sum(wins) / len(wins), 2) if wins else 0,
            "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0,
            "expectancy": round(sum(pnl) / n, 2) if n else 0}


def group(rows, key):
    g = defaultdict(list)
    for r in rows:
        g[key(r)].append(r)
    return {k: summarize(v) for k, v in sorted(g.items())}


def main():
    sells = [r for r in load() if r["type"] == "SELL"]
    s = summarize(sells)
    lines = [f"# Review {dt.date.today()}", "",
             f"Closed trades: {s['n']} (need {MIN_TRADES} before drawing conclusions)", "",
             f"Overall (after all costs): {s}", "",
             "By exit reason: " + json.dumps(group(sells, lambda r: r["reason"])), "",
             "By source (core vs news theme): " + json.dumps(group(sells, lambda r: r.get("src", "core"))), "",
             "By symbol: " + json.dumps(group(sells, lambda r: r["sym"])), "",
             "By RSI bucket at exit: " + json.dumps(group(sells, lambda r: f"{int(r['rsi'] // 10) * 10}s")), ""]
    verdict = "INSUFFICIENT DATA: change nothing."
    if s["n"] >= MIN_TRADES:
        verdict = ("EDGE NOT PROVEN NEGATIVE: keep running; propose at most ONE small param change."
                   if s["expectancy"] >= 0 else
                   "NEGATIVE EXPECTANCY AFTER COSTS: halt trading and rethink the strategy.")
    lines += [f"**Verdict:** {verdict}"]
    open("memory/review_report.md", "w").write("\n".join(lines))
    print("\n".join(lines))

    if "--apply" in sys.argv and s["n"] >= MIN_TRADES and s["expectancy"] < 0:
        open("STOP", "w").write("halted by review.py")
        with open("memory/lessons.md", "a") as f:
            f.write(f"\n{dt.date.today()} | expectancy {s['expectancy']} over {s['n']} trades "
                    f"| halted trading (STOP file created)\n")
        print("\nSTOP file created.")


if __name__ == "__main__":
    main()
