"""NSE India option-chain fetcher.

Yahoo Finance (yfinance) does not carry option chains for NSE/BSE symbols, so
Indian underlyings are served straight from NSE's public JSON API. NSE requires
a cookie warm-up handshake before the API responds, and the chain is a two-step
flow: contract-info (expiry list) then option-chain-v3 (the chain itself).
"""
import threading
from datetime import datetime

import pandas as pd
import requests

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/option-chain",
    "X-Requested-With": "XMLHttpRequest",
}

# yfinance index symbol -> NSE underlying name (only those with listed options).
_INDEX_MAP = {
    "^NSEI": "NIFTY",
    "^NSEBANK": "BANKNIFTY",
    "^CNXIT": "FINNIFTY",
}
_INDEX_NAMES = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYMIDSELECT"}

_BASE = "https://www.nseindia.com"
_session: requests.Session | None = None
_lock = threading.Lock()


def is_indian_options(symbol: str) -> bool:
    s = symbol.upper()
    return s in _INDEX_MAP or s in _INDEX_NAMES or s.endswith(".NS") or s.endswith(".BO")


def _underlying(symbol: str) -> tuple[str, str]:
    s = symbol.upper()
    if s in _INDEX_MAP:
        return _INDEX_MAP[s], "Indices"
    if s in _INDEX_NAMES:
        return s, "Indices"
    return s.split(".")[0], "Equity"


def _warm(force: bool = False) -> requests.Session:
    global _session
    with _lock:
        if _session is not None and not force:
            return _session
        s = requests.Session()
        s.headers.update(_HEADERS)
        try:
            s.get(_BASE, timeout=15)
            s.get(f"{_BASE}/option-chain", timeout=15)
        except requests.RequestException:
            pass
        _session = s
        return _session


def _get_json(url: str, retries: int = 2):
    for attempt in range(retries + 1):
        s = _warm(force=attempt > 0)
        try:
            r = s.get(url, timeout=15)
            if r.status_code == 200 and r.content and r.content.strip() not in (b"{}", b"[]"):
                return r.json()
        except (requests.RequestException, ValueError):
            continue
    return None


def _to_iso(nse_date: str) -> str:
    try:
        return datetime.strptime(nse_date, "%d-%b-%Y").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return nse_date


def _to_nse(iso_date: str) -> str:
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d-%b-%Y")
    except (ValueError, TypeError):
        return iso_date


def _side_df(rows: list[dict], side: str) -> pd.DataFrame:
    recs = []
    for row in rows:
        leg = row.get(side)
        if not leg:
            continue
        recs.append({
            "strike": leg.get("strikePrice"),
            "lastPrice": leg.get("lastPrice"),
            "bid": leg.get("buyPrice1"),
            "ask": leg.get("sellPrice1"),
            # NSE quotes IV as a percentage; store as a decimal to match yfinance
            # so the shared normalizer in main.py (iv * 100) restores it.
            "impliedVolatility": (leg.get("impliedVolatility") or 0) / 100.0,
            "volume": leg.get("totalTradedVolume"),
            "openInterest": leg.get("openInterest"),
            "changeinOpenInterest": leg.get("changeinOpenInterest"),
        })
    return pd.DataFrame(recs)


def fetch_options(symbol: str, expiry_iso: str | None = None) -> dict | None:
    underlying, otype = _underlying(symbol)

    ci = _get_json(f"{_BASE}/api/option-chain-contract-info?symbol={underlying}")
    expiries_nse = (ci or {}).get("expiryDates") or []
    if not expiries_nse:
        return None
    expiries_iso = [_to_iso(e) for e in expiries_nse]

    if expiry_iso and expiry_iso in expiries_iso:
        chosen_nse = _to_nse(expiry_iso)
        chosen_iso = expiry_iso
    else:
        chosen_nse = expiries_nse[0]
        chosen_iso = expiries_iso[0]

    chain = _get_json(
        f"{_BASE}/api/option-chain-v3?type={otype}&symbol={underlying}&expiry={chosen_nse}"
    )
    rec = (chain or {}).get("records") or {}
    rows = rec.get("data") or []
    if not rows:
        return None

    calls = _side_df(rows, "CE")
    puts = _side_df(rows, "PE")
    if calls.empty and puts.empty:
        return None

    return {
        "expiries": expiries_iso,
        "expiry": chosen_iso,
        "calls": calls,
        "puts": puts,
        "spot": rec.get("underlyingValue"),
    }
