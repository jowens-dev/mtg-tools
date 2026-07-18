import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from flavor_engine import resolve_card_plane, check_aesthetic_clash


def test_resolve_card_plane_by_set():
    card_kamigawa = {"set": "neo", "name": "Reckoner Bankbuster", "flavor_text": ""}
    card_innistrad = {"set": "isd", "name": "Olivia Voldaren", "flavor_text": ""}
    card_unknown = {"set": "xyz", "name": "Generic Card", "flavor_text": ""}

    assert resolve_card_plane(card_kamigawa) == "Kamigawa"
    assert resolve_card_plane(card_innistrad) == "Innistrad"
    assert resolve_card_plane(card_unknown) is None


def test_resolve_card_plane_by_keywords():
    # Card from generic set (e.g. Commander C17) containing Innistrad keywords
    card_lore = {
        "set": "c17",
        "name": "Edgar's Crusade",
        "flavor_text": "The Markov bloodline will rise again.",
        "oracle_text": ""
    }
    # Card with keyword in oracle text
    card_oracle = {
        "set": "m15",
        "name": "Angel of Sigarda",
        "flavor_text": "",
        "oracle_text": "Whenever a creature dies, search for Avacyn."
    }

    assert resolve_card_plane(card_lore) == "Innistrad"
    assert resolve_card_plane(card_oracle) == "Innistrad"


def test_check_aesthetic_clash():
    # Cyberpunk (Kamigawa) in Gothic Horror (Innistrad) -> Clash!
    clash1, msg1 = check_aesthetic_clash("Innistrad", "Kamigawa")
    assert clash1 is True
    assert "Aesthetic Clash" in msg1

    # Art Deco (Capenna) in Greek Myth (Theros) -> Clash!
    clash2, msg2 = check_aesthetic_clash("Theros", "Capenna")
    assert clash2 is True
    assert "Aesthetic Clash" in msg2

    # High Fantasy (Dominaria) in Gothic Horror (Innistrad) -> No Clash (Classic/Broad Compatibility)
    clash3, msg3 = check_aesthetic_clash("Innistrad", "Dominaria")
    assert clash3 is False
    assert msg3 == ""

    # Same Plane -> No Clash
    clash4, msg4 = check_aesthetic_clash("Innistrad", "Innistrad")
    assert clash4 is False
    assert msg4 == ""
