"""Query helpers over the EPS dataset. Read-only, no I/O of its own.

Every function takes the record list so it stays testable without a file.
"""

from __future__ import annotations


def tickers(records: list[dict]) -> list[str]:
    """Distinct tickers present, sorted.

    Args:
        records: EPS records.

    Returns:
        Sorted ticker symbols.
    """
    return sorted({r["ticker"] for r in records})


def for_ticker(records: list[dict], ticker: str) -> list[dict]:
    """All quarters for one ticker, oldest first.

    Args:
        records: EPS records.
        ticker: symbol to filter on.

    Returns:
        Matching records sorted by date.
    """
    rows = [r for r in records if r["ticker"] == ticker]
    return sorted(rows, key=lambda r: r["earnings_date"])


def historical(records: list[dict], ticker: str | None = None) -> list[dict]:
    """Quarters that have been reported.

    Args:
        records: EPS records.
        ticker: restrict to one symbol, or None for all.

    Returns:
        Reported records sorted by ticker then date.
    """
    rows = [r for r in records if r["status"] == "reported"]
    if ticker:
        rows = [r for r in rows if r["ticker"] == ticker]
    return sorted(rows, key=lambda r: (r["ticker"], r["earnings_date"]))


def upcoming(records: list[dict], ticker: str | None = None) -> list[dict]:
    """Quarters with a consensus estimate but no actual yet.

    Args:
        records: EPS records.
        ticker: restrict to one symbol, or None for all.

    Returns:
        Upcoming records sorted by date then ticker.
    """
    rows = [r for r in records if r["status"] == "upcoming"]
    if ticker:
        rows = [r for r in rows if r["ticker"] == ticker]
    return sorted(rows, key=lambda r: (r["earnings_date"], r["ticker"]))


def next_report(records: list[dict]) -> dict[str, dict]:
    """Each ticker's soonest upcoming quarter.

    Args:
        records: EPS records.

    Returns:
        ticker -> that ticker's next record, for tickers that have one.
    """
    out: dict[str, dict] = {}
    for record in upcoming(records):
        out.setdefault(record["ticker"], record)
    return out


def latest_reported(records: list[dict]) -> dict[str, dict]:
    """Each ticker's most recent reported quarter.

    Args:
        records: EPS records.

    Returns:
        ticker -> that ticker's newest reported record.
    """
    out: dict[str, dict] = {}
    for record in historical(records):
        out[record["ticker"]] = record   # sorted ascending, so last wins
    return out
