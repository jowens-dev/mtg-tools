import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from math_utils import (
    hypergeometric_pmf,
    hypergeometric_cdf_ge,
    calculate_joint_consistency
)

from recommend_deck import (
    calculate_fragility_weight,
    is_protection,
    is_multiplayer_scaling,
    calculate_spice_score
)


def test_hypergeometric_pmf():
    # In a population of 10 with 4 successes, probability of drawing exactly 2 successes in 3 draws
    # comb(4, 2) * comb(6, 1) / comb(10, 3) = 6 * 6 / 120 = 36 / 120 = 0.3
    assert hypergeometric_pmf(10, 3, 4, 2) == pytest.approx(0.3)
    
    # Boundary cases
    assert hypergeometric_pmf(10, 3, 4, 5) == 0.0
    assert hypergeometric_pmf(10, 3, 4, -1) == 0.0


def test_hypergeometric_cdf_ge():
    # In a population of 10 with 4 successes, probability of drawing >= 2 successes in 3 draws
    # P(X=2) + P(X=3) = 0.3 + (comb(4, 3) * comb(6, 0) / 120) = 0.3 + (4 / 120) = 0.3 + 0.03333... = 0.33333...
    assert hypergeometric_cdf_ge(10, 3, 4, 2) == pytest.approx(1/3)


def test_calculate_joint_consistency():
    # Small population joint test
    # Deck size: 20
    # Hand size: 5
    # Lands: 8 (need >= 2)
    # Ramp: 4 (need >= 1)
    # Draw: 3 (need >= 1)
    prob = calculate_joint_consistency(20, 5, 8, 2, 4, 1, 3, 1)
    assert 0.0 < prob < 1.0


def test_calculate_fragility_weight():
    card_creature = {"type_line": "Creature — Vampire"}
    card_artifact = {"type_line": "Artifact"}
    card_enchantment = {"type_line": "Enchantment"}
    card_land = {"type_line": "Land"}
    card_spell = {"type_line": "Instant"}
    card_art_creature = {"type_line": "Artifact Creature — Construct"}

    assert calculate_fragility_weight(card_creature) == 0.8
    assert calculate_fragility_weight(card_artifact) == 0.6
    assert calculate_fragility_weight(card_enchantment) == 0.3
    assert calculate_fragility_weight(card_land) == 0.05
    assert calculate_fragility_weight(card_spell) == 0.0
    # Artifact Creature picks the highest (Creature: 0.8)
    assert calculate_fragility_weight(card_art_creature) == 0.8


def test_is_protection():
    card_protect = {"type_line": "Instant", "oracle_text": "Target creature gains hexproof and indestructible."}
    card_normal = {"type_line": "Instant", "oracle_text": "Draw 2 cards."}
    
    assert is_protection(card_protect) is True
    assert is_protection(card_normal) is False


def test_is_multiplayer_scaling():
    card_multi = {"type_line": "Enchantment", "oracle_text": "At the beginning of your upkeep, each opponent loses 1 life."}
    card_normal = {"type_line": "Enchantment", "oracle_text": "You draw a card."}

    assert is_multiplayer_scaling(card_multi) is True
    assert is_multiplayer_scaling(card_normal) is False


def test_multiplayer_spice_multiplier():
    # When a card has a multiplayer trigger, its spice score should be multiplied by 3x.
    commander = {"name": "Edgar", "subtypes": ["vampire"], "keywords": []}
    comm_keywords = {"vampire"}
    obscurity_db = {"subtypes": {"vampire": 50}, "keywords": {}}

    card_plain = {
        "name": "Blood Artist",
        "type_line": "Creature — Vampire",
        "subtypes": ["vampire"],
        "oracle_text": "Whenever a creature dies, target player loses 1 life.",
        "cmc": 2,
        "reprint": True,
        "set_type": "core"
    }

    card_multi = {
        "name": "Blood Artist",
        "type_line": "Creature — Vampire",
        "subtypes": ["vampire"],
        "oracle_text": "Whenever a creature dies, each opponent loses 1 life.", # triggers multiplayer
        "cmc": 2,
        "reprint": True,
        "set_type": "core"
    }

    score_plain, _ = calculate_spice_score(card_plain, commander, comm_keywords, obscurity_db)
    score_multi, _ = calculate_spice_score(card_multi, commander, comm_keywords, obscurity_db)

    # The rules text of card_multi is slightly longer, so text density will be slightly different.
    # But let's check: card_multi has is_multiplayer_scaling(card) == True, so it gets multiplied by 3.0.
    # score_plain is: base_synergy (4) + scarcity (1.0) + density (len("Whenever a creature dies, target player loses 1 life.") is 53. 53/2 = 26.5. 26.5/50 = 0.53) = 5.53
    # score_multi pre-mult is: base_synergy (4) + scarcity (1.0) + density (len("Whenever a creature dies, each opponent loses 1 life.") is 53. 53/2 = 26.5. 26.5/50 = 0.53) = 5.53.
    # score_multi post-mult = 5.53 * 3 = 16.59.
    assert score_plain == pytest.approx(5.53)
    assert score_multi == pytest.approx(16.59)
