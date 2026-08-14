"""CLI: inspect the EPS dataset."""

from __future__ import annotations

import argparse
import json

from allocation_gym2 import grid, jsondb, reader


def main() -> None:
    p = argparse.ArgumentParser(prog="allocation-gym-2", description=__doc__)
    p.add_argument("command", choices=["tickers", "historical", "upcoming", "next", "grid"])
    p.add_argument("--ticker", default=None)
    p.add_argument("--path", default=None, help="dataset path (default $EPS_DATASET)")
    p.add_argument("--out", default="eps-grid.html", help="grid output file")
    args = p.parse_args()

    if args.command == "grid":
        # Self-contained page — opens off disk, no server needed.
        print(grid.write(jsondb.load(args.path), args.out))
        return

    rows = jsondb.records(args.path)

    if args.command == "tickers":
        print(json.dumps(reader.tickers(rows), indent=2))
    elif args.command == "historical":
        print(json.dumps(reader.historical(rows, args.ticker), indent=2))
    elif args.command == "upcoming":
        print(json.dumps(reader.upcoming(rows, args.ticker), indent=2))
    else:
        print(json.dumps(reader.next_report(rows), indent=2))


if __name__ == "__main__":
    main()
