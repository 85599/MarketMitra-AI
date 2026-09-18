"""Alert rules fire on crafted indicator frames and stay quiet otherwise."""

from app.alerts import detect_alerts
from app.indicators import enrich
from tests.conftest import make_ohlcv


def _types(alerts):
    return {a["type"] for a in alerts}


def test_short_frame_returns_no_alerts():
    df = enrich(make_ohlcv(20))
    assert detect_alerts(df) == []


def test_sharp_move_high_severity():
    df = enrich(make_ohlcv(120))
    # Force a >5% jump on the last session.
    df.loc[df.index[-1], "Close"] = df["Close"].iloc[-2] * 1.08
    df["RET_1D"] = df["Close"].pct_change()
    alerts = detect_alerts(df)
    sharp = [a for a in alerts if a["type"] == "sharp_move"]
    assert sharp and sharp[0]["severity"] == "high"


def test_rsi_overbought_alert():
    df = enrich(make_ohlcv(120))
    df.loc[df.index[-1], "RSI14"] = 78.0
    assert "rsi_overbought" in _types(detect_alerts(df))


def test_rsi_oversold_alert():
    df = enrich(make_ohlcv(120))
    df.loc[df.index[-1], "RSI14"] = 22.0
    assert "rsi_oversold" in _types(detect_alerts(df))


def test_volume_spike_alert():
    df = enrich(make_ohlcv(120))
    df.loc[df.index[-1], "Volume"] = df["VOL_SMA20"].iloc[-1] * 3
    assert "volume_spike" in _types(detect_alerts(df))


def test_macd_bullish_cross():
    df = enrich(make_ohlcv(120))
    prev, last = df.index[-2], df.index[-1]
    df.loc[prev, ["MACD", "MACD_SIGNAL"]] = [1.0, 2.0]   # below
    df.loc[last, ["MACD", "MACD_SIGNAL"]] = [3.0, 2.0]   # crossed above
    assert "macd_bullish_cross" in _types(detect_alerts(df))


def test_near_52w_high_from_quote():
    df = enrich(make_ohlcv(120))
    close = float(df["Close"].iloc[-1])
    quote = {"week52High": close * 1.01, "week52Low": close * 0.6}
    assert "near_52w_high" in _types(detect_alerts(df, quote))


def test_alerts_sorted_by_severity():
    df = enrich(make_ohlcv(120))
    df.loc[df.index[-1], "Close"] = df["Close"].iloc[-2] * 1.09
    df["RET_1D"] = df["Close"].pct_change()
    df.loc[df.index[-1], "RSI14"] = 75.0
    order = {"high": 0, "medium": 1, "low": 2}
    alerts = detect_alerts(df)
    ranks = [order[a["severity"]] for a in alerts]
    assert ranks == sorted(ranks)


def test_calm_market_has_no_high_severity():
    df = enrich(make_ohlcv(200, seed=3))
    # Neutralize the last bar so nothing dramatic triggers.
    df.loc[df.index[-1], "RSI14"] = 50.0
    high_sev = [a for a in detect_alerts(df) if a["severity"] == "high"]
    assert all(a["type"] in {"golden_cross", "death_cross", "sharp_move"} for a in high_sev)
