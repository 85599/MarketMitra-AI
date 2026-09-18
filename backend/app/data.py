"""yfinance data access with a small in-memory TTL cache."""
import threading
import time

import pandas as pd
import yfinance as yf

from . import nse
from .indicators import enrich

_CACHE: dict[str, tuple[float, object]] = {}
_LOCK = threading.Lock()

TTL_QUOTE = 30          # seconds
TTL_HISTORY = 300       # seconds
TTL_NEWS = 600          # seconds
TTL_SEARCH = 3600       # seconds
TTL_OPTIONS = 60        # seconds
TTL_SCANNER = 120       # seconds


def _get(key: str, ttl: int, producer):
    now = time.time()
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
    value = producer()
    empty = (isinstance(value, (list, dict)) and len(value) == 0) or (hasattr(value, "empty") and value.empty)
    if value is None or empty:
        return value
    with _LOCK:
        _CACHE[key] = (now, value)
    return value


def search_tickers(query: str) -> list[dict]:
    def produce():
        try:
            res = yf.Search(query, max_results=10)
            quotes = getattr(res, "quotes", []) or []
        except Exception:
            quotes = []
        out = []
        for q in quotes:
            symbol = q.get("symbol")
            if not symbol:
                continue
            out.append({
                "symbol": symbol,
                "name": q.get("shortname") or q.get("longname") or symbol,
                "exchange": q.get("exchDisp") or q.get("exchange") or "",
                "type": q.get("quoteType") or "",
                "currency": q.get("currency") or "",
            })
        return out

    return _get(f"search:{query.lower()}", TTL_SEARCH, produce)


def get_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    def produce():
        df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
        if df.empty:
            return None
        idx = df.index
        if getattr(idx, "tz", None) is not None:
            idx = idx.tz_localize(None)
        df.index = idx.normalize()
        df = df.rename(columns=str.title)[["Open", "High", "Low", "Close", "Volume"]]
        return enrich(df)

    return _get(f"hist:{symbol}:{period}:{interval}", TTL_HISTORY, produce)


def get_quote(symbol: str) -> dict | None:
    def produce():
        tk = yf.Ticker(symbol)
        try:
            info = tk.fast_info
        except Exception:
            info = None
        quote: dict = {"symbol": symbol}
        if info is not None:
            def g(attr):
                try:
                    v = getattr(info, attr, None)
                    return float(v) if v is not None else None
                except Exception:
                    return None

            quote.update({
                "price": g("last_price"),
                "previousClose": g("previous_close"),
                "open": g("open"),
                "dayHigh": g("day_high"),
                "dayLow": g("day_low"),
                "marketCap": g("market_cap"),
                "currency": getattr(info, "currency", None),
                "exchange": getattr(info, "exchange", None),
            })
        try:
            meta = tk.info or {}
        except Exception:
            meta = {}
        for src, dst in [
            ("shortName", "name"), ("sector", "sector"), ("industry", "industry"),
            ("trailingPE", "pe"), ("forwardPE", "forwardPe"),
            ("fiftyTwoWeekHigh", "week52High"), ("fiftyTwoWeekLow", "week52Low"),
            ("trailingAnnualDividendYield", "dividendYield"),
            ("marketCap", "marketCapFallback"), ("currency", "currencyFallback"),
        ]:
            if meta.get(src) is not None:
                quote[dst] = meta[src]
        if quote.get("name") is None:
            quote["name"] = symbol
        if quote.get("currency") is None:
            quote["currency"] = quote.get("currencyFallback")
        quote.pop("currencyFallback", None)
        quote.pop("marketCapFallback", None)
        if quote.get("price") is None and quote.get("previousClose"):
            quote["price"] = quote["previousClose"]
        return quote if quote.get("price") is not None else None

    return _get(f"quote:{symbol}", TTL_QUOTE, produce)


def get_news(symbol: str) -> list[dict]:
    def produce():
        try:
            items = yf.Ticker(symbol).news or []
        except Exception:
            items = []
        out = []
        for it in items[:15]:
            content = it.get("content", it)
            title = content.get("title") or it.get("title")
            if not title:
                continue
            prov = content.get("provider")
            provider = prov.get("displayName") if isinstance(prov, dict) else None
            link = None
            canon = content.get("canonicalUrl")
            if isinstance(canon, dict):
                link = canon.get("url")
            link = link or content.get("link") or it.get("link")
            pub = content.get("pubDate") or it.get("providerPublishTime")
            if isinstance(pub, (int, float)):
                pub = pd.to_datetime(pub, unit="s").isoformat()
            out.append({
                "title": title,
                "publisher": provider or it.get("publisher") or "",
                "link": link or "",
                "published": str(pub) if pub else "",
            })
        return out

    return _get(f"news:{symbol}", TTL_NEWS, produce)


def get_options(symbol: str, expiry: str | None = None):
    def produce():
        if nse.is_indian_options(symbol):
            return nse.fetch_options(symbol, expiry)
        tk = yf.Ticker(symbol)
        expiries = list(tk.options or [])
        if not expiries:
            return None
        exp = expiry if expiry in expiries else expiries[0]
        chain = tk.option_chain(exp)
        return {"expiries": expiries, "expiry": exp,
                "calls": chain.calls, "puts": chain.puts}

    return _get(f"options:{symbol}:{expiry}", TTL_OPTIONS, produce)


def get_scanner_quotes(symbols: list[str]) -> dict:
    """Batched last/prev close for many symbols in one yfinance download."""
    def produce():
        try:
            df = yf.download(
                list(symbols), period="5d", interval="1d",
                group_by="ticker", auto_adjust=True, progress=False, threads=True,
            )
        except Exception:
            return None
        if df is None or df.empty:
            return None
        out = {}
        multi = isinstance(df.columns, pd.MultiIndex)
        for s in symbols:
            try:
                closes = (df[s]["Close"] if multi else df["Close"]).dropna()
            except (KeyError, TypeError):
                continue
            if len(closes) >= 2:
                last, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
                out[s] = {"price": round(last, 4),
                          "changePercent": round((last / prev - 1) * 100, 2) if prev else None}
            elif len(closes) == 1:
                out[s] = {"price": round(float(closes.iloc[-1]), 4), "changePercent": None}
        return out or None

    return _get(f"scanner:{','.join(symbols)}", TTL_SCANNER, produce)
