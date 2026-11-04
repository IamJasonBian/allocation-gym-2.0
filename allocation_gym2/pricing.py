"""Black–Scholes call-spread pricing (ported from `.context/bars/pricing_service`).

Per-leg Yahoo IV, flat r=4%, q=0. Pure functions only — no network.
"""

from __future__ import annotations

import math
from typing import Any

RATE = 0.04


def bs_call(S: float, K: float, T: float, r: float, sig: float) -> float:
    """Black-Scholes-Merton European call (q=0)."""
    if T <= 1e-9:
        return max(S - K, 0.0)
    d1 = (math.log(S / K) + (r + sig * sig / 2) * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    n = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
    return S * n(d1) - K * math.exp(-r * T) * n(d2)


def spread_value(S: float, T: float, leg_l: dict[str, Any], leg_s: dict[str, Any]) -> float:
    """Long-call spread value from two chain legs (each has strike + impliedVolatility)."""
    return bs_call(S, leg_l["strike"], T, RATE, leg_l["impliedVolatility"]) - bs_call(
        S, leg_s["strike"], T, RATE, leg_s["impliedVolatility"]
    )


def spread_value_ivs(
    S: float,
    T: float,
    k_long: float,
    k_short: float,
    iv_long: float,
    iv_short: float,
    r: float = RATE,
) -> float:
    """Spread value from strikes and vols (scenario tables)."""
    return bs_call(S, k_long, T, r, iv_long) - bs_call(S, k_short, T, r, iv_short)


def spread_marks(leg_l: dict[str, Any], leg_s: dict[str, Any]) -> tuple[float, float]:
    """Mid and natural (bid long − ask short) for a debit call spread."""
    mid_l = (leg_l["bid"] + leg_l["ask"]) / 2
    mid_s = (leg_s["bid"] + leg_s["ask"]) / 2
    mid = round(mid_l - mid_s, 2)
    natural = round(leg_l["bid"] - leg_s["ask"], 2)
    return mid, natural


def solve_underlying_for_value(
    target: float,
    T: float,
    leg_l: dict[str, Any],
    leg_s: dict[str, Any],
    s_hi: float,
) -> float | None:
    """Bisection: spot where BS spread value == target (searches below s_hi)."""
    lo, hi = 0.5 * s_hi, s_hi
    if spread_value(lo, T, leg_l, leg_s) > target:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        if spread_value(mid, T, leg_l, leg_s) < target:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 2)


def quote_debit_call_spread(
    *,
    symbol: str,
    spot: float,
    expiry: str,
    dte: float,
    k_long: float,
    k_short: float,
    leg_l: dict[str, Any],
    leg_s: dict[str, Any],
    T: float,
    stop_fraction: float = 0.5,
) -> dict[str, Any]:
    """Build the `/spread` JSON body from spot + cached chain legs."""
    mid, natural = spread_marks(leg_l, leg_s)
    theo = round(spread_value(spot, T, leg_l, leg_s), 2)
    stop_value = round(mid * stop_fraction, 2)
    stop_under = solve_underlying_for_value(stop_value, T, leg_l, leg_s, spot)
    return {
        "symbol": symbol,
        "spot": spot,
        "expiry": expiry,
        "dte": dte,
        "long": k_long,
        "short": k_short,
        "legs": {
            str(k_long): {
                "bid": leg_l["bid"],
                "ask": leg_l["ask"],
                "iv": round(leg_l["impliedVolatility"], 4),
            },
            str(k_short): {
                "bid": leg_s["bid"],
                "ask": leg_s["ask"],
                "iv": round(leg_s["impliedVolatility"], 4),
            },
        },
        "mid": mid,
        "natural_close": natural,
        "bs_theoretical": theo,
        "model": "Black-Scholes-Merton, per-leg IV, r=4%, q=0",
        "stop_value_50pct": stop_value,
        "stop_underlying_approx": stop_under,
    }


__all__ = [
    "RATE",
    "bs_call",
    "quote_debit_call_spread",
    "solve_underlying_for_value",
    "spread_marks",
    "spread_value",
    "spread_value_ivs",
]
