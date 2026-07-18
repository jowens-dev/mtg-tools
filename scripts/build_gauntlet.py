#!/usr/bin/env python3
"""Build a simple gauntlet-card candidate list from a tagged inventory CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable


def resolve_price_column(headers: Iterable[str]) -> str:
    for candidate in ["Price", "price", "Market Price", "market_price", "Price USD", "price_usd", "TCG Market Price", "tcg_market_price"]:
        if candidate in headers:
            return candidate
    raise ValueError("No supported price column found in inventory CSV")


def resolve_quantity_column(headers: Iterable[str]) -> str:
    for candidate in ["Quantity", "quantity", "Qty", "qty", "Count", "count", "Total Quantity", "total_quantity"]:
        if candidate in headers:
            return candidate
    raise ValueError("No supported quantity column found in inventory CSV")


def build_gauntlet(inventory_path: str | Path, *, color_identity: str, max_price: float, max_cards: int = 60) -> list[dict[str, str]]:
    inventory_path = Path(inventory_path)
    with inventory_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Inventory CSV is empty")
        price_column = resolve_price_column(reader.fieldnames)
        quantity_column = resolve_quantity_column(reader.fieldnames)
        rows = list(reader)

    filtered: list[dict[str, str]] = []
    for row in rows:
        color_value = row.get("Color Identity", "")
        if color_identity and color_value and color_identity not in color_value.split(","):
            continue

        quantity_text = row.get(quantity_column, "0")
        try:
            quantity = int(quantity_text)
        except ValueError:
            quantity = 0
        if quantity <= 0:
            continue

        price_text = row.get(price_column, "0")
        try:
            price = float(price_text)
        except ValueError:
            price = 0.0
        if price > max_price:
            continue

        filtered.append(row)

    filtered.sort(key=lambda row: (row.get("Card Name", row.get("Product Name", row.get("Name", row.get("Title", "")))),))
    return filtered[:max_cards]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory_csv", help="Path to the color-tagged inventory CSV")
    parser.add_argument("--color-identity", required=True, help="Color identity to filter by, e.g. R or W,U")
    parser.add_argument("--max-price", type=float, required=True, help="Maximum price per card")
    parser.add_argument("--max-cards", type=int, default=60, help="Maximum cards to output")
    parser.add_argument("--output", help="Optional CSV path for the gauntlet candidate list")
    args = parser.parse_args()

    candidates = build_gauntlet(args.inventory_csv, color_identity=args.color_identity, max_price=args.max_price, max_cards=args.max_cards)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(candidates[0].keys()) if candidates else ["Card Name", "Color Identity", "Price", "Quantity"])
            writer.writeheader()
            writer.writerows(candidates)

    for candidate in candidates:
        print(candidate.get("Card Name", ""))


if __name__ == "__main__":
    main()
