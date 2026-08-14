"""Tests for the read path. Fixture data only — no file, no network."""

import json

import pytest

from allocation_gym2 import jsondb, reader

RECORDS = [
    {"ticker": "AVGO", "earnings_date": "2026-06-03", "eps_estimate": 2.40,
     "eps_actual": 2.44, "status": "reported"},
    {"ticker": "AVGO", "earnings_date": "2026-03-04", "eps_estimate": 2.02,
     "eps_actual": 2.05, "status": "reported"},
    {"ticker": "AVGO", "earnings_date": "2026-09-02", "eps_estimate": 3.24,
     "eps_actual": None, "status": "upcoming"},
    {"ticker": "NVDA", "earnings_date": "2026-05-20", "eps_estimate": 1.77,
     "eps_actual": 1.87, "status": "reported"},
    {"ticker": "NVDA", "earnings_date": "2026-08-26", "eps_estimate": 2.08,
     "eps_actual": None, "status": "upcoming"},
    {"ticker": "NVDA", "earnings_date": "2026-11-18", "eps_estimate": 2.55,
     "eps_actual": None, "status": "upcoming"},
]


def test_tickers_are_distinct_and_sorted():
    assert reader.tickers(RECORDS) == ["AVGO", "NVDA"]


def test_for_ticker_is_date_sorted():
    dates = [r["earnings_date"] for r in reader.for_ticker(RECORDS, "AVGO")]
    assert dates == ["2026-03-04", "2026-06-03", "2026-09-02"]


def test_historical_keeps_only_reported_quarters():
    rows = reader.historical(RECORDS)
    assert len(rows) == 3
    assert all(r["eps_actual"] is not None for r in rows)


def test_upcoming_keeps_only_quarters_without_an_actual():
    rows = reader.upcoming(RECORDS)
    assert len(rows) == 3
    assert all(r["eps_actual"] is None for r in rows)
    assert all(r["eps_estimate"] is not None for r in rows)


def test_filters_narrow_to_one_ticker():
    assert {r["ticker"] for r in reader.historical(RECORDS, "NVDA")} == {"NVDA"}
    assert {r["ticker"] for r in reader.upcoming(RECORDS, "AVGO")} == {"AVGO"}


def test_next_report_picks_the_soonest_upcoming():
    nxt = reader.next_report(RECORDS)
    assert nxt["NVDA"]["earnings_date"] == "2026-08-26"
    assert nxt["AVGO"]["earnings_date"] == "2026-09-02"


def test_latest_reported_picks_the_newest_actual():
    latest = reader.latest_reported(RECORDS)
    assert latest["AVGO"]["earnings_date"] == "2026-06-03"
    assert latest["AVGO"]["eps_actual"] == 2.44


def test_empty_records_are_handled_everywhere():
    assert reader.tickers([]) == []
    assert reader.historical([]) == []
    assert reader.next_report([]) == {}
    assert reader.latest_reported([]) == {}


# --------------------------------------------------------------------------- #
# jsondb loading + validation
# --------------------------------------------------------------------------- #

def _write(tmp_path, payload):
    path = tmp_path / "eps.json"
    path.write_text(json.dumps(payload))
    return str(path)


def test_load_reads_a_valid_dataset(tmp_path):
    path = _write(tmp_path, {"generated": "2026-08-13",
                             "tickers": ["AVGO", "NVDA"], "eps": RECORDS})
    data = jsondb.load(path)
    assert len(data["eps"]) == 6
    assert jsondb.records(path) == RECORDS


def test_load_accepts_an_empty_dataset(tmp_path):
    path = _write(tmp_path, {"generated": "2026-08-13", "tickers": [], "eps": []})
    assert jsondb.load(path)["eps"] == []


def test_load_rejects_a_missing_eps_key(tmp_path):
    path = _write(tmp_path, {"generated": "2026-08-13"})
    with pytest.raises(jsondb.DatasetError, match="'eps' key"):
        jsondb.load(path)


def test_load_rejects_eps_that_is_not_a_list(tmp_path):
    path = _write(tmp_path, {"eps": {"nope": True}})
    with pytest.raises(jsondb.DatasetError, match="must be a list"):
        jsondb.load(path)


def test_load_rejects_records_missing_required_keys(tmp_path):
    path = _write(tmp_path, {"eps": [{"ticker": "AVGO"}]})
    with pytest.raises(jsondb.DatasetError, match="missing keys"):
        jsondb.load(path)


def test_load_raises_for_a_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        jsondb.load(str(tmp_path / "nope.json"))
