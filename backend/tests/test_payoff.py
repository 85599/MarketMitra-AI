"""Option payoff builder: legs, net premium, breakevens and P/L bounds."""
import numpy as np
import pandas as pd
import pytest

from app import payoff


def _chain(strikes, call_px, put_px):
    c = pd.DataFrame({"strike": strikes, "lastPrice": call_px})
    p = pd.DataFrame({"strike": strikes, "lastPrice": put_px})
    return c, p


@pytest.fixture
def chain():
    # Wide enough ladder that every strategy's wing offsets land on distinct strikes.
    strikes = [80, 85, 90, 95, 100, 105, 110, 115, 120]
    call_px = [22.0, 18.0, 13.0, 8.0, 5.0, 3.0, 2.0, 1.2, 0.8]
    put_px = [0.8, 1.2, 2.0, 3.0, 5.0, 8.0, 13.0, 18.0, 22.0]
    return _chain(strikes, call_px, put_px)


def test_sorted_strikes_dedupes(chain):
    c, p = chain
    assert payoff._sorted_strikes(c, p) == [80, 85, 90, 95, 100, 105, 110, 115, 120]


def test_atm_selection(chain):
    c, p = chain
    strikes = payoff._sorted_strikes(c, p)
    atm, step = payoff._atm_and_step(strikes, 101)
    assert atm == 100
    assert step == 5


def test_nth_walks_the_strike_ladder(chain):
    c, p = chain
    strikes = payoff._sorted_strikes(c, p)
    assert payoff._nth(strikes, 100, 2) == 110
    assert payoff._nth(strikes, 100, -2) == 90


def test_straddle_breakevens_straddle_around_atm(chain):
    c, p = chain
    res = payoff.analyze("STRADDLE", c, p, 100)
    # ATM call 5 + put 5 = 10 debit -> breakevens 90 and 110.
    assert res["netPremium"] == 10.0
    assert res["breakevens"] == [90.0, 110.0]
    assert res["maxLoss"] == -10.0
    assert res["maxProfit"] > 0


def test_bull_call_spread_is_debit_with_capped_pl(chain):
    c, p = chain
    res = payoff.analyze("BULL_CALL", c, p, 100)
    assert res["netPremium"] > 0            # net debit
    assert res["maxProfit"] > 0
    assert res["maxLoss"] == -res["netPremium"]
    assert len(res["legs"]) == 2
    assert {x["side"] for x in res["legs"]} == {"long", "short"}


def test_iron_condor_is_net_credit(chain):
    c, p = chain
    res = payoff.analyze("IRONCONDOR", c, p, 100)
    assert res["netPremium"] < 0            # net credit received
    assert res["maxProfit"] == -res["netPremium"]
    assert len(res["legs"]) == 4


def test_payoff_symmetry_for_straddle(chain):
    c, p = chain
    res = payoff.analyze("STRADDLE", c, p, 100)
    spots = np.array(res["spots"])
    pay = np.array(res["payoff"])
    left = pay[spots < 100]
    right = pay[spots > 100]
    assert left.max() > 0 and right.max() > 0   # profits on both wings


def test_leg_payoff_long_call():
    leg = {"type": "call", "strike": 100, "premium": 5, "side": "long"}
    pay = payoff.leg_payoff(leg, np.array([90, 100, 110]))
    assert list(pay) == [-5.0, -5.0, 5.0]


def test_leg_payoff_short_put():
    leg = {"type": "put", "strike": 100, "premium": 4, "side": "short"}
    pay = payoff.leg_payoff(leg, np.array([90, 100, 110]))
    assert list(pay) == [-6.0, 4.0, 4.0]


def test_net_premium_sign():
    legs = [{"premium": 5, "side": "long"}, {"premium": 2, "side": "short"}]
    assert payoff.net_premium(legs) == 3.0


def test_unknown_strategy_raises(chain):
    c, p = chain
    with pytest.raises(ValueError):
        payoff.build_legs("BUTTERFLY", [100], 100, {}, {})


def test_analyze_without_chain_returns_error():
    res = payoff.analyze("STRADDLE", pd.DataFrame(), pd.DataFrame(), 100)
    assert "error" in res


def test_all_strategies_produce_full_output(chain):
    c, p = chain
    for strat in payoff.STRATEGIES:
        res = payoff.analyze(strat, c, p, 100)
        assert res["legs"] and len(res["spots"]) == 121
        assert res["label"] == payoff.STRATEGIES[strat]
