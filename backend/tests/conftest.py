"""Shared fixtures: synthetic OHLCV data, no network access."""
import numpy as np
import pandas as pd
import pytest


def make_ohlcv(n: int = 300, start: float = 100.0, seed: int = 7) -> pd.DataFrame:
    """Deterministic random-walk OHLCV frame with a normalized DatetimeIndex."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0004, 0.015, n)
    close = start * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0, 0.006, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.006, n)))
    open_ = np.concatenate([[start], close[:-1]])
    volume = rng.integers(1_000_000, 5_000_000, n).astype(float)
    idx = pd.date_range("2023-01-02", periods=n, freq="B")
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )


@pytest.fixture
def ohlcv() -> pd.DataFrame:
    return make_ohlcv()


@pytest.fixture
def enriched(ohlcv) -> pd.DataFrame:
    from app.indicators import enrich
    return enrich(ohlcv)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Redirect the SQLite store to a temp file so tests never touch the real DB."""
    from app import store
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test_predictions.db")
