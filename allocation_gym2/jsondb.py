"""Load the EPS dataset written by allocation-engine-2.0.

Read-only. This package never writes the dataset — allocation-engine-2.0 owns
the write path (`app/earnings_writer.py`) and exports the JSON this reads.

Dataset shape:

    {
      "generated": "YYYY-MM-DD",
      "tickers":   ["NVDA", ...],
      "eps": [
        {"ticker", "earnings_date", "eps_estimate", "eps_actual", "status"}
      ]
    }

`status` is "reported" (has an actual) or "upcoming" (estimate only).
"""

from __future__ import annotations

import json
import os

DEFAULT_PATH = os.getenv("EPS_DATASET", "data/eps.json")

REQUIRED_RECORD_KEYS = {"ticker", "earnings_date", "eps_estimate",
                        "eps_actual", "status"}


class DatasetError(ValueError):
    """The file loaded but is not a valid EPS dataset."""


def load(path: str | None = None) -> dict:
    """Read and validate the dataset.

    Args:
        path: dataset file; defaults to $EPS_DATASET or data/eps.json.

    Returns:
        The parsed dataset dict.

    Raises:
        FileNotFoundError: if the file is missing.
        DatasetError: if the shape is wrong.
    """
    path = path or DEFAULT_PATH
    with open(path) as f:
        data = json.load(f)

    if not isinstance(data, dict) or "eps" not in data:
        raise DatasetError(f"{path}: expected an object with an 'eps' key")
    if not isinstance(data["eps"], list):
        raise DatasetError(f"{path}: 'eps' must be a list")

    # Check the first record only — the writer emits uniform rows, and
    # validating 600 of them on every read buys nothing.
    if data["eps"]:
        missing = REQUIRED_RECORD_KEYS - set(data["eps"][0])
        if missing:
            raise DatasetError(f"{path}: records missing keys {sorted(missing)}")

    return data


def records(path: str | None = None) -> list[dict]:
    """Just the EPS records.

    Args:
        path: dataset file; defaults to $EPS_DATASET or data/eps.json.

    Returns:
        The record list.
    """
    return load(path)["eps"]
