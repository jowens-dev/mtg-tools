import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from recommend_deck import (
    calculate_spice_score,
    generate_deck
)


def test_intent_keyword_multipliers():
    commander = {"name": "Edgar", "subtypes": ["vampire"], "keywords": []}
    comm_keywords = {"vampire"}
    obscurity_db = {"subtypes": {"vampire": 50}, "keywords": {}}

    card_aggro = {
        "name": "Blade Historian",
        "type_line": "Creature — Human Soldier",
        "subtypes": [],
        "oracle_text": "Attacking creatures you control have double strike.",
        "cmc": 4,
        "reprint": True,
        "set_type": "core"
    }

    # Calculation under Aggro-Combat playstyle
    score_aggro, _ = calculate_spice_score(card_aggro, commander, comm_keywords, obscurity_db, "Aggro-Combat")
    
    # Calculation under Grindy Value Engine playstyle (should not match keywords and therefore have a lower score)
    score_grindy, _ = calculate_spice_score(card_aggro, commander, comm_keywords, obscurity_db, "Grindy Value Engine")

    # score_aggro should be exactly 1.5x the base score (since the card has "attacking" and "double strike")
    assert score_aggro == pytest.approx(score_grindy * 1.5)


def test_bracket_mismatch_low_power_with_fast_mana():
    # Setup mock oracle db
    oracle_db = {
        "edgar markov": {
            "name": "Edgar Markov",
            "color_identity": ["W", "B", "R"],
            "type_line": "Legendary Creature — Vampire Knight",
            "subtypes": ["vampire", "knight"],
            "oracle_text": "Create tokens.",
            "cmc": 6,
            "reprint": False,
            "set_type": "expansion"
        },
        "mana crypt": {
            "name": "Mana Crypt",
            "color_identity": [],
            "type_line": "Artifact",
            "subtypes": [],
            "oracle_text": "{T}: Add {C}{C}.",
            "cmc": 0,
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
        }
    }

    collection = ["Edgar Markov", "Mana Crypt"] + ["Swamp"] * 40
    intent_profile = {"target_ix": "Aggro-Combat", "bracket_level": 2, "win_cons_needed": 1}

    deck = generate_deck("Edgar Markov", collection, oracle_db, intent_profile, target_lands=10, target_ramp=1, target_draw=0, target_removal=0, target_synergy=5)
    
    # Should trigger a warning because Mana Crypt (fast mana) is in a Bracket 2 deck
    assert len(deck["bracket_warnings"]) > 0
    assert "mana crypt" in deck["bracket_warnings"][0]


def test_win_condition_density_auditor():
    oracle_db = {
        "edgar markov": {
            "name": "Edgar Markov",
            "color_identity": ["W", "B", "R"],
            "type_line": "Legendary Creature — Vampire Knight",
            "subtypes": ["vampire", "knight"],
            "oracle_text": "Create tokens.",
            "cmc": 6,
            "reprint": False,
            "set_type": "expansion"
        },
        "craterhoof behemoth": {
            "name": "Craterhoof Behemoth",
            "color_identity": ["B"],
            "type_line": "Creature — Beast",
            "subtypes": ["beast"],
            "oracle_text": "Creatures you control get +5/+5 and gain trample.", # triggers finisher regex
            "cmc": 8,
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
        }
    }

    collection = ["Edgar Markov", "Craterhoof Behemoth"] + ["Swamp"] * 40
    
    # We require 3 win conditions in the profile
    intent_profile_high_demand = {"target_ix": "Aggro-Combat", "bracket_level": 2, "win_cons_needed": 3}
    deck_warning = generate_deck("Edgar Markov", collection, oracle_db, intent_profile_high_demand, target_lands=10, target_ramp=0, target_draw=0, target_removal=0, target_synergy=5)
    
    # We require 1 win condition in the profile
    intent_profile_low_demand = {"target_ix": "Aggro-Combat", "bracket_level": 2, "win_cons_needed": 1}
    deck_fine = generate_deck("Edgar Markov", collection, oracle_db, intent_profile_low_demand, target_lands=10, target_ramp=0, target_draw=0, target_removal=0, target_synergy=5)

    # Deck with high demand has warnings, deck with low demand has none
    assert len(deck_warning["win_con_warnings"]) > 0
    assert len(deck_fine["win_con_warnings"]) == 0
    assert deck_fine["finishers"][0]["name"] == "Craterhoof Behemoth"
