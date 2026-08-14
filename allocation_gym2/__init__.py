"""allocation-gym-2.0 — read-only client over the EPS dataset."""

from allocation_gym2.jsondb import DatasetError, load, records
from allocation_gym2.reader import (
    for_ticker,
    historical,
    latest_reported,
    next_report,
    tickers,
    upcoming,
)

__version__ = "0.1.0"

__all__ = [
    "DatasetError",
    "for_ticker",
    "historical",
    "latest_reported",
    "load",
    "next_report",
    "records",
    "tickers",
    "upcoming",
]
