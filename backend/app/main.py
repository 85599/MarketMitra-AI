"""StockVision AI backend — FastAPI application."""
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import data, payoff, sentiment, store, universe
from . import forecast as fc
from .alerts import detect_alerts
from .assets import BENCH_BY_CLASS, CLASS_LABELS, asset_class

app = FastAPI(title="MarketMitra AI", version="2.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

INDICATOR_FIELDS = ["SMA20", "SMA50", "SMA200", "EMA9", "EMA21", "RSI14",
                    "MACD", "MACD_SIGNAL", "MACD_HIST", "BB_UPPER", "BB_LOWER"]


@app.on_event("startup")
def startup():
    store.init_db()


def _df_to_series(df: pd.DataFrame, cols: list[str]) -> list[dict]:
    out = []
    idx = df.index
    for i in range(len(df)):
        row = {"time": pd.Timestamp(idx[i]).strftime("%Y-%m-%d")}
        for c in cols:
            v = df[c].values[i]
            row[c] = None if pd.isna(v) else round(float(v), 4)
        out.append(row)
    return out


@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


@app.get("/api/search")
def search(q: str = Query(min_length=1)):
    results = data.search_tickers(q)
    if not results:
        results = [{"symbol": q.upper(), "name": q.upper(), "exchange": "", "type": "", "currency": ""}]
    return {"results": results}


@app.get("/api/quote/{symbol}")
def quote(symbol: str):
    q = data.get_quote(symbol)
    if not q:
        raise HTTPException(404, f"No quote data for {symbol}")
    cls = asset_class(symbol)
    q["assetClass"] = cls
    q["classLabel"] = CLASS_LABELS[cls]
    if q.get("price") is not None and q.get("previousClose"):
        q["change"] = round(q["price"] - q["previousClose"], 4)
        q["changePercent"] = round((q["price"] / q["previousClose"] - 1) * 100, 2)
    return q


@app.get("/api/history/{symbol}")
def history(
    symbol: str,
    period: str = Query("1y", pattern="^(1mo|3mo|6mo|1y|2y|5y|max)$"),
    interval: str = Query("1d", pattern="^(1d|1wk|1mo)$"),
):
    df = data.get_history(symbol, period, interval)
    if df is None or df.empty:
        raise HTTPException(404, f"No history for {symbol}")
    ohlc = [
        {
            "time": pd.Timestamp(idx).strftime("%Y-%m-%d"),
            "open": round(float(r["Open"]), 4),
            "high": round(float(r["High"]), 4),
            "low": round(float(r["Low"]), 4),
            "close": round(float(r["Close"]), 4),
            "volume": int(r["Volume"]) if pd.notna(r["Volume"]) else 0,
        }
        for idx, r in df.iterrows()
    ]
    indicators = _df_to_series(df, INDICATOR_FIELDS)
    rets = df["RET_1D"].dropna()
    daily_returns = [
        {"time": pd.Timestamp(idx).strftime("%Y-%m-%d"), "value": round(float(v) * 100, 3)}
        for idx, v in rets.items()
    ]
    stats = {
        "volatilityAnn": round(float(rets.std() * np.sqrt(252) * 100), 2) if len(rets) > 5 else None,
        "maxDrawdown": round(float(((df["Close"] / df["Close"].cummax()) - 1).min() * 100), 2),
        "periodReturn": round(float((df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100), 2),
        "avgVolume": int(df["Volume"].tail(20).mean()) if len(df) >= 20 else None,
    }
    return {"symbol": symbol, "period": period, "interval": interval,
            "candles": ohlc, "indicators": indicators,
            "dailyReturns": daily_returns, "stats": stats}


@app.get("/api/forecast/{symbol}")
def forecast(symbol: str):
    df = data.get_history(symbol, "2y", "1d")
    if df is None or len(df) < 120:
        raise HTTPException(400, f"Not enough history for {symbol}")
    result = fc.forecast(df)
    if "error" in result:
        raise HTTPException(400, result["error"])
    result["symbol"] = symbol
    result["generatedAt"] = datetime.now(UTC).isoformat()

    created = datetime.now(UTC)
    created_at = created.strftime("%Y-%m-%d %H:%M")
    target_date = (created + timedelta(days=1)).strftime("%Y-%m-%d")
    store.save_prediction(symbol, created_at, target_date, result["lastClose"],
                          result["predictedPrice"], result["predictedReturn"],
                          result["range80"][0], result["range80"][1])
    return result


@app.get("/api/predictions/{symbol}")
def predictions(symbol: str):
    df = data.get_history(symbol, "3mo", "1d")
    if df is not None and not df.empty:
        closes = {pd.Timestamp(idx).strftime("%Y-%m-%d"): float(r["Close"])
                  for idx, r in df.iterrows()}
        store.resolve_pending(symbol, closes)
    rows = store.list_predictions(symbol)
    perf = store.performance(symbol)
    return {"symbol": symbol, "predictions": rows, "performance": perf}


@app.get("/api/news/{symbol}")
def news(symbol: str):
    items = data.get_news(symbol)
    result = sentiment.analyze_news(items)
    result["symbol"] = symbol
    return result


@app.get("/api/alerts/{symbol}")
def alerts(symbol: str):
    df = data.get_history(symbol, "6mo", "1d")
    if df is None or df.empty:
        raise HTTPException(404, f"No data for {symbol}")
    q = data.get_quote(symbol)
    return {"symbol": symbol, "alerts": detect_alerts(df, q)}


@app.get("/api/context/{symbol}")
def market_context(symbol: str):
    df = data.get_history(symbol, "1y", "1d")
    if df is None or len(df) < 60:
        raise HTTPException(400, f"Not enough history for {symbol}")

    sym_rets = df["RET_1D"].dropna()
    benchmarks = {}
    for b_sym, b_name in BENCH_BY_CLASS[asset_class(symbol)].items():
        if b_sym == symbol:
            continue
        b_df = data.get_history(b_sym, "1y", "1d")
        if b_df is None or b_df.empty:
            continue
        b_rets = b_df["RET_1D"].dropna()
        joined = pd.concat([sym_rets, b_rets], axis=1, join="inner").dropna()
        if len(joined) < 30:
            continue
        cov = np.cov(joined.values.T)
        beta = float(cov[0, 1] / cov[1, 1]) if cov[1, 1] else None
        corr = float(np.corrcoef(joined.values.T)[0, 1])

        def perf(series, days):
            if len(series) <= days:
                return None
            return round(float((series.iloc[-1] / series.iloc[-days - 1] - 1) * 100), 2)

        benchmarks[b_sym] = {
            "name": b_name,
            "beta": round(beta, 2) if beta is not None else None,
            "correlation": round(corr, 2),
            "rs": {
                "1m": (perf(df["Close"], 21), perf(b_df["Close"], 21)),
                "3m": (perf(df["Close"], 63), perf(b_df["Close"], 63)),
                "6m": (perf(df["Close"], 126), perf(b_df["Close"], 126)),
                "1y": (perf(df["Close"], 252), perf(b_df["Close"], 252)),
            },
        }

    close = df["Close"]
    hi52, lo52 = float(close.max()), float(close.min())
    last = float(close.iloc[-1])
    ann_vol = float(sym_rets.std() * np.sqrt(252) * 100) if len(sym_rets) > 5 else None
    sharpe = None
    if len(sym_rets) > 5 and sym_rets.std() > 0:
        sharpe = round(float(sym_rets.mean() / sym_rets.std() * np.sqrt(252)), 2)

    norm = (close / close.iloc[0] * 100).round(2)
    rs_line = {
        "dates": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in df.index],
        "values": norm.tolist(),
    }

    return {
        "symbol": symbol,
        "positionInRange52": round((last - lo52) / (hi52 - lo52) * 100, 1) if hi52 > lo52 else 50.0,
        "high52": round(hi52, 2),
        "low52": round(lo52, 2),
        "annualizedVolatility": round(ann_vol, 2) if ann_vol else None,
        "sharpeRatio": sharpe,
        "benchmarks": benchmarks,
        "normalizedLine": rs_line,
    }


@app.get("/api/options/{symbol}")
def options(symbol: str, expiry: str | None = None):
    raw = data.get_options(symbol, expiry)
    if raw is None:
        return {"symbol": symbol, "available": False, "expiries": [], "chain": [], "stats": None}

    calls, puts = raw["calls"], raw["puts"]
    spot = raw.get("spot")
    if spot is None:
        quote_data = data.get_quote(symbol)
        spot = quote_data.get("price") if quote_data else None
    if spot is None and not calls.empty:
        spot = float(calls["strike"].median())

    def clean(df):
        cols = ["strike", "lastPrice", "bid", "ask", "impliedVolatility", "volume",
                "openInterest", "changeinOpenInterest"]
        out = df[[c for c in cols if c in df.columns]].copy()
        for c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
        return out

    calls_c, puts_c = clean(calls), clean(puts)

    call_oi = float(calls_c["openInterest"].fillna(0).sum()) if "openInterest" in calls_c else 0.0
    put_oi = float(puts_c["openInterest"].fillna(0).sum()) if "openInterest" in puts_c else 0.0
    pcr = round(put_oi / call_oi, 2) if call_oi else None

    strikes = np.unique(np.concatenate([calls_c["strike"].dropna().values, puts_c["strike"].dropna().values]))
    max_pain = None
    if len(strikes) and "openInterest" in calls_c and "openInterest" in puts_c:
        co = calls_c.groupby("strike")["openInterest"].sum().fillna(0)
        po = puts_c.groupby("strike")["openInterest"].sum().fillna(0)
        best, best_pain = None, None
        for k in strikes:
            pain = float(
                (co.values * np.maximum(k - co.index.values, 0)).sum()
                + (po.values * np.maximum(po.index.values - k, 0)).sum()
            )
            if best_pain is None or pain < best_pain:
                best, best_pain = k, pain
        max_pain = float(best)

    window = calls_c if spot is None else calls_c.reindex(
        (calls_c["strike"] - spot).abs().sort_values().index
    )
    if spot is not None and len(window):
        atm_strike = float(window["strike"].iloc[0])
        tol = atm_strike * 0.06 + 1e-9
        near_c = calls_c[(calls_c["strike"] - atm_strike).abs() <= tol]["strike"].dropna()
        near_p = puts_c[(puts_c["strike"] - atm_strike).abs() <= tol]["strike"].dropna()
        keep = sorted(set(near_c) | set(near_p))
    else:
        atm_strike = None
        keep = sorted(set(calls_c["strike"].dropna()) | set(puts_c["strike"].dropna()))[:15]

    c_by = {round(float(r["strike"]), 4): r for _, r in calls_c.iterrows() if pd.notna(r["strike"])}
    p_by = {round(float(r["strike"]), 4): r for _, r in puts_c.iterrows() if pd.notna(r["strike"])}
    chain = []
    for k in keep:
        key = round(float(k), 4)
        c, p = c_by.get(key), p_by.get(key)

        def val(row, col):
            v = row.get(col) if row is not None else None
            return None if v is None or pd.isna(v) else float(v)

        def side(row):
            if row is None:
                return None
            iv = val(row, "impliedVolatility")
            vol = val(row, "volume")
            oi = val(row, "openInterest")
            oic = val(row, "changeinOpenInterest")
            return {
                "ltp": val(row, "lastPrice"),
                "iv": round(iv * 100, 1) if iv is not None else None,
                "volume": int(vol) if vol is not None else 0,
                "oi": int(oi) if oi is not None else 0,
                "oiChange": int(oic) if oic is not None else 0,
            }

        chain.append({"strike": key, "call": side(c), "put": side(p),
                      "atm": atm_strike is not None and abs(float(k) - atm_strike) < 1e-9})

    atm_iv = None
    if atm_strike is not None:
        row = c_by.get(round(atm_strike, 4))
        iv = val(row, "impliedVolatility") if row is not None else None
        if iv is not None:
            atm_iv = round(iv * 100, 1)

    return {
        "symbol": symbol,
        "available": True,
        "expiries": raw["expiries"],
        "expiry": raw["expiry"],
        "spot": round(spot, 2) if spot else None,
        "stats": {
            "pcr": pcr,
            "maxPain": max_pain,
            "callOI": int(call_oi),
            "putOI": int(put_oi),
            "atmIV": atm_iv,
        },
        "chain": chain,
    }


@app.get("/api/payoff/{symbol}")
def payoff_view(
    symbol: str,
    expiry: str | None = None,
    strategy: str = Query("STRADDLE", pattern="^(STRADDLE|STRANGLE|BULL_CALL|BEAR_PUT|IRONCONDOR)$"),
):
    raw = data.get_options(symbol, expiry)
    if raw is None:
        raise HTTPException(404, f"No options for {symbol}")
    calls, puts = raw["calls"], raw["puts"]
    spot = raw.get("spot")
    if spot is None:
        q = data.get_quote(symbol)
        spot = q.get("price") if q else None
    if spot is None and not calls.empty:
        spot = float(calls["strike"].median())

    def num(df):
        cols = [c for c in ["strike", "lastPrice"] if c in df.columns]
        out = df[cols].copy()
        for c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
        return out

    result = payoff.analyze(strategy, num(calls), num(puts), spot)
    if "error" in result:
        raise HTTPException(400, result["error"])
    result["symbol"] = symbol
    result["expiry"] = raw["expiry"]
    result["expiries"] = raw["expiries"]
    result["strategies"] = [{"id": k, "label": v} for k, v in payoff.STRATEGIES.items()]
    return result


@app.get("/api/universes")
def universes():
    return {
        "default": universe.DEFAULT_UNIVERSE,
        "universes": [
            {"id": k, "label": v["label"], "count": len(v["symbols"])}
            for k, v in universe.UNIVERSES.items()
        ],
    }


@app.get("/api/scanner")
def scanner(u: str = Query("nifty50")):
    uni = universe.get_universe(u)
    syms = [x["symbol"] for x in uni["symbols"]]
    meta = {x["symbol"]: x for x in uni["symbols"]}
    quotes = data.get_scanner_quotes(syms) or {}

    rows = []
    for s in syms:
        q = quotes.get(s)
        if not q or q.get("changePercent") is None:
            continue
        m = meta[s]
        rows.append({
            "symbol": s, "name": m["name"], "sector": m["sector"],
            "price": q["price"], "changePercent": q["changePercent"],
        })
    rows.sort(key=lambda r: r["changePercent"], reverse=True)

    gainers = rows[:5]
    losers = list(reversed(rows[-5:])) if len(rows) > 5 else list(reversed(rows))

    by_sector: dict[str, list[float]] = {}
    for r in rows:
        by_sector.setdefault(r["sector"], []).append(r["changePercent"])
    sectors = [
        {"sector": k, "changePercent": round(sum(v) / len(v), 2), "count": len(v)}
        for k, v in by_sector.items()
    ]
    sectors.sort(key=lambda x: x["changePercent"], reverse=True)

    return {
        "universe": u, "label": uni["label"],
        "asOf": datetime.now(UTC).isoformat(),
        "rows": rows, "gainers": gainers, "losers": losers, "sectors": sectors,
    }


@app.get("/api/watchlist")
def watchlist(symbols: str = Query(min_length=1)):
    syms = [s.strip() for s in symbols.split(",") if s.strip()][:20]
    out = []
    for s in syms:
        q = data.get_quote(s)
        if not q or q.get("price") is None:
            continue
        cls = asset_class(s)
        chg = None
        if q.get("previousClose"):
            chg = round((q["price"] / q["previousClose"] - 1) * 100, 2)
        out.append({
            "symbol": s, "name": q.get("name", s), "price": q.get("price"),
            "changePercent": chg, "currency": q.get("currency"),
            "assetClass": cls, "classLabel": CLASS_LABELS[cls],
        })
    return {"symbols": out}
