#!/usr/bin/env python3
"""Validate relocated UTF-8 CSV headers and row counts; this does not execute M."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUERY = ROOT / "powerbi" / "RefreshQueries.pq"


def contracts():
    text = QUERY.read_text(encoding="utf-8")
    result = {}
    for line in text.splitlines():
        match = re.search(r'ReadCsv\("([a-z_]+)", (\{\{.*?\}\})\)', line)
        if match:
            result[match[1]] = re.findall(r'\{"([a-z_]+)",', match[2])
    if len(result) != 7:
        raise ValueError("Expected seven CSV contracts in RefreshQueries.pq")
    return result


def inspect(folder: Path):
    result = {}
    for name, columns in contracts().items():
        path = folder / f"{name}.csv"
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            actual = next(reader)
            if actual != columns:
                raise ValueError(f"{name}: expected headers {columns}, got {actual}")
            rows = 0
            for row in reader:
                if len(row) != len(columns):
                    raise ValueError(f"{name}: malformed row {rows + 2}")
                rows += 1
        result[name] = {"rows": rows, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--compare-with", type=Path, help="Require identical CSVs in a second location")
    args = parser.parse_args()
    result = inspect(args.folder)
    if args.compare_with and result != inspect(args.compare_with):
        raise ValueError("Relocated files differ from the original files")
    print(json.dumps({"scope": "CSV files only; Power Query refresh is not executed", "tables": result}, indent=2))


if __name__ == "__main__":
    main()
