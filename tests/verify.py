#!/usr/bin/env python3
"""Compara los resultados de un test_queryN contra su archivo expected."""
import re
import sys
from pathlib import Path


def extract_query(text: str, query_id: int) -> list[str]:
    header = f"=== Query {query_id} "
    output: list[str] = []
    capture = False
    for line in text.splitlines():
        if line.startswith(header):
            capture = True
            continue
        if line.startswith("=== Query "):
            capture = False
            continue
        if capture and line.strip():
            output.append(line.strip())
    return output


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Uso: {Path(sys.argv[0]).name} <directorio-del-test>", file=sys.stderr)
        return 2

    test_dir = Path(sys.argv[1]).resolve()
    match = re.fullmatch(r"test_query([1-5])", test_dir.name)
    if not match:
        print(f"Directorio de test inválido: {test_dir.name}", file=sys.stderr)
        return 2

    query_id = int(match.group(1))
    results = test_dir / "output" / "results.txt"
    expected_file = test_dir / f"expected_query{query_id}.txt"

    if not results.exists():
        print(f"Falta {results} — ¿el cliente terminó bien?", file=sys.stderr)
        return 1
    if not expected_file.exists():
        print(f"Falta el archivo esperado {expected_file}", file=sys.stderr)
        return 1

    actual = extract_query(results.read_text(encoding="utf-8"), query_id)
    expected = [
        line.strip()
        for line in expected_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    if actual != expected:
        print(f"Query {query_id} MISMATCH", file=sys.stderr)
        print(f"  Expected ({len(expected)}):", file=sys.stderr)
        for line in expected:
            print(f"    {line}", file=sys.stderr)
        print(f"  Actual ({len(actual)}):", file=sys.stderr)
        for line in actual:
            print(f"    {line}", file=sys.stderr)
        return 1

    print(f"OK: Query {query_id} = {len(actual)} filas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
