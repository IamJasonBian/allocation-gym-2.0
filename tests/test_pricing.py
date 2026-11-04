"""Pricing port from `.context/bars/pricing_service` — fixture legs only."""

from allocation_gym2 import pricing


def _leg(strike: float, bid: float, ask: float, iv: float) -> dict:
    return {"strike": strike, "bid": bid, "ask": ask, "impliedVolatility": iv}


def test_bs_call_atm_positive():
    v = pricing.bs_call(100, 100, 30 / 365, pricing.RATE, 0.25)
    assert 3 < v < 6


def test_spread_marks_and_theoretical():
    leg_l = _leg(500, 15.0, 16.0, 1.0)
    leg_s = _leg(530, 6.0, 7.0, 0.95)
    mid, natural = pricing.spread_marks(leg_l, leg_s)
    assert mid == 9.0
    assert natural == 8.0
    theo = pricing.spread_value(505, 2 / 365, leg_l, leg_s)
    assert theo > 0


def test_spread_value_ivs_matches_leg_form():
    T = 2 / 365
    S = 505.0
    iv_l, iv_s = 1.1168, 1.0508
    a = pricing.spread_value_ivs(S, T, 500, 530, iv_l, iv_s)
    b = pricing.spread_value(
        S,
        T,
        _leg(500, 0, 0, iv_l),
        _leg(530, 0, 0, iv_s),
    )
    assert abs(a - b) < 1e-9


def test_stop_solver_finds_spot_below_current():
    leg_l = _leg(500, 15, 16, 1.0)
    leg_s = _leg(530, 6, 7, 0.95)
    spot = 505.0
    T = 2 / 365
    mid, _ = pricing.spread_marks(leg_l, leg_s)
    stop_val = mid / 2
    s_stop = pricing.solve_underlying_for_value(stop_val, T, leg_l, leg_s, spot)
    assert s_stop is not None
    assert s_stop < spot
    assert abs(pricing.spread_value(s_stop, T, leg_l, leg_s) - stop_val) < 0.05


def test_quote_payload_shape():
    leg_l = _leg(500, 15, 16, 1.1168)
    leg_s = _leg(530, 6, 7, 1.0508)
    body = pricing.quote_debit_call_spread(
        symbol="AMD",
        spot=505.69,
        expiry="2026-11-06",
        dte=2.0,
        k_long=500,
        k_short=530,
        leg_l=leg_l,
        leg_s=leg_s,
        T=2 / 365,
    )
    assert body["mid"] == 9.0
    assert body["stop_value_50pct"] == 4.5
    assert "bs_theoretical" in body
    assert body["model"].startswith("Black-Scholes")
