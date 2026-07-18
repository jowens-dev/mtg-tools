#!/usr/bin/env python3
"""Tag a card inventory CSV with color identity data from a Scryfall SQLite database."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Iterable
import urllib.error
import urllib.parse
import urllib.request


def resolve_name_column(headers: Iterable[str]) -> str:
    for candidate in ["Card Name", "card_name", "Name", "name", "Product Name", "product_name", "Title"]:
        if candidate in headers:
            return candidate
    raise ValueError("No supported card-name column found in inventory CSV")


def normalize_color_identity(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            if item is None:
                continue
            letters = [letter for letter in str(item).upper() if letter in "WUBRG"]
            values.extend(letters)
        if values:
            return ",".join(dict.fromkeys(values))
        return ""
    text = str(value).strip()
    if not text:
        return ""
    letters = [letter for letter in text.upper() if letter in "WUBRG"]
    if letters:
        return ",".join(letters)
    return text


def build_color_lookup_from_api(names: Iterable[str]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    name_list = list(dict.fromkeys(name for name in names if name))

    def chunked(items: list[str], size: int) -> Iterable[list[str]]:
        for index in range(0, len(items), size):
            yield items[index:index + size]

    for batch in chunked(name_list, 75):
        payload = {"identifiers": [{"name": name} for name in batch]}
        request = urllib.request.Request(
            "https://api.scryfall.com/cards/collection",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "mtg-tools/1.0"},
        )
        attempt = 0
        while attempt < 4:
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    data = json.load(response)
                    for card in data.get("data", []):
                        if card.get("name"):
                            lookup[card["name"]] = normalize_color_identity(card.get("color_identity"))
                    break
            except urllib.error.HTTPError as error:
                if error.code in {429, 500, 502, 503, 504} and attempt < 3:
                    attempt += 1
                    time.sleep(2 * attempt)
                    continue
                break
            except Exception:
                break
        else:
            for name in batch:
                lookup[name] = ""
        if not any(name in lookup for name in batch):
            for name in batch:
                lookup[name] = ""

    return lookup


def build_color_lookup(connection: sqlite3.Connection | None, names: Iterable[str]) -> dict[str, str]:
    name_list = list(dict.fromkeys(name for name in names if name))
    lookup: dict[str, str] = {}
    if not name_list:
        return lookup

    if connection is None:
        return build_color_lookup_from_api(name_list)

    batch_size = 900
    for index in range(0, len(name_list), batch_size):
        batch = name_list[index:index + batch_size]
        placeholders = ",".join("?" for _ in batch)
        sql = f"SELECT name, color_identity FROM cards WHERE name IN ({placeholders})"
        rows = connection.execute(sql, batch).fetchall()
        for row in rows:
            lookup[row[0]] = normalize_color_identity(row[1])
    return lookup


def tag_inventory(inventory_path: str | os.PathLike[str], db_path: str | os.PathLike[str] | None, output_path: str | os.PathLike[str] | None = None) -> tuple[int, int]:
    inventory_path = Path(inventory_path)
    db_path = Path(db_path) if db_path else None
    if not inventory_path.exists():
        raise FileNotFoundError(f"Inventory CSV not found: {inventory_path}")

    with inventory_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Inventory CSV is empty")
        name_column = resolve_name_column(reader.fieldnames)
        rows = list(reader)

    names = [row.get(name_column, "") for row in rows]

    connection = sqlite3.connect(str(db_path)) if db_path and db_path.exists() else None
    try:
        color_lookup = build_color_lookup(connection, names)
    finally:
        if connection is not None:
            connection.close()

    output_path = Path(output_path) if output_path else inventory_path.with_name(f"{inventory_path.stem}_tagged.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = None
        for row in rows:
            row_copy = dict(row)
            row_copy["Color Identity"] = color_lookup.get(row.get(name_column, ""), "")
            if writer is None:
                writer = csv.DictWriter(handle, fieldnames=list(row_copy.keys()))
                writer.writeheader()
            writer.writerow(row_copy)

    matched = sum(1 for value in color_lookup.values() if value)
    missing = len(rows) - matched
    return len(rows), missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory_csv", help="Path to the canonical inventory CSV")
    parser.add_argument("scryfall_db", nargs="?", help="Optional path to a local Scryfall SQLite database")
    parser.add_argument("--output", help="Optional output CSV path")
    args = parser.parse_args()

    total_rows, missing = tag_inventory(args.inventory_csv, args.scryfall_db, args.output)
    print(f"Tagged {total_rows} rows; {missing} rows missing color identity")


if __name__ == "__main__":
    main()
