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
    assert is_ramp(MOCK_LAND) is False  # Lands shouldn't be counted in the ramp spell slot

    assert is_draw(MOCK_DRAW_SPELL) is True
    assert is_draw(MOCK_PLAIN_CREATURE) is False

    assert is_removal(MOCK_REMOVAL_SPELL) is True
    assert is_removal(MOCK_REMOVAL_COUNTER) is True
    assert is_removal(MOCK_PLAIN_CREATURE) is False


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

    # Blood Artist matches vampire subtype (3 points) + type line (1 point) = 4
    assert calculate_synergy_score(card_matching_both, keywords) == 4
    
    # Vampire Nighthawk matches vampire subtype (3 points) + type line (1 point) = 4
    assert calculate_synergy_score(card_matching_type, keywords) == 4
    
    # Counterspell matches nothing
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
            "cmc": 6
        },
        "vampire nighthawk": {
            "name": "Vampire Nighthawk",
            "color_identity": ["B"],
            "type_line": "Creature — Vampire Shaman",
            "subtypes": ["vampire", "shaman"],
            "oracle_text": "Lifelink",
            "cmc": 3
        },
        "sol ring": {
            "name": "Sol Ring",
            "color_identity": [],
            "type_line": "Artifact",
            "subtypes": [],
            "oracle_text": "{T}: Add {C}{C}.",
            "cmc": 1
        },
        "swamp": {
            "name": "Swamp",
            "color_identity": ["B"],
            "type_line": "Basic Land — Swamp",
            "subtypes": [],
            "oracle_text": "",
            "cmc": 0
        },
        "counterspell": {
            "name": "Counterspell",
            "color_identity": ["U"],
            "type_line": "Instant",
            "subtypes": [],
            "oracle_text": "Counter target spell.",
            "cmc": 2
        }
    }

    # Setup mock collection
    collection = ["Edgar Markov", "Vampire Nighthawk", "Sol Ring", "Counterspell"]
    # Add 40 swamps to fill land and remaining requirements
    collection.extend(["Swamp"] * 40)

    # Edgar Markov has WBR color identity.
    # Counterspell has U color identity, so it should be filtered out.
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
    
    # Lands check (should only contain valid color identity lands)
    assert len(deck["lands"]) == 10
    assert all(c["name"] == "Swamp" for c in deck["lands"])

    # Sol ring is a ramp artifact
    assert len(deck["ramp"]) == 1
    assert deck["ramp"][0]["name"] == "Sol Ring"

    # Counterspell is invalid color identity (Blue), so it shouldn't be in the deck
    all_deck_cards = deck["lands"] + deck["ramp"] + deck["draw"] + deck["removal"] + deck["synergy"]
    assert not any(c["name"] == "Counterspell" for c in all_deck_cards)
    assert not any(c["name"] == "Edgar Markov" for c in all_deck_cards)  # Commander is excluded from deck lists

    # Vampire Nighthawk matches "vampire" keyword, so it should be in the synergy slot
    assert any(c["name"] == "Vampire Nighthawk" for c in deck["synergy"])

    # Vorthos details assertions
    assert deck["commander_plane"] == "Innistrad"
    # Vampire Nighthawk does not have Innistrad keywords in this minimal mock dict,
    # so cohesion_score should be 0.0% (0 of 1 spells with resolved planes, wait: Sol Ring is not a land, but has no plane keywords).
    # Since Sol Ring has no plane, spells_with_planes = 0.
    # Therefore, cohesion_score should be None (or N/A).
    assert deck["cohesion_score"] is None
    assert len(deck["clashes"]) == 0

