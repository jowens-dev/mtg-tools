import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_gauntlet import build_gauntlet, resolve_price_column


def test_resolve_price_column_prefers_common_price_headers():
    assert resolve_price_column(["Ignore", "Price", "Qty"]) == "Price"
    assert resolve_price_column(["price", "Qty"]) == "price"


def test_build_gauntlet_filters_by_color_identity_and_budget(tmp_path):
    inventory_path = tmp_path / "inventory.csv"
    with inventory_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Card Name", "Color Identity", "Price", "Quantity"])
        writer.writeheader()
        writer.writerow({"Card Name": "Lightning Bolt", "Color Identity": "R", "Price": "1.00", "Quantity": "2"})
        writer.writerow({"Card Name": "Shock", "Color Identity": "R", "Price": "2.00", "Quantity": "1"})
        writer.writerow({"Card Name": "Counterspell", "Color Identity": "U", "Price": "1.50", "Quantity": "2"})

    result = build_gauntlet(str(inventory_path), color_identity="R", max_price=1.50, max_cards=5)

    assert [row["Card Name"] for row in result] == ["Lightning Bolt"]


def test_build_gauntlet_accepts_tcgplayer_style_headers(tmp_path):
    inventory_path = tmp_path / "inventory.csv"
    with inventory_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Product Name", "Color Identity", "TCG Market Price", "Total Quantity"])
        writer.writeheader()
        writer.writerow({"Product Name": "Lightning Bolt", "Color Identity": "R", "TCG Market Price": "1.00", "Total Quantity": "2"})
        writer.writerow({"Product Name": "Shock", "Color Identity": "R", "TCG Market Price": "2.00", "Total Quantity": "1"})

    result = build_gauntlet(str(inventory_path), color_identity="R", max_price=1.50, max_cards=5)

    assert [row["Product Name"] for row in result] == ["Lightning Bolt"]


def test_build_gauntlet_raises_when_no_supported_price_column_exists(tmp_path):
    inventory_path = tmp_path / "inventory.csv"
    with inventory_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Card Name", "Color Identity", "Cost"])
        writer.writeheader()
        writer.writerow({"Card Name": "Lightning Bolt", "Color Identity": "R", "Cost": "1.00"})

    with pytest.raises(ValueError):
        build_gauntlet(str(inventory_path), color_identity="R", max_price=1.50)
