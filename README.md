# allocation-gym-2.0

Thin analytics client. Computes cohort analytics — earnings calendars, EPS
estimate-vs-actual, surprise statistics — and emits a flat record payload for
a storage service to persist.

Deliberately holds **no storage of its own**. The counterpart writer client and
SQLite storage interface live in
[`allocation-engine-2.0`](https://github.com/IamJasonBian/allocation-engine-2.0)
(`app/earnings_store.py`, `app/earnings_writer.py`). This package computes; that
one persists. The contract between them is the JSON payload documented in
`allocation_gym2/client.py` — no shared database handle, no import across repos.

## Install

```bash
pip install -e ".[data,dev]"
```

`yfinance` is an optional `data` extra, lazily imported, so the pure analytics
(`surprise`) can be imported and tested without a network stack.

## Usage

```bash
# Full payload — cohort + calendar + EPS history + surprise stats
python -m allocation_gym2 collect --out payload.json

# Just the surprise table, to stdout
python -m allocation_gym2 surprise

# Narrow to one subsector
python -m allocation_gym2 collect --subsector silicon --out silicon.json
```

Then hand the payload to the engine's writer:

```bash
python scripts/load_earnings.py payload.json   # in allocation-engine-2.0
```

## Why surprise stats are median-based

`surprise_pct` is a ratio against consensus, so it detonates when consensus is
near zero — a $0.01 estimate printing $0.02 reads as +100%, and Cloudflare's
best quarter reads **+1829%**. Averaging those produces a number driven entirely
by the smallest denominators.

`surprise_stats()` therefore reports median surprise %, median dollar delta, and
a raw beat rate, and flags `pct_unstable` for any ticker whose typical consensus
is under $0.25 — below that, a one-cent miss moves the percentage by double
digits and the % column should be read as noise regardless of the median.

## Layout

| Module | Holds |
|---|---|
| `cohort.py` | cohort membership, subsector, market cap — reference data |
| `calendar.py` | next scheduled report per ticker, with source provenance |
| `eps.py` | EPS estimate/actual fetch (yfinance) |
| `surprise.py` | pure surprise math — no I/O, fully unit-tested |
| `client.py` | assembles the payload; the repo's only public entry point |
