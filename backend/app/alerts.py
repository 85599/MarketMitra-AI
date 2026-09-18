"""Rule-based market alerts computed from the latest indicator rows."""
import pandas as pd


def _crossed(prev_a, prev_b, a, b):
    return prev_a <= prev_b and a > b


def detect_alerts(df: pd.DataFrame, quote: dict | None = None) -> list[dict]:
    if df is None or len(df) < 30:
        return []
    alerts = []
    last, prev = df.iloc[-1], df.iloc[-2]
    close = float(last["Close"])

    def add(kind, severity, message, value=None):
        alerts.append({
            "id": f"{kind}-{df.index[-1].strftime('%Y%m%d')}",
            "type": kind,
            "severity": severity,
            "message": message,
            "value": value,
            "date": df.index[-1].strftime("%Y-%m-%d"),
        })

    day_ret = float(last["RET_1D"]) if pd.notna(last["RET_1D"]) else 0.0
    if abs(day_ret) >= 0.05:
        add("sharp_move", "high", f"Sharp {day_ret * 100:+.1f}% move in the last session", round(day_ret, 4))
    elif abs(day_ret) >= 0.03:
        add("sharp_move", "medium",
            f"Notable {day_ret * 100:+.1f}% move in the last session", round(day_ret, 4))

    rsi_now = float(last["RSI14"])
    if rsi_now >= 70:
        add("rsi_overbought", "medium", f"RSI at {rsi_now:.1f} — overbought territory", round(rsi_now, 1))
    elif rsi_now <= 30:
        add("rsi_oversold", "medium", f"RSI at {rsi_now:.1f} — oversold territory", round(rsi_now, 1))

    if _crossed(prev["MACD"], prev["MACD_SIGNAL"], last["MACD"], last["MACD_SIGNAL"]):
        add("macd_bullish_cross", "medium", "MACD crossed above its signal line — bullish momentum", None)
    if _crossed(prev["MACD_SIGNAL"], prev["MACD"], last["MACD_SIGNAL"], last["MACD"]):
        add("macd_bearish_cross", "medium", "MACD crossed below its signal line — bearish momentum", None)

    if pd.notna(last["SMA50"]) and pd.notna(prev["SMA50"]):
        if _crossed(prev["Close"], prev["SMA50"], last["Close"], last["SMA50"]):
            add("golden_cross_50", "medium", "Price crossed above the 50-day moving average", None)
        if _crossed(prev["SMA50"], prev["Close"], last["SMA50"], last["Close"]):
            add("break_below_50", "medium", "Price crossed below the 50-day moving average", None)
    if pd.notna(last["SMA50"]) and pd.notna(last["SMA200"]) and pd.notna(prev["SMA200"]):
        if _crossed(prev["SMA50"], prev["SMA200"], last["SMA50"], last["SMA200"]):
            add("golden_cross", "high", "Golden cross: 50-day MA crossed above 200-day MA", None)
        if _crossed(prev["SMA200"], prev["SMA50"], last["SMA200"], last["SMA50"]):
            add("death_cross", "high", "Death cross: 50-day MA crossed below 200-day MA", None)

    vol = float(last["Volume"])
    vol_avg = float(last["VOL_SMA20"]) if pd.notna(last["VOL_SMA20"]) else 0.0
    if vol_avg > 0 and vol >= 2 * vol_avg:
        add("volume_spike", "medium",
            f"Volume spike: {vol / vol_avg:.1f}x the 20-day average", round(vol / vol_avg, 1))

    if pd.notna(last["BB_UPPER"]) and close > float(last["BB_UPPER"]):
        add("bb_breakout_up", "low", "Close above the upper Bollinger band — stretched to the upside", None)
    if pd.notna(last["BB_LOWER"]) and close < float(last["BB_LOWER"]):
        add("bb_breakout_down", "low",
            "Close below the lower Bollinger band — stretched to the downside", None)

    if quote:
        hi, lo = quote.get("week52High"), quote.get("week52Low")
        if hi and close >= hi * 0.98:
            add("near_52w_high", "low", f"Trading within 2% of the 52-week high ({hi:,.2f})", None)
        if lo and close <= lo * 1.02:
            add("near_52w_low", "low", f"Trading within 2% of the 52-week low ({lo:,.2f})", None)

    order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: order.get(a["severity"], 3))
    return alerts
