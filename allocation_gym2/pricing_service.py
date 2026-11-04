#!/usr/bin/env python3
"""Local option pricing HTTP service (Yahoo-backed).

Same endpoints as `.context/bars/pricing_service.py`; core math lives in
`allocation_gym2.pricing`.

    GET /spot?symbol=AMD
    GET /spread?symbol=AMD&expiry=2026-11-06&long=500&short=530
    GET /health
"""

from __future__ import annotations

import json
import subprocess
import time
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

from allocation_gym2.pricing import RATE, quote_debit_call_spread

PORT = 8791
SPOT_TTL = 15
CHAIN_TTL = 30
COOKIE_JAR = "/tmp/yck.txt"

_crumb: str | None = None
_cache: dict = {}


def _curl(url: str, use_auth: bool = False) -> str:
    cmd = ["curl", "-s", "-H", "User-Agent: Mozilla/5.0"]
    if use_auth:
        cmd += ["-b", COOKIE_JAR]
    cmd.append(url)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout


def _get_crumb() -> str:
    global _crumb
    if _crumb:
        return _crumb
    subprocess.run(
        [
            "curl",
            "-s",
            "-c",
            COOKIE_JAR,
            "-H",
            "User-Agent: Mozilla/5.0",
            "https://fc.yahoo.com",
            "-o",
            "/dev/null",
        ],
        timeout=30,
        check=False,
    )
    _crumb = _curl("https://query1.finance.yahoo.com/v1/test/getcrumb", use_auth=True).strip()
    return _crumb


def _cached(key: str, ttl: int, fn):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    val = fn()
    _cache[key] = (time.time(), val)
    return val


def get_spot(symbol: str) -> dict:
    def fn():
        raw = _curl(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
        )
        meta = json.loads(raw)["chart"]["result"][0]["meta"]
        return {
            "symbol": symbol,
            "spot": meta["regularMarketPrice"],
            "ts": datetime.now(timezone.utc).isoformat(),
        }

    return _cached(f"spot:{symbol}", SPOT_TTL, fn)


def get_chain(symbol: str, expiry: str) -> dict[float, dict]:
    exp_unix = int(datetime.fromisoformat(expiry).replace(tzinfo=timezone.utc).timestamp())

    def fn():
        url = (
            f"https://query1.finance.yahoo.com/v7/finance/options/{symbol}"
            f"?date={exp_unix}&crumb={urllib.parse.quote(_get_crumb())}"
        )
        raw = _curl(url, use_auth=True)
        calls = json.loads(raw)["optionChain"]["result"][0]["options"][0]["calls"]
        return {c["strike"]: c for c in calls}

    return _cached(f"chain:{symbol}:{exp_unix}", CHAIN_TTL, fn)


def get_spread(symbol: str, expiry: str, kl: float, ks: float) -> dict:
    spot = get_spot(symbol)["spot"]
    chain = get_chain(symbol, expiry)
    leg_l, leg_s = chain[float(kl)], chain[float(ks)]
    exp_unix = int(datetime.fromisoformat(expiry).replace(tzinfo=timezone.utc).timestamp())
    T = max((exp_unix - time.time()) / (365.25 * 86400), 1e-6)
    dte = round(T * 365.25, 1)
    return quote_debit_call_spread(
        symbol=symbol,
        spot=spot,
        expiry=expiry,
        dte=dte,
        k_long=kl,
        k_short=ks,
        leg_l=leg_l,
        leg_s=leg_s,
        T=T,
        stop_fraction=0.5,
    )


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        try:
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            if u.path == "/health":
                body = {"ok": True, "rate": RATE}
            elif u.path == "/spot":
                body = get_spot(q["symbol"][0])
            elif u.path == "/spread":
                body = get_spread(
                    q["symbol"][0],
                    q["expiry"][0],
                    float(q["long"][0]),
                    float(q["short"][0]),
                )
            else:
                self.send_error(404, "unknown endpoint")
                return
            data = json.dumps(body, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:  # noqa: BLE001 — one bad request must not kill the server
            self.send_error(500, str(e))

    def log_message(self, fmt: str, *args) -> None:
        pass


def main() -> None:
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
