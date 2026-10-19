import logging

import httpx

from newsagent.models import Slide

log = logging.getLogger("newsagent")
INDICES = [("Sensex", "^BSESN"), ("Nifty 50", "^NSEI"), ("Nasdaq", "^IXIC"), ("S&P 500", "^GSPC")]


def _quote(symbol: str) -> list[str]:
    r = httpx.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        params={"interval": "1d", "range": "1d"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    r.raise_for_status()
    m = r.json()["chart"]["result"][0]["meta"]
    price, high, low = m["regularMarketPrice"], m["regularMarketDayHigh"], m["regularMarketDayLow"]
    prev = m.get("chartPreviousClose") or price
    return [f"{price:,.2f}", f"{high:,.2f}", f"{low:,.2f}", f"{(price - prev) / prev * 100:+.2f}%"]


def market_slide() -> Slide:
    rows = [["Index", "Last", "High", "Low", "Chg"]]
    for name, sym in INDICES:
        try:
            rows.append([name, *_quote(sym)])
        except Exception as e:  # unofficial endpoint, never break the run
            log.warning("Quote failed for %s: %s", name, e)
            rows.append([name, "n/a", "n/a", "n/a", "n/a"])
    return Slide(
        category="MARKETS",
        headline="Market snapshot: today's highs and lows",
        source="Yahoo Finance",
        subject="Bombay Stock Exchange",
        keywords="stock exchange",
        rows=rows,
    )
