# allocation-gym-2.0

Implementation - https://iamjasonbian.github.io/chasethedice/papers/allocation-gym-whitepaper/

Read-only client over the EPS dataset. Loads the JSON db that
[`allocation-engine-2.0`](https://github.com/IamJasonBian/allocation-engine-2.0)
writes, answers questions about it, and renders it.

**This package never writes.** The engine owns the write path — it fetches EPS
values and exports the dataset (`app/earnings_writer.py`, `app/earnings_store.py`).
This one reads.

## Install

```bash
pip install -e ".[dev]"
```

No data dependencies — nothing here fetches.

## Usage

```bash
export EPS_DATASET=../allocation-engine-2.0/data/eps.json

python -m allocation_gym2 tickers
python -m allocation_gym2 historical --ticker AVGO
python -m allocation_gym2 upcoming
python -m allocation_gym2 next

# self-contained page — open it straight off disk, no server
python -m allocation_gym2 grid --out eps-grid.html
```

```python
from allocation_gym2 import records, historical, next_report

rows = records()                      # $EPS_DATASET, or pass a path
historical(rows, "NVDA")              # reported quarters, oldest first
next_report(rows)["AVGO"]             # soonest upcoming quarter + consensus
```

## Dataset shape

```json
{
  "generated": "2026-08-13",
  "tickers": ["AVGO", "NVDA"],
  "eps": [
    {"ticker": "NVDA", "earnings_date": "2026-05-20",
     "eps_estimate": 1.77, "eps_actual": 1.87, "status": "reported"},
    {"ticker": "NVDA", "earnings_date": "2026-08-26",
     "eps_estimate": 2.08, "eps_actual": null, "status": "upcoming"}
  ]
}
```

`status` is `reported` (has an actual) or `upcoming` (consensus only) — so
current and historical live in the same table.

Values are split-adjusted at the source, so older quarters won't match headlines
from the time.

## Layout

| Module | Holds |
|---|---|
| `jsondb.py` | load + validate the dataset |
| `reader.py` | queries — by ticker, historical, upcoming, next, latest |
| `grid.py` | render the dataset as a self-contained HTML grid |

The grid inlines its data rather than fetching it, so it opens under `file://`.
Rendering lives here rather than in the engine — a plot is a read.
