# allocation-gym — approach & PR

Typeset page (Computer Modern + KaTeX): **[whitepaper.html](whitepaper.html)**

**Status:** gym PR [#1](https://github.com/IamJasonBian/allocation-gym-2.0/pull/1) · engine write [#113](https://github.com/IamJasonBian/allocation-engine-2.0/pull/113) · vol surface [#117](https://github.com/IamJasonBian/allocation-engine-2.0/pull/117)

## Core Types

As defined in the repos — auth box value objects (`auth-service/models.py`),
endpoint return dicts, broker schemas (`app/schemas.py`), and the live snapshot
envelope (`app/api/snapshot.py`).

### Auth box — `models.py`

```python
@dataclass(frozen=True, slots=True)
class Credentials:
    username: str
    password: str
    totp_secret: str | None = None
    device_token: str | None = None

@dataclass(frozen=True, slots=True)
class Session:
    access_token: str
    refresh_token: str
    token_type: str
    expires_at: float
    device_token: str
    account_url: str = ""
    account_number: str = ""

    def headers(self) -> dict: ...
    def with_account(self, account_url: str, account_number: str) -> Session: ...

@dataclass(frozen=True, slots=True)
class AuthResult:
    status: str                   # OK | NEEDS_APPROVAL | MFA_REQUIRED | TIMEOUT | ERROR
    session: Session | None = None
    approval_id: str | None = None
    error_code: str | None = None
    detail: str = ""
```

### Auth box — endpoint shapes

```python
# session.status  →  GET /auth/status
{
    "profile": str,
    "authenticated": bool,
    "token_unexpired": bool,
    "token_verified": bool | None,
    "verify_interval": int,
    "expires_at": float | None,
    "account_number": str | None,
}

# _handle_token  →  GET /token
{
    "token": str,
    "token_type": str,
    "expires_at": float,
    "device_token": str,
    "account_number": str,
}

# GET /orders/trailing_stop
{"count": int, "orders": list[dict]}

# build_trailing_stop_payload  →  POST place / replace body["payload"]
{
    "account": str,
    "instrument": str,
    "symbol": str,
    "type": "market",
    "time_in_force": "gtc",
    "trigger": "stop",
    "side": str,
    "quantity": str,
    "trailing_peg": {"type": "percentage", "percentage": str},
    "ref_id": str,
    # "stop_price": str   optional
}
```

### Broker schemas — `app/schemas.py`

```python
class PositionSchema(BaseModel):
    symbol: str
    qty: float
    side: str                     # 'long' | 'short'
    market_value: float
    avg_entry: float
    unrealized_pl: float
    unrealized_pl_pct: float

class OrderSchema(BaseModel):
    id: str
    symbol: str
    side: str                     # 'BUY' | 'SELL'
    qty: float
    type: str                     # 'market' | 'limit' | 'stop' | 'stop_limit'
    limit_price: float | None = None
    stop_price: float | None = None
    status: str

class AccountSchema(BaseModel):
    equity: float
    cash: float
    buying_power: float
    portfolio_value: float
```

### Snapshot — `GET /api/snapshot`

```python
{
    "timestamp": str,
    "order_book": [
        {
            "order_id": str,
            "symbol": str,
            "side": str,
            "order_type": str,
            "trigger": "immediate",
            "state": str,
            "quantity": float,
            "limit_price": float,
            "stop_price": float | None,
            "created_at": str,
            "updated_at": str,
        },
        ...
    ],
    "portfolio": {
        "cash": {
            "cash": float,
            "cash_available_for_withdrawal": float,
            "buying_power": float,
            "tradeable_cash": float,
        },
        "equity": float,
        "market_value": float,
        "positions": [
            {
                "symbol": str,
                "name": str,
                "quantity": float,
                "avg_buy_price": float,
                "current_price": float,
                "equity": float,
                "profit_loss": float,
                "profit_loss_pct": float,
                "percent_change": None,
                "percentage": None,
                "asset_type": str,
            },
            ...
        ],
        "open_orders": [...],
        "open_option_orders": [...],
        "options": [...],
    },
    "market_data": None,
}
```

Broker `qty` / `avg_entry` map into snapshot `quantity` / `avg_buy_price`. Vol
below uses snapshot `quantity` as $q$.

## Vol

### Book slice

Per-symbol vol from `VolSlicer` / `VolSlice`, over daily closes. Let $c_t$ be
the close and $q$ the signed position.

| SYMBOL | POSITION | GR | DOWNSIDE GR | DAILY STDEV | DOWNSIDE STDEV | LATEST DAY (Z) | 1-STDEV MOVE (USD) | 30D | 60D Z-PATH |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| NBIS | 89.01 | +0.725% | −4.528% | 7.50% | 4.10% | z −0.16 | 1,463 | −0.24% | |
| BTC | 498.156016 | −0.126% | −2.191% | 2.84% | 2.06% | z +2.16 | 483 | +20.55% | |
| MSFT | 34.449544 | +0.001% | −1.358% | 2.04% | 1.33% | z +0.21 | 339 | +25.48% | |
| AVGO | 33.729031 | +0.136% | −2.163% | 3.04% | 2.06% | z +0.35 | 378 | −7.88% | |
| QQQ | 16.545245 | +0.096% | −0.948% | 1.23% | 0.84% | z +0.21 | 146 | −1.66% | |
| MA | 19.164231 | −0.003% | −1.054% | 1.41% | 1.00% | z +0.84 | 156 | +10.23% | |
| SPY | 13.575022 | +0.072% | −0.605% | 0.81% | 0.56% | z +0.42 | 84 | +1.43% | |
| VOO | 13.681061 | +0.072% | −0.609% | 0.81% | 0.55% | z +0.39 | 78 | +1.42% | |

*Source: allocation-engine risk desk · daily mark-to-market vol.*

### Calculation logic

$$
g_t = \frac{c_t}{c_{t-1}} - 1
$$

- **POSITION** — signed $q$; notional uses $|q|\,c_T$.
- **GR** — $\bar g = \frac{1}{n}\sum g_t$.
- **DOWNSIDE GR** — mean of $\{g_t : g_t < 0\}$, else $0$.
- **DAILY STDEV** — sample $\sigma_g$.
- **DOWNSIDE STDEV** — $\sqrt{\frac{1}{n}\sum(\min(g_t,0))^2}$.
- **LATEST DAY (Z)** — $z_T = (g_T - \bar g)/\sigma_g$ (or $0$ if $\sigma_g = 0$).
- **1-STDEV MOVE** — $|q|\cdot c_T\cdot\sigma_g$.
- **30D** — $c_T/c_{T-W}-1$.
- **60D Z-PATH** — $(z_t)_{t\in W}$ where $z_t = (g_t - \bar g_W)/\sigma_{g,W}$. Sequence, not a scalar; empty when not exported.

## Write / read boundary

| Side | Repo | Owns |
|---|---|---|
| Write | `allocation-engine-2.0` | fetch → classify → store → export |
| Read | `allocation-gym-2.0` | load → query → render |

Zero runtime dependencies on the gym side. PR #1 shipped `jsondb`, `reader`,
CLI, and the self-contained local grid.
