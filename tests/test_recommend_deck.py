import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from recommend_deck import (
    is_land,
    is_ramp,
    is_draw,
    is_removal,
    calculate_synergy_score,
    extract_commander_keywords,
    calculate_scarcity_score,
    calculate_text_density_score,
    calculate_spice_score,
    generate_deck
)

# Mock cards for testing role classification
MOCK_LAND = {"type_line": "Basic Land — Swamp"}
MOCK_RAMP_ARTIFACT = {"type_line": "Artifact", "oracle_text": "{T}: Add {C}."}
MOCK_RAMP_SPELL = {"type_line": "Sorcery", "oracle_text": "Search your library for a basic land card and put it onto the battlefield."}
MOCK_RAMP_TREASURE = {"type_line": "Instant", "oracle_text": "Create two Treasure tokens."}
MOCK_DRAW_SPELL = {"type_line": "Sorcery", "oracle_text": "Draw three cards, then discard a card."}
MOCK_REMOVAL_SPELL = {"type_line": "Instant", "oracle_text": "Destroy target nonland permanent."}
MOCK_REMOVAL_COUNTER = {"type_line": "Instant", "oracle_text": "Counter target spell."}
MOCK_PLAIN_CREATURE = {"type_line": "Creature — Vampire Soldier", "oracle_text": "Flying."}


def test_card_role_classification():
    assert is_land(MOCK_LAND) is True
    assert is_land(MOCK_RAMP_ARTIFACT) is False

    assert is_ramp(MOCK_RAMP_ARTIFACT) is True
    assert is_ramp(MOCK_RAMP_SPELL) is True
    assert is_ramp(MOCK_RAMP_TREASURE) is True
    assert is_ramp(MOCK_PLAIN_CREATURE) is False
    assert is_ramp(MOCK_LAND) is False

    assert is_draw(MOCK_DRAW_SPELL) is True
    assert is_draw(MOCK_PLAIN_CREATURE) is False

    assert is_removal(MOCK_REMOVAL_SPELL) is True
    assert is_removal(MOCK_REMOVAL_COUNTER) is True
    assert is_removal(MOCK_PLAIN_CREATURE) is False


def test_scarcity_score():
    # Single print card
    card_single = {"reprint": False, "set_type": "expansion"}
    assert calculate_scarcity_score(card_single) == 10.0

    # Common reprinted staple
    card_core = {"reprint": True, "set_type": "core"}
    assert calculate_scarcity_score(card_core) == 1.0

    # Expansion reprint
    card_expansion_reprint = {"reprint": True, "set_type": "expansion"}
    assert calculate_scarcity_score(card_expansion_reprint) == 5.0


def test_text_density_score():
    # 100 character rules text, 2 CMC. Ratio = 100 / 2 = 50. Output = 50 / 50 = 1.0
    card_normal = {"oracle_text": "A" * 100, "cmc": 2}
    assert calculate_text_density_score(card_normal) == 1.0

    # 50 character rules text, 0 CMC. Ratio = 50 / max(0, 0.5) = 100. Output = 100 / 50 = 2.0
    card_free = {"oracle_text": "B" * 50, "cmc": 0}
    assert calculate_text_density_score(card_free) == 2.0


def test_calculate_spice_score():
    # Setup commander
    commander = {
        "name": "Edgar Markov",
        "subtypes": ["vampire"],
        "keywords": []
    }
    comm_keywords = {"vampire"}

    # Obscurity DB: Vampire is obscure (count 10), Shaman is common (count 500)
    obscurity_db = {
        "subtypes": {
            "vampire": 10,
            "shaman": 500
        },
        "keywords": {}
    }

    # Card 1: Core role (Ramp) and shares obscure subtype (Vampire) -> Deep Cut
    card_deep = {
        "name": "Blood Artist",
        "type_line": "Creature — Vampire",
        "subtypes": ["vampire"],
        "oracle_text": "Search your library for a basic land card.",  # triggers is_ramp
        "cmc": 2,
        "reprint": True,
        "set_type": "core"
    }

    # Card 2: Core role (Ramp) but shares common/no obscure subtype (Shaman) -> No Deep Cut
    card_no_deep = {
        "name": "Sakura-Tribe Elder",
        "type_line": "Creature — Snake Shaman",
        "subtypes": ["snake", "shaman"],
        "oracle_text": "Search your library for a basic land card.",  # triggers is_ramp
        "cmc": 2,
        "reprint": True,
        "set_type": "core"
    }

    score_deep, is_deep = calculate_spice_score(card_deep, commander, comm_keywords, obscurity_db)
    score_no_deep, is_no_deep = calculate_spice_score(card_no_deep, commander, comm_keywords, obscurity_db)

    assert is_deep is True
    assert is_no_deep is False
    
    # Deep score should be doubled
    # Blood Artist synergy: 3 (vampire subtype) + 1 (vampire in type line) = 4
    # Scarcity: reprint in core = 1.0
    # Text density: len("Search your library for a basic land card.") is 42. cmc is 2. 42/2 = 21.0. Density score = 21.0 / 50 = 0.42
    # Total pre-deep = 4 + 1.0 + 0.42 = 5.42. Doubled = 10.84
    assert score_deep == pytest.approx(10.84)


