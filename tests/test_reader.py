"""Tests for the read path and the grid. Fixture data only — no network."""

import json

import pytest

from allocation_gym2 import grid, jsondb, reader

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

DATASET = {"generated": "2026-08-13", "tickers": ["AVGO", "NVDA"], "eps": RECORDS}


def test_historical_and_upcoming_split_on_status():
    assert all(r["eps_actual"] is not None for r in reader.historical(RECORDS))
    assert all(r["eps_actual"] is None for r in reader.upcoming(RECORDS))
    assert len(reader.historical(RECORDS)) == 3
    assert len(reader.upcoming(RECORDS)) == 3


def test_queries_sort_and_filter():
    assert reader.tickers(RECORDS) == ["AVGO", "NVDA"]
    assert [r["earnings_date"] for r in reader.for_ticker(RECORDS, "AVGO")] == [
        "2026-03-04", "2026-06-03", "2026-09-02"]
    assert {r["ticker"] for r in reader.historical(RECORDS, "NVDA")} == {"NVDA"}


def test_next_report_and_latest_reported_pick_the_right_end():
    assert reader.next_report(RECORDS)["NVDA"]["earnings_date"] == "2026-08-26"
    assert reader.latest_reported(RECORDS)["AVGO"]["eps_actual"] == 2.44


def test_empty_records_are_handled_everywhere():
    assert reader.tickers([]) == []
    assert reader.historical([]) == []
    assert reader.next_report([]) == {}
    assert reader.latest_reported([]) == {}


def test_load_reads_a_valid_dataset(tmp_path):
    path = tmp_path / "eps.json"
    path.write_text(json.dumps(DATASET))
    assert jsondb.records(str(path)) == RECORDS


@pytest.mark.parametrize("payload,match", [
    ({"generated": "2026-08-13"}, "'eps' key"),
    ({"eps": {"nope": True}}, "must be a list"),
    ({"eps": [{"ticker": "AVGO"}]}, "missing keys"),
])
def test_load_rejects_a_malformed_dataset(tmp_path, payload, match):
    path = tmp_path / "eps.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(jsondb.DatasetError, match=match):
        jsondb.load(str(path))


def test_grid_is_self_contained_so_it_opens_off_disk():
    page = grid.render(DATASET)
    assert "__EPS_DATA__" not in page, "data placeholder was not substituted"
    assert "fetch(" not in page, "a fetch would fail under file://"
    assert "AVGO" in page and "3.24" in page


def test_grid_escapes_a_closing_script_tag_in_the_data():
    """An embedded </script> would end the block early and break the page."""
    page = grid.render({"generated": "x", "tickers": ["A"],
                        "eps": [{"ticker": "</script><b>", "earnings_date": "2026-01-01",
                                 "eps_estimate": 1.0, "eps_actual": 1.1,
                                 "status": "reported"}]})
    assert "</script><b>" not in page
    assert page.count("</script>") == 1


def test_grid_write_creates_the_file(tmp_path):
    out = grid.write(DATASET, str(tmp_path / "eps-grid.html"))
    with open(out) as f:
        assert "<!DOCTYPE html>" in f.read()
