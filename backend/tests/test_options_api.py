"""Options + payoff HTTP endpoints with a mocked chain (no network, no NSE)."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import data
from app.main import app


def _mock_chain(spot=100.0):
    strikes = np.arange(80, 121, 5, dtype=float)
    calls = pd.DataFrame({
        "strike": strikes,
        "lastPrice": np.maximum(spot - strikes, 0) + 3.0,
        "bid": np.maximum(spot - strikes, 0) + 2.5,
        "ask": np.maximum(spot - strikes, 0) + 3.5,
        "impliedVolatility": 0.25,          # decimal, as yfinance returns
        "volume": 1000,
        "openInterest": 5000,
        "changeinOpenInterest": 120,
    })
    puts = pd.DataFrame({
        "strike": strikes,
        "lastPrice": np.maximum(strikes - spot, 0) + 3.0,
        "bid": np.maximum(strikes - spot, 0) + 2.5,
        "ask": np.maximum(strikes - spot, 0) + 3.5,
        "impliedVolatility": 0.27,
        "volume": 900,
        "openInterest": 4000,
        "changeinOpenInterest": -80,
    })
    return {"expiries": ["2026-10-30"], "expiry": "2026-10-30",
            "calls": calls, "puts": puts, "spot": spot}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(data, "get_options", lambda symbol, expiry=None: _mock_chain())
    return TestClient(app)


def test_options_available_shape(client):
    r = client.get("/api/options/RELIANCE.NS")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert body["spot"] == 100.0
    assert body["expiries"] == ["2026-10-30"]
    stats = body["stats"]
    assert stats["callOI"] > 0 and stats["putOI"] > 0
    assert stats["pcr"] == round(stats["putOI"] / stats["callOI"], 2)


def test_options_iv_scaled_to_percent(client):
    body = client.get("/api/options/RELIANCE.NS").json()
    row = next(r for r in body["chain"] if r["call"])
    # 0.25 decimal -> 25.0 percent
    assert row["call"]["iv"] == 25.0


def test_options_chain_has_oi_change(client):
    body = client.get("/api/options/RELIANCE.NS").json()
    for row in body["chain"]:
        if row["call"]:
            assert row["call"]["oiChange"] == 120
        if row["put"]:
            assert row["put"]["oiChange"] == -80


def test_options_marks_atm(client):
    body = client.get("/api/options/RELIANCE.NS").json()
    atm_rows = [r for r in body["chain"] if r["atm"]]
    assert len(atm_rows) == 1
    assert atm_rows[0]["strike"] == 100.0


def test_options_max_pain_present(client):
    stats = client.get("/api/options/RELIANCE.NS").json()["stats"]
    assert stats["maxPain"] is not None
    assert 80 <= stats["maxPain"] <= 120


def test_options_unavailable_returns_flag(client, monkeypatch):
    monkeypatch.setattr(data, "get_options", lambda symbol, expiry=None: None)
    body = client.get("/api/options/NOPE").json()
    assert body["available"] is False
    assert body["chain"] == []


def test_payoff_endpoint(client):
    r = client.get("/api/payoff/RELIANCE.NS", params={"strategy": "STRADDLE"})
    assert r.status_code == 200
    body = r.json()
    assert body["strategy"] == "STRADDLE"
    assert len(body["legs"]) == 2
    assert len(body["spots"]) == 121
    assert body["netPremium"] > 0
    assert body["breakevens"]
    assert {s["id"] for s in body["strategies"]} >= {"STRADDLE", "IRONCONDOR"}


def test_payoff_rejects_unknown_strategy(client):
    r = client.get("/api/payoff/RELIANCE.NS", params={"strategy": "BUTTERFLY"})
    assert r.status_code == 422  # blocked by the Query pattern


def test_universes_endpoint(client):
    body = client.get("/api/universes").json()
    assert body["default"]
    ids = {u["id"] for u in body["universes"]}
    assert "nifty50" in ids
    assert all(u["count"] > 0 for u in body["universes"])


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"