def test_extract_commander_keywords():
    commander = {
        "name": "Edgar Markov",
        "type_line": "Legendary Creature — Vampire Knight",
        "subtypes": ["vampire", "knight"],
        "oracle_text": "Whenever you cast another Vampire spell, create a 1/1 black Vampire creature token."
    }
    keywords = extract_commander_keywords(commander)
    assert "vampire" in keywords
    assert "knight" in keywords
    assert "token" in keywords


def test_calculate_synergy_score():
    keywords = {"vampire", "token"}
    card_matching_both = {
        "name": "Blood Artist",
        "type_line": "Creature — Vampire",
        "subtypes": ["vampire"],
        "oracle_text": "Whenever Blood Artist or another creature dies, target player loses 1 life."
    }
    card_matching_type = {
        "name": "Vampire Nighthawk",
        "type_line": "Creature — Vampire Shaman",
        "subtypes": ["vampire", "shaman"],
        "oracle_text": "Flying, lifelink, deathtouch"
    }
    card_no_match = {
        "name": "Counterspell",
        "type_line": "Instant",
        "subtypes": [],
        "oracle_text": "Counter target spell."
    }

    assert calculate_synergy_score(card_matching_both, keywords) == 4
    assert calculate_synergy_score(card_matching_type, keywords) == 4
    assert calculate_synergy_score(card_no_match, keywords) == 0


def test_deck_generation():
    # Setup mock oracle db
    oracle_db = {
        "edgar markov": {
            "name": "Edgar Markov",
            "color_identity": ["W", "B", "R"],
            "type_line": "Legendary Creature — Vampire Knight",
            "subtypes": ["vampire", "knight"],
            "oracle_text": "Create Vampire tokens.",
            "cmc": 6,
            "reprint": False,
            "set_type": "expansion"
        },
        "vampire nighthawk": {
            "name": "Vampire Nighthawk",
            "color_identity": ["B"],
            "type_line": "Creature — Vampire Shaman",
            "subtypes": ["vampire", "shaman"],
            "oracle_text": "Lifelink",
            "cmc": 3,
            "reprint": True,
            "set_type": "core"
        },
        "sol ring": {
            "name": "Sol Ring",
            "color_identity": [],
            "type_line": "Artifact",
            "subtypes": [],
            "oracle_text": "{T}: Add {C}{C}.",
            "cmc": 1,
            "reprint": True,
            "set_type": "core"
        },
        "swamp": {
            "name": "Swamp",
            "color_identity": ["B"],
            "type_line": "Basic Land — Swamp",
            "subtypes": [],
            "oracle_text": "",
            "cmc": 0,
            "reprint": True,
            "set_type": "core"
        },
        "counterspell": {
            "name": "Counterspell",
            "color_identity": ["U"],
            "type_line": "Instant",
            "subtypes": [],
            "oracle_text": "Counter target spell.",
            "cmc": 2,
            "reprint": True,
            "set_type": "core"
        },
        "_obscurity_db": {
            "subtypes": {"vampire": 50, "shaman": 200},
            "keywords": {}
        }
    }

    # Setup mock collection
    collection = ["Edgar Markov", "Vampire Nighthawk", "Sol Ring", "Counterspell"]
    collection.extend(["Swamp"] * 40)

    deck = generate_deck(
        "Edgar Markov",
        collection,
        oracle_db,
        target_lands=10,
        target_ramp=1,
        target_draw=1,
        target_removal=1,
        target_synergy=5
    )

    # Assertions
    assert deck["commander"]["name"] == "Edgar Markov"
    assert "vampire" in deck["keywords"]
    assert len(deck["lands"]) == 10
    assert all(c["name"] == "Swamp" for c in deck["lands"])

    assert len(deck["ramp"]) == 1
    assert deck["ramp"][0]["name"] == "Sol Ring"

    all_deck_cards = deck["lands"] + deck["ramp"] + deck["draw"] + deck["removal"] + deck["synergy"]
    assert not any(c["name"] == "Counterspell" for c in all_deck_cards)
    assert not any(c["name"] == "Edgar Markov" for c in all_deck_cards)

    assert any(c["name"] == "Vampire Nighthawk" for c in deck["synergy"])

    # Spice assertions
    assert deck["average_spice"] > 0
    assert "sol ring" in deck["spice_data"]
    assert "vampire nighthawk" in deck["spice_data"]
