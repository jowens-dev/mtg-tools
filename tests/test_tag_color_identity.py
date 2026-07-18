import csv
import sqlite3
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from tag_color_identity import build_color_lookup_from_api, normalize_color_identity, resolve_name_column, tag_inventory


def test_resolve_name_column_prefers_common_inventory_headers():
    assert resolve_name_column(["Ignore", "Card Name", "Qty"]) == "Card Name"
    assert resolve_name_column(["card_name", "Qty"]) == "card_name"


def test_resolve_name_column_raises_when_no_supported_header_exists():
    with pytest.raises(ValueError):
        resolve_name_column(["CardTitle", "Count"])


def test_normalize_color_identity_splits_and_orders_letters():
    assert normalize_color_identity("WU") == "W,U"
    assert normalize_color_identity("W,U") == "W,U"
    assert normalize_color_identity("") == ""


def test_build_color_lookup_from_api_uses_payload_color_identity(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout):
        return FakeResponse()

    monkeypatch.setattr("tag_color_identity.urllib.request.urlopen", fake_urlopen)

    def fake_json_load(response):
        return {"data": [{"name": "Lightning Bolt", "color_identity": ["R"]}]}

    monkeypatch.setattr("tag_color_identity.json.load", fake_json_load)

    assert build_color_lookup_from_api(["Lightning Bolt"]) == {"Lightning Bolt": "R"}


def test_tag_inventory_accepts_tcgplayer_style_headers(tmp_path):
    inventory_path = tmp_path / "inventory.csv"
    inventory_path.write_text(
        "Product Name,TCG Market Price,Total Quantity\nLightning Bolt,1.23,2\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "cards.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE cards (name TEXT, color_identity TEXT)")
    connection.execute("INSERT INTO cards VALUES (?, ?)", ("Lightning Bolt", "R"))
    connection.commit()
    connection.close()

    output_path = tmp_path / "tagged.csv"
    total_rows, missing = tag_inventory(str(inventory_path), str(db_path), str(output_path))

    assert total_rows == 1
    assert missing == 0

    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["Color Identity"] == "R"
