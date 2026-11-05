#!/usr/bin/env python3
"""Verifica Query 1 comparando ./output/results.txt contra expected_query1.txt."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "output" / "results.txt"
EXPECTED = HERE / "expected_query1.txt"
QUERY_HEADER = "=== Query 1 "


def extract_query1(text: str) -> list[str]:
    out, capture = [], False
    for line in text.splitlines():
        if line.startswith(QUERY_HEADER):
            capture = True
            continue
        if line.startswith("=== Query "):
            capture = False
            continue
        if capture and line.strip():
            out.append(line.strip())
    return out


def main() -> int:
    if not RESULTS.exists():
        print(f"Falta {RESULTS} — ¿el cliente terminó bien?", file=sys.stderr)
        return 1
    actual = extract_query1(RESULTS.read_text(encoding="utf-8"))
    expected = [
        ln.strip()
        for ln in EXPECTED.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    if actual != expected:
        print("Query 1 MISMATCH", file=sys.stderr)
        print(f"  Expected ({len(expected)}):", file=sys.stderr)
        for ln in expected:
            print(f"    {ln}", file=sys.stderr)
        print(f"  Actual ({len(actual)}):", file=sys.stderr)
        for ln in actual:
            print(f"    {ln}", file=sys.stderr)
        return 1
    print(f"OK: Query 1 = {len(actual)} filas")
    return 0


if __name__ == "__main__":
    sys.exit(main())