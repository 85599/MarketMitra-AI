"""Option strategy payoff builder.

Pure functions over a normalized chain so they are easy to unit-test. Payoffs
are per one unit of each leg, computed at expiry (intrinsic value only).
"""
import numpy as np
import pandas as pd

STRATEGIES = {
    "STRADDLE": "Long Straddle",
    "STRANGLE": "Long Strangle",
    "BULL_CALL": "Bull Call Spread",
    "BEAR_PUT": "Bear Put Spread",
    "IRONCONDOR": "Iron Condor",
}


def _ltp_map(df: pd.DataFrame) -> dict[float, float]:
    out = {}
    if df is None or df.empty or "strike" not in df or "lastPrice" not in df:
        return out
    for _, r in df.iterrows():
        k, lp = r.get("strike"), r.get("lastPrice")
        if pd.isna(k):
            continue
        out[round(float(k), 4)] = 0.0 if pd.isna(lp) else float(lp)
    return out


def _sorted_strikes(calls: pd.DataFrame, puts: pd.DataFrame) -> list[float]:
    vals = []
    for df in (calls, puts):
        if df is not None and not df.empty and "strike" in df:
            vals.extend(df["strike"].dropna().astype(float).tolist())
    return sorted(set(round(v, 4) for v in vals))


def _atm_and_step(strikes: list[float], spot: float) -> tuple[float, float]:
    atm = min(strikes, key=lambda k: abs(k - spot))
    diffs = [b - a for a, b in zip(strikes, strikes[1:], strict=False) if b > a]
    step = float(np.median(diffs)) if diffs else max(atm * 0.01, 1.0)
    return atm, step


def _nth(strikes: list[float], atm: float, offset: int) -> float:
    """Strike `offset` steps away from ATM (positive = higher)."""
    if offset == 0:
        return atm
    target = atm
    if offset > 0:
        for _ in range(offset):
            nxt = [k for k in strikes if k > target + 1e-9]
            if nxt:
                target = nxt[0]
    else:
        for _ in range(-offset):
            prv = [k for k in strikes if k < target - 1e-9]
            if prv:
                target = prv[-1]
    return target


def build_legs(strategy: str, strikes: list[float], spot: float,
               call_ltp: dict, put_ltp: dict) -> list[dict]:
    atm, _ = _atm_and_step(strikes, spot)
    n = lambda off: _nth(strikes, atm, off)

    def call(off, side):
        k = n(off)
        return {"type": "call", "strike": round(k, 2), "side": side,
                "premium": round(call_ltp.get(round(k, 4), 0.0), 2)}

    def put(off, side):
        k = n(off)
        return {"type": "put", "strike": round(k, 2), "side": side,
                "premium": round(put_ltp.get(round(k, 4), 0.0), 2)}

    s = strategy.upper()
    if s == "STRADDLE":
        return [call(0, "long"), put(0, "long")]
    if s == "STRANGLE":
        return [call(2, "long"), put(-2, "long")]
    if s == "BULL_CALL":
        return [call(0, "long"), call(3, "short")]
    if s == "BEAR_PUT":
        return [put(0, "long"), put(-3, "short")]
    if s == "IRONCONDOR":
        return [call(2, "short"), call(5, "long"), put(-2, "short"), put(-5, "long")]
    raise ValueError(f"unknown strategy: {strategy}")


def leg_payoff(leg: dict, spots: np.ndarray) -> np.ndarray:
    k, prem, side = leg["strike"], leg["premium"], leg["side"]
    if leg["type"] == "call":
        intrinsic = np.maximum(spots - k, 0.0)
    else:
        intrinsic = np.maximum(k - spots, 0.0)
    return (intrinsic - prem) if side == "long" else (prem - intrinsic)


def net_premium(legs: list[dict]) -> float:
    """Positive = net debit (paid), negative = net credit (received)."""
    return round(sum(x["premium"] if x["side"] == "long" else -x["premium"] for x in legs), 2)


def breakevens(spots: np.ndarray, payoff: np.ndarray) -> list[float]:
    bes = []
    for i in range(len(payoff) - 1):
        a, b = payoff[i], payoff[i + 1]
        if a == 0:
            bes.append(round(float(spots[i]), 2))
        elif a * b < 0:
            t = a / (a - b)
            bes.append(round(float(spots[i] + t * (spots[i + 1] - spots[i])), 2))
    return bes


def analyze(strategy: str, calls: pd.DataFrame, puts: pd.DataFrame, spot: float) -> dict:
    strikes = _sorted_strikes(calls, puts)
    if not strikes or spot is None:
        return {"error": "no chain data for payoff"}
    call_ltp, put_ltp = _ltp_map(calls), _ltp_map(puts)
    legs = build_legs(strategy, strikes, float(spot), call_ltp, put_ltp)

    leg_strikes = [x["strike"] for x in legs]
    lo = min(float(spot) * 0.8, min(leg_strikes) * 0.9)
    hi = max(float(spot) * 1.2, max(leg_strikes) * 1.1)
    spots = np.linspace(lo, hi, 121)
    payoff = np.sum([leg_payoff(x, spots) for x in legs], axis=0)

    return {
        "strategy": strategy.upper(),
        "label": STRATEGIES.get(strategy.upper(), strategy),
        "spot": round(float(spot), 2),
        "legs": legs,
        "netPremium": net_premium(legs),
        "spots": [round(float(s), 2) for s in spots],
        "payoff": [round(float(p), 2) for p in payoff],
        "maxProfit": round(float(payoff.max()), 2),
        "maxLoss": round(float(payoff.min()), 2),
        "breakevens": breakevens(spots, payoff),
    }
