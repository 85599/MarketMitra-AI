"""Indicator math: bounds, alignment and column completeness."""
import numpy as np
import pandas as pd

from app.indicators import ema, enrich, rsi, sma


def test_sma_matches_manual_mean(ohlcv):
    s = sma(ohlcv["Close"], 20)
    assert np.isclose(s.iloc[25], ohlcv["Close"].iloc[6:26].mean())
    assert s.iloc[:19].isna().all()  # not enough history yet


def test_ema_no_nans_after_warmup(ohlcv):
    e = ema(ohlcv["Close"], 9)
    assert e.notna().all()


def test_rsi_stays_in_range(enriched):
    r = enriched["RSI14"].dropna()
    assert ((r >= 0) & (r <= 100)).all()


def test_rsi_extreme_series():
    # Positive drift with genuine down-steps (a pure monotonic series has zero
    # losses, which the RSI guard fills to a neutral 50).
    rng = np.random.default_rng(1)
    up = pd.Series(100 + np.cumsum(rng.normal(1.2, 0.8, 80)))
    assert rsi(up).iloc[-1] > 65
    down = pd.Series(300 + np.cumsum(rng.normal(-1.2, 0.8, 80)))
    assert rsi(down).iloc[-1] < 35


def test_bollinger_ordering(enriched):
    valid = enriched.dropna(subset=["BB_UPPER", "BB_LOWER"])
    assert (valid["BB_UPPER"] >= valid["BB_LOWER"]).all()


def test_macd_histogram_is_difference(enriched):
    hist = enriched["MACD"] - enriched["MACD_SIGNAL"]
    assert np.allclose(hist.dropna(), enriched["MACD_HIST"].dropna(), atol=1e-9)


def test_atr_positive(enriched):
    assert (enriched["ATR14"].dropna() > 0).all()


def test_enrich_adds_all_forecast_columns(ohlcv):
    out = enrich(ohlcv)
    for col in ["SMA20", "SMA50", "SMA200", "EMA9", "RSI14", "MACD_HIST",
                "ATR14", "VOL_SMA20", "RET_1D"]:
        assert col in out.columns
    assert len(out) == len(ohlcv)  # row count preserved
