"""Forecast output shape, ranges and multi-horizon structure (no accuracy claims)."""

from app import forecast as fc
from app.indicators import enrich
from tests.conftest import make_ohlcv


def test_insufficient_history_returns_error():
    df = enrich(make_ohlcv(60))
    assert "error" in fc.forecast(df)


def test_forecast_top_level_shape(enriched):
    res = fc.forecast(enriched)
    assert "error" not in res
    for key in ["lastClose", "predictedPrice", "predictedReturn", "direction",
                "range80", "range95", "confidence", "horizons", "modelStats", "history"]:
        assert key in res
    assert res["direction"] in {"up", "down"}
    assert 0.0 <= res["confidence"] <= 1.0


def test_ranges_are_ordered_and_bracket_prediction(enriched):
    res = fc.forecast(enriched)
    lo80, hi80 = res["range80"]
    lo95, hi95 = res["range95"]
    assert lo95 <= lo80 <= res["predictedPrice"] <= hi80 <= hi95


def test_all_horizons_present_and_consistent(enriched):
    res = fc.forecast(enriched)
    hs = [h["h"] for h in res["horizons"]]
    assert hs == fc.HORIZONS
    last_close = res["lastClose"]
    for h in res["horizons"]:
        assert h["direction"] in {"up", "down"}
        assert h["range80"][0] <= h["predictedPrice"] <= h["range80"][1]
        assert h["range95"][0] <= h["range95"][1]
        # predicted price must equal lastClose * (1 + return) within rounding
        assert abs(h["predictedPrice"] - last_close * (1 + h["predictedReturn"])) < 0.05
        assert 0.0 <= h["directionAccuracy"] <= 1.0


def test_wider_uncertainty_at_longer_horizon(enriched):
    res = fc.forecast(enriched)
    widths = [h["range95"][1] - h["range95"][0] for h in res["horizons"]]
    # 10-day band should not be tighter than the 1-day band.
    assert widths[-1] >= widths[0]


def test_history_rows_have_predicted_and_actual(enriched):
    res = fc.forecast(enriched)
    assert res["history"], "expected a backtest history"
    for row in res["history"]:
        assert {"date", "predictedReturn", "actualReturn", "predictedPrice", "actualPrice"} <= row.keys()


def test_model_stats_architecture(enriched):
    res = fc.forecast(enriched)
    stats = res["modelStats"]
    assert stats["ensembleSize"] == fc.ENSEMBLE
    assert stats["horizons"] == fc.HORIZONS
    assert f"x{fc.ENSEMBLE}" in stats["architecture"]


def test_forecast_is_deterministic(enriched):
    a = fc.forecast(enriched)["predictedPrice"]
    b = fc.forecast(enriched)["predictedPrice"]
    assert a == b
