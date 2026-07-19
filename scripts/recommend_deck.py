#!/usr/bin/env python3
"""Recommend a rules-based, objective 99-card Commander deck list from an owned collection using the Spice Weighting Algorithm and advanced engine analysis."""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Import math utility functions
from math_utils import calculate_joint_consistency

# --- OBJECTIVE CLASSIFIER REGEXES ---
RAMP_PATTERNS = [
    re.compile(r"\badd\b.*\bmana\b", re.IGNORECASE),
    re.compile(r"\badd\s+({[WUBRGCCX/]+}|\w+\s+mana)", re.IGNORECASE),
    re.compile(r"search\s+your\s+library\s+for\s+a\s+.*land", re.IGNORECASE),
    re.compile(r"create\s+.*Treasure", re.IGNORECASE),
]

DRAW_PATTERNS = [
    re.compile(r"\bdraw\s+(\w+|\d+)?\s*cards?\b", re.IGNORECASE),
    re.compile(r"\bdraws\s+a\s+card\b", re.IGNORECASE),
]

REMOVAL_PATTERNS = [
    re.compile(r"\b(destroy|exile|counter)\b\s+target", re.IGNORECASE),
    re.compile(r"deals?\s+(\d+|x)\s+damage\s+to\s+target", re.IGNORECASE),
    re.compile(r"damage\s+to\s+any\s+target", re.IGNORECASE),
    re.compile(r"counter\s+target\s+spell", re.IGNORECASE),
]

NOISE_TYPES = {
    "legendary", "basic", "snow", "world", "ongoing",
    "creature", "artifact", "enchantment", "instant", "sorcery",
    "planeswalker", "land", "battle", "tribal", "hero", "scheme", "vanguard",
    "plains", "island", "swamp", "mountain", "forest", "wastes"
}

PROTECTION_KEYWORDS = [
    r"\bhexproof\b", r"\bshroud\b", r"\bindestructible\b", 
    r"\bphase out\b", r"\bregenerate\b", r"\bcounter target\b"
]
PROTECTION_REGEX = re.compile("|".join(PROTECTION_KEYWORDS), re.IGNORECASE)

MULTIPLAYER_KEYWORDS = [
    r"each opponent", r"whenever an opponent", r"each player", r"number of opponents"
]
MULTIPLAYER_REGEX = re.compile("|".join(MULTIPLAYER_KEYWORDS), re.IGNORECASE)

# --- INTENTIONAL EXPERIENCE (IX) CONFIGS ---
INTENT_KEYWORDS = {
    "Aggro-Combat": ["combat", "attack", "damage", "trample", "haste", "double strike"],
    "Grindy Value Engine": ["recursion", "draw", "graveyard", "return", "whenever", "end step", "trigger"],
    "Deterministic Combo": ["infinite", "win the game", "tutor", "search your library", "untap"],
    "Political/Interactive": ["monarch", "vote", "council", "tempt", "choice", "gains control"]
}

FAST_MANA_CARDS = {
    "mana vault", "mana crypt", "jeweled lotus", "mox diamond", "chrome mox", 
    "mox opal", "grim monolith", "lion's eye diamond"
}

HIGH_EFFICIENCY_TUTORS = {
    "demonic tutor", "vampiric tutor", "mystical tutor", "enlightened tutor", 
    "worldly tutor", "imperial seal"
}

FINISHER_KEYWORDS = [
    r"win the game", r"loses the game", r"additional combat phase", 
    r"\binfect\b", r"creatures you control get \+\d+/\+\d+"
]
FINISHER_REGEX = re.compile("|".join(FINISHER_KEYWORDS), re.IGNORECASE)


def load_oracle_database(filepath: Path) -> dict:
    """Load Scryfall oracle cards from a JSON file into a name-keyed lookup dictionary."""
    filepath = Path(filepath)
    database = {}
    if not filepath.exists():
        print(f"Error: Oracle DB not found at {filepath}", file=sys.stderr)
        return database

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"Error parsing Oracle DB: {e}", file=sys.stderr)
        return database

    keyword_counts = defaultdict(int)
    subtype_counts = defaultdict(int)

    for card in raw_data:
        name = card.get("name", "")
        if not name:
            continue

        name_lower = name.lower()
        color_identity = card.get("color_identity", [])
        cmc = card.get("cmc", 0.0)
        set_code = card.get("set", "")
        flavor_text = card.get("flavor_text", "")
        set_type = card.get("set_type", "")
        reprint = card.get("reprint", False)

        # Handle double faced cards
        if "card_faces" in card:
            faces = card["card_faces"]
            mana_cost = faces[0].get("mana_cost", "")
            type_line = " / ".join(f.get("type_line", "") for f in faces)
            oracle_text = "\n//\n".join(f.get("oracle_text", "") for f in faces)
            colors = list(set(card.get("colors", []) + faces[0].get("colors", []) + (faces[1].get("colors", []) if len(faces) > 1 else [])))
            flavor_text = "\n//\n".join(f.get("flavor_text", "") for f in faces if f.get("flavor_text")) or flavor_text
        else:
            mana_cost = card.get("mana_cost", "")
            type_line = card.get("type_line", "")
            oracle_text = card.get("oracle_text", "")
            colors = card.get("colors", [])

        # Parse types
        clean_types = type_line.replace("—", " ").replace("-", " ").lower().split()
        subtypes = [t for t in clean_types if t not in NOISE_TYPES and len(t) > 2]

        # Extract keywords
        raw_keywords = [kw.lower() for kw in card.get("keywords", []) if kw]

        database[name_lower] = {
            "name": name,
            "mana_cost": mana_cost,
            "colors": colors,
            "color_identity": color_identity,
            "type_line": type_line,
            "subtypes": subtypes,
            "oracle_text": oracle_text or "",
            "cmc": int(cmc),
            "set": set_code,
            "flavor_text": flavor_text or "",
            "set_type": set_type,
            "reprint": reprint,
            "keywords": raw_keywords,
            "types": subtypes,      # Compatibility for UI dashboard
            "raw_type": type_line   # Compatibility for UI dashboard
        }

        # Track frequencies
        for sub in subtypes:
            subtype_counts[sub] += 1
        for kw in raw_keywords:
            keyword_counts[kw] += 1

    database["_obscurity_db"] = {
        "subtypes": subtype_counts,
        "keywords": keyword_counts
    }
    return database


def load_collection(filepath: Path) -> list[str]:
    """Load owned cards from a CSV file, returning a list of card names."""
    cards = []
    if not filepath.exists():
        print(f"Error: Collection file not found at {filepath}", file=sys.stderr)
        return cards

    with filepath.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return cards

        # Resolve card name column
        name_col = None
        for col in ["Card Name", "Product Name", "Name", "Title", "card_name"]:
            if col in reader.fieldnames:
                name_col = col
                break

        if not name_col:
            print("Error: Could not find card name column in CSV", file=sys.stderr)
            return cards

        # Resolve quantity column
        qty_col = None
        for col in ["Quantity", "quantity", "Qty", "qty", "Count", "count", "Total Quantity"]:
            if col in reader.fieldnames:
                qty_col = col
                break

        for row in reader:
            name = row.get(name_col, "").strip()
            if not name:
                continue

            qty = 1
            if qty_col:
                try:
                    qty = int(row.get(qty_col, "1"))
                except ValueError:
                    qty = 1

            for _ in range(qty):
                cards.append(name)

    return cards


def load_intent_profile(filepath: Path) -> dict:
    """Load the Deck Intent Profile header from a JSON config file."""
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not parse intent profile at {filepath}: {e}", file=sys.stderr)
    return {"target_ix": "Aggro-Combat", "bracket_level": 2, "win_cons_needed": 3}


def is_land(card: dict) -> bool:
    return "land" in card.get("type_line", "").lower()


def is_ramp(card: dict) -> bool:
    if is_land(card):
        return False
    text = card.get("oracle_text", "")
    return any(p.search(text) for p in RAMP_PATTERNS)


def is_draw(card: dict) -> bool:
    if is_land(card):
        return False
    text = card.get("oracle_text", "")
    return any(p.search(text) for p in DRAW_PATTERNS)


def is_removal(card: dict) -> bool:
    if is_land(card):
        return False
    text = card.get("oracle_text", "")
    return any(p.search(text) for p in REMOVAL_PATTERNS)


def is_protection(card: dict) -> bool:
    if is_land(card):
        return False
    text = card.get("oracle_text", "")
    return bool(PROTECTION_REGEX.search(text))


def is_multiplayer_scaling(card: dict) -> bool:
    if is_land(card):
        return False
    text = card.get("oracle_text", "")
    return bool(MULTIPLAYER_REGEX.search(text))


def calculate_fragility_weight(card: dict) -> float:
    """Determine the baseline fragility weight of a card type."""
    type_line = card.get("type_line", "").lower()
    if "land" in type_line:
        return 0.05
    
    weights = []
    if "creature" in type_line:
        weights.append(0.8)
    if "planeswalker" in type_line:
        weights.append(0.7)
    if "artifact" in type_line:
        weights.append(0.6)
    if "enchantment" in type_line:
        weights.append(0.3)
        
    if weights:
        return max(weights)
    return 0.0  # Instants and Sorceries are non-permanents (no on-board disruption risk)


def extract_commander_keywords(commander: dict) -> set[str]:
    """Extract mechanical keywords and creature subtypes from the commander for synergy mapping."""
    keywords = set()
    
    # Extract subtypes (creature types)
    for subtype in commander.get("subtypes", []):
        keywords.add(subtype)

    # Standard mechanical themes to check for in commander text
    core_themes = {
        "sacrifice", "token", "graveyard", "counter", "historic", "artifact", 
        "enchantment", "landfall", "combat", "exile", "life", "discard", "draw"
    }
    
    text_lower = commander.get("oracle_text", "").lower()
    for theme in core_themes:
        if theme in text_lower:
            keywords.add(theme)

    return keywords


def calculate_synergy_score(card: dict, keywords: set[str]) -> int:
    """Calculate an objective synergy score based on keyword match count in type or text."""
    if not keywords:
        return 0

    score = 0
    # Match subtypes
    for subtype in card.get("subtypes", []):
        if subtype in keywords:
            score += 3  # Higher weight for matching creature types

    # Count keywords in oracle text and type line
    text_lower = card.get("oracle_text", "").lower()
    type_lower = card.get("type_line", "").lower()
    for kw in keywords:
        score += len(re.findall(rf"\b{re.escape(kw)}\b", text_lower))
        if kw in type_lower:
            score += 1

    return score


def calculate_scarcity_score(card: dict) -> float:
    """Award higher spice points to cards with fewer historical printings."""
    if not card.get("reprint", False):
        return 10.0  # Never reprinted, highly scarce

    set_type = card.get("set_type", "").lower()
    if set_type in ("core", "commander", "box", "promo"):
        return 1.0  # Generic reprinted staples
    elif set_type == "expansion":
        return 5.0  # Expansion set reprint
    else:
        return 3.0  # Other set types


def calculate_text_density_score(card: dict) -> float:
    """Calculate ratio of rules text character count to mana value."""
    text_len = len(card.get("oracle_text", ""))
    cmc = card.get("cmc", 0)
    ratio = text_len / max(cmc, 0.5)
    return ratio / 50.0  # Normalized scaled score


def calculate_spice_score(
    card: dict,
    commander: dict,
    comm_keywords: set[str],
    obscurity_db: dict,
    target_ix: str = None
) -> tuple[float, bool]:
    """Calculate the overall spice score of a card under the Commander, incorporating Playstyle Intentions."""
    synergy = calculate_synergy_score(card, comm_keywords)
    scarcity = calculate_scarcity_score(card)
    density = calculate_text_density_score(card)
    
    total_score = synergy + scarcity + density
    
    # Check Deep Cut Overlap
    has_obscure_match = False
    is_core_role = is_ramp(card) or is_draw(card) or is_removal(card)
    
    if is_core_role and obscurity_db:
        # Check subtypes
        shared_subtypes = set(commander.get("subtypes", [])).intersection(set(card.get("subtypes", [])))
        for sub in shared_subtypes:
            sub_count = obscurity_db.get("subtypes", {}).get(sub, 0)
            if 0 < sub_count <= 150:
                has_obscure_match = True
                break
                
        # Check keywords
        if not has_obscure_match:
            shared_kws = set(commander.get("keywords", [])).intersection(set(card.get("keywords", [])))
            for kw in shared_kws:
                kw_count = obscurity_db.get("keywords", {}).get(kw, 0)
                if 0 < kw_count <= 150:
                    has_obscure_match = True
                    break
                    
    satisfies_deep_cut = is_core_role and has_obscure_match
    
    if satisfies_deep_cut:
        total_score *= 2.0
        
    # Multiplayer setting scaling
    if is_multiplayer_scaling(card):
        total_score *= 3.0
        
    # Intent-Weighted Keyword Multiplier (1.5x)
    if target_ix and target_ix in INTENT_KEYWORDS:
        intent_kws = INTENT_KEYWORDS[target_ix]
        text_lower = (card.get("oracle_text", "") + " " + card.get("type_line", "")).lower()
        if any(re.search(rf"\b{re.escape(kw)}\b", text_lower) for kw in intent_kws):
            total_score *= 1.5
        
    return total_score, satisfies_deep_cut


def generate_deck(
    commander_name: str,
    collection_cards: list[str],
    oracle_db: dict,
    intent_profile: dict = None,
    target_lands: int = 37,
    target_ramp: int = 10,
    target_draw: int = 10,
    target_removal: int = 8,
    target_synergy: int = 34
) -> dict:
    """Filter, score, and partition cards from collection into deck slots."""
    comm_lower = commander_name.lower()
    if comm_lower not in oracle_db:
        raise ValueError(f"Commander '{commander_name}' not found in Oracle Database.")

    commander = oracle_db[comm_lower]
    comm_identity = set(commander.get("color_identity", []))

    # Extract keywords
    comm_keywords = extract_commander_keywords(commander)
    obscurity_db = oracle_db.get("_obscurity_db", {})

    # Set up default intent profile if missing
    if not intent_profile:
        intent_profile = {"target_ix": "Aggro-Combat", "bracket_level": 2, "win_cons_needed": 3}
    target_ix = intent_profile.get("target_ix", "Aggro-Combat")

    # Filter collection to valid card identities & map to oracle records
    valid_pool = []
    for name in collection_cards:
        name_lower = name.lower()
        if name_lower == comm_lower:
            continue  # Commander goes in the command zone

        card_info = oracle_db.get(name_lower)
        if not card_info:
            continue

        card_identity = set(card_info.get("color_identity", []))
        if not card_identity.issubset(comm_identity):
            continue

        valid_pool.append(card_info)

    # Pre-score all cards using the Spice Weighting algorithm
    pool_scored = []
    card_spice_data = {}
    for card in valid_pool:
        score, deep_cut = calculate_spice_score(card, commander, comm_keywords, obscurity_db, target_ix)
        pool_scored.append((card, score))
        card_spice_data[card["name"].lower()] = (score, deep_cut)

    # Sort all cards by spice score (descending) and then cmc (ascending)
    pool_scored.sort(key=lambda x: (-x[1], x[0].get("cmc", 0)))

    # Allocate lands
    lands = [item for item in pool_scored if is_land(item[0])]
    non_lands = [item for item in pool_scored if not is_land(item[0])]

    # Deduplicate allocations based on count instances
    remaining_inventory = defaultdict(int)
    for name in collection_cards:
        remaining_inventory[name.lower()] += 1
    remaining_inventory[comm_lower] = 0

    def take_candidate(pool, condition_fn, count_needed):
        allocated = []
        for card, score in pool:
            if len(allocated) >= count_needed:
                break
            card_name = card["name"].lower()
            if remaining_inventory[card_name] > 0 and condition_fn(card):
                allocated.append(card)
                remaining_inventory[card_name] -= 1
        return allocated

    # 1. Lands
    lands.sort(key=lambda x: (
        -len(set(x[0].get("color_identity", [])).intersection(comm_identity)),
        x[0]["name"]
    ))
    selected_lands = []
    for card, _ in lands:
        if len(selected_lands) >= target_lands:
            break
        card_name = card["name"].lower()
        if remaining_inventory[card_name] > 0:
            selected_lands.append(card)
            remaining_inventory[card_name] -= 1

    # 2. Ramp
    selected_ramp = take_candidate(non_lands, is_ramp, target_ramp)

    # 3. Draw
    selected_draw = take_candidate(non_lands, is_draw, target_draw)

    # 4. Removal
    selected_removal = take_candidate(non_lands, is_removal, target_removal)

    # 5. Synergy
    selected_synergy = []
    for card, _ in non_lands:
        if len(selected_synergy) >= target_synergy:
            break
        card_name = card["name"].lower()
        if remaining_inventory[card_name] > 0:
            selected_synergy.append(card)
            remaining_inventory[card_name] -= 1

    # Fill backfill slots if any category was underfilled
    total_spells = len(selected_ramp) + len(selected_draw) + len(selected_removal) + len(selected_synergy)
    needed_spells = (99 - target_lands)
    
    if total_spells < needed_spells:
        for card, _ in non_lands:
            if total_spells >= needed_spells:
                break
            card_name = card["name"].lower()
            if remaining_inventory[card_name] > 0:
                selected_synergy.append(card)
                remaining_inventory[card_name] -= 1
                total_spells += 1

    # Calculate overall deck spice score
    all_non_lands = selected_ramp + selected_draw + selected_removal + selected_synergy
    total_spice = 0.0
    for card in all_non_lands:
        score, _ = card_spice_data[card["name"].lower()]
        total_spice += score
    avg_spice = (total_spice / len(all_non_lands)) if all_non_lands else 0.0

    # --- ADVANCED ENGINE METRICS ---
    # 1. Fragility Indexing
    non_land_permanents = [card for card in all_non_lands if not is_land(card) and calculate_fragility_weight(card) > 0.0]
    total_fragility = sum(calculate_fragility_weight(card) for card in non_land_permanents)
    avg_fragility = (total_fragility / len(non_land_permanents)) if non_land_permanents else 0.0
    
    # Scan for protection
    protection_spells = [card for card in all_non_lands if is_protection(card)]
    adjusted_fragility = avg_fragility - (len(protection_spells) * 0.05)
    
    if adjusted_fragility >= 0.6:
        fragility_rating = "High Fragility"
    elif adjusted_fragility >= 0.35:
        fragility_rating = "Medium Fragility"
    else:
        fragility_rating = "Low Fragility"

    # 2. Multiplayer Table-Pressure
    scaling_spells = [card for card in all_non_lands if is_multiplayer_scaling(card)]
    table_pressure_score = min(len(scaling_spells) * 10, 100)

    # 3. Hypergeometric Draw Consistency
    K_lands = len(selected_lands)
    K_ramp = len(selected_ramp)
    K_draw = len(selected_draw)
    
    joint_prob = calculate_joint_consistency(99, 13, K_lands, 3, K_ramp, 1, K_draw, 1)
    
    if joint_prob >= 0.70:
        consistency_rating = "High Consistency"
    elif joint_prob >= 0.50:
        consistency_rating = "Medium Consistency"
    else:
        consistency_rating = "Low Consistency"

    # --- INTENTIONAL EXPERIENCE (IX) METRICS ---
    # 1. Bracket Check
    bracket_level = intent_profile.get("bracket_level", 2)
    deck_card_names = {c["name"].lower() for c in all_non_lands}
    
    fast_mana_found = FAST_MANA_CARDS.intersection(deck_card_names)
    tutors_found = HIGH_EFFICIENCY_TUTORS.intersection(deck_card_names)
    
    bracket_warnings = []
    
    # Spell Average CMC calculation
    spells_cmc = sum(c.get("cmc", 0) for c in all_non_lands)
    avg_cmc = (spells_cmc / len(all_non_lands)) if all_non_lands else 0.0

    if bracket_level in (1, 2):
        if fast_mana_found:
            bracket_warnings.append(f"[!] Warning: Fast mana ({', '.join(sorted(list(fast_mana_found)))}) detected in low power Bracket {bracket_level}.")
        if tutors_found:
            bracket_warnings.append(f"[!] Warning: High efficiency tutors ({', '.join(sorted(list(tutors_found)))}) detected in low power Bracket {bracket_level}.")
    elif bracket_level == 4:
        if avg_cmc > 2.2:
            bracket_warnings.append(f"[!] Warning: Spell Average CMC is high ({avg_cmc:.2f}) for Bracket 4 (cEDH target < 2.2).")
        if not fast_mana_found and not tutors_found:
            bracket_warnings.append("[!] Warning: No fast mana or tutors found; deck is too slow for Bracket 4 (cEDH).")

    # 2. Win-Condition Auditor
    win_cons_needed = intent_profile.get("win_cons_needed", 3)
    finishers_found = [c for c in all_non_lands if bool(FINISHER_REGEX.search(c.get("oracle_text", "")))]
    
    win_con_warnings = []
    if len(finishers_found) < win_cons_needed:
        win_con_warnings.append(f"[!] Warning: Low Win-Condition Density (only {len(finishers_found)}/{win_cons_needed} finishers detected). Risk of becoming a 'Value-Pile'.")

    return {
        "commander": commander,
        "keywords": comm_keywords,
        "lands": selected_lands,
        "ramp": selected_ramp,
        "draw": selected_draw,
        "removal": selected_removal,
        "synergy": selected_synergy,
        "spice_data": card_spice_data,
        "average_spice": avg_spice,
        
        # Analytics payload
        "avg_fragility": avg_fragility,
        "protection_count": len(protection_spells),
        "adjusted_fragility": adjusted_fragility,
        "fragility_rating": fragility_rating,
        "table_pressure_score": table_pressure_score,
        "scaling_spells": scaling_spells,
        "joint_prob": joint_prob,
        "consistency_rating": consistency_rating,
        
        # IX payload
        "intent_profile": intent_profile,
        "bracket_warnings": bracket_warnings,
        "win_con_warnings": win_con_warnings,
        "finishers": finishers_found,
        "avg_cmc": avg_cmc
    }


# --- THEMATIC ENGINE FUNCTIONS (Layer 4) ---

MECHANICAL_THEMES = {
    "Landfall / Lands": [r"landfall", r"whenever a land enters", r"play an additional land"],
    "Sacrifice / Aristocrats": [r"sacrifice a", r"whenever a.*dies", r"die, you", r"aristocrat"],
    "Graveyard / Reanimator": [r"graveyard", r"return.*from your graveyard", r"reanimate", r"dredge", r"undergrowth"],
    "Blink / Flicker": [r"exile.*then return.*to the battlefield", r"flicker", r"blink", r"enters the battlefield again"],
    "Tokens": [r"create.*token", r"populate", r"amass"],
    "Counters (+1/+1 / Proliferate)": [r"\+1/\+1 counter", r"proliferate", r"doubling season", r"hardened scales"],
    "Spellslinger": [r"whenever you cast an instant or sorcery", r"instant or sorcery spell", r"magecraft"],
    "Artifacts / Voltron": [r"artifact", r"equip", r"enchant creature", r"aura", r"vehicles"],
    "Lifegain": [r"gain life", r"whenever you gain life", r"lifelink"],
    "Discard / Madness": [r"discard", r"cycling", r"madness"],
    "Planeswalkers / Superfriends": [r"\bplaneswalker\b", r"\bloyalty\b"]
}

MECHANICAL_REGEXES = {
    theme: re.compile("|".join(patterns), re.IGNORECASE)
    for theme, patterns in MECHANICAL_THEMES.items()
}

SET_TO_PLANE = {
    # Innistrad (Gothic horror, vampires, werewolves)
    "isd": "Innistrad", "dka": "Innistrad", "avr": "Innistrad", "soi": "Innistrad", "emn": "Innistrad", "mid": "Innistrad", "vow": "Innistrad",
    # Kamigawa (Cyberpunk / Traditional Japanese)
    "chk": "Kamigawa", "bok": "Kamigawa", "sok": "Kamigawa", "neo": "Kamigawa",
    # Ravnica (Guild metropolis)
    "rav": "Ravnica", "gpt": "Ravnica", "dis": "Ravnica", "rtr": "Ravnica", "gtc": "Ravnica", "dgm": "Ravnica", "grn": "Ravnica", "rna": "Ravnica", "war": "Ravnica", "mkm": "Ravnica",
    # Mirrodin / New Phyrexia (Metal world)
    "mrd": "Mirrodin", "dst": "Mirrodin", "5dn": "Mirrodin", "som": "Mirrodin", "mbs": "Mirrodin", "nph": "Mirrodin", "one": "Mirrodin",
    # Zendikar (Adventure, elements, lands)
    "zen": "Zendikar", "wwk": "Zendikar", "roe": "Zendikar", "bfz": "Zendikar", "ogw": "Zendikar", "znr": "Zendikar",
    # Dominaria (High fantasy, history)
    "dom": "Dominaria", "dmu": "Dominaria", "bro": "Dominaria",
    # Theros (Greek myth, enchantments)
    "ths": "Theros", "bng": "Theros", "jou": "Theros", "thb": "Theros",
    # Eldraine (Fairy tales, knights)
    "eld": "Eldraine", "woe": "Eldraine",
    # Ixalan (Dinosaurs, Mesoamerican, pirates)
    "xln": "Ixalan", "rix": "Ixalan", "lci": "Ixalan"
}

PLANE_CLASHES = {
    "Kamigawa": {"Innistrad", "Eldraine", "Theros"},
    "Innistrad": {"Kamigawa", "Kaladesh"},
    "Eldraine": {"Kamigawa", "Mirrodin"},
    "Mirrodin": {"Eldraine", "Theros", "Ixalan"},
    "Theros": {"Kamigawa", "Mirrodin"},
    "Ixalan": {"Mirrodin", "Kamigawa"}
}

def scan_mechanical_keywords(card_info: dict) -> list[str]:
    """Scan card's oracle text and types to identify matching mechanical themes."""
    matched_themes = []
    text = card_info.get("oracle_text", "")
    type_line = card_info.get("type_line", "")
    
    # Check type line for simple theme matches (e.g., 'Artifact' type)
    for theme, regex in MECHANICAL_REGEXES.items():
        if regex.search(text) or regex.search(type_line):
            matched_themes.append(theme)
            
    return matched_themes

def calculate_cohesion_score(deck_names: list, db: dict) -> dict:
    """
    Calculate the Theme Cohesion Score (0-100) based on creature subtypes
    and mechanical keywords.
    """
    spells_count = 0
    creatures_count = 0
    subtype_counts = defaultdict(int)
    theme_counts = defaultdict(int)
    
    for name in deck_names:
        card_info = db.get(name.lower())
        if not card_info:
            continue
        
        # We only look at non-land spells for mechanical cohesion
        raw_type = card_info.get("raw_type", "").lower()
        if "land" in raw_type and "creature" not in raw_type:
            continue
            
        spells_count += 1
        
        # Subtype counts
        if "creature" in raw_type:
            creatures_count += 1
            for sub in card_info.get("subtypes", []):
                subtype_counts[sub] += 1
                
        # Mechanical themes counts
        matched = scan_mechanical_keywords(card_info)
        for theme in matched:
            theme_counts[theme] += 1
            
    # Find dominant subtype (creature type) density
    max_subtype_count = max(subtype_counts.values()) if subtype_counts else 0
    dominant_subtype = max(subtype_counts, key=subtype_counts.get) if subtype_counts else "None"
    subtype_density = (max_subtype_count / creatures_count) * 100 if creatures_count > 0 else 0
    
    # Find dominant mechanical theme density
    max_theme_count = max(theme_counts.values()) if theme_counts else 0
    dominant_theme = max(theme_counts, key=theme_counts.get) if theme_counts else "None"
    theme_density = (max_theme_count / spells_count) * 100 if spells_count > 0 else 0
    
    # Cohesion formula:
    # Blend dominant creature type density (weighted 40%) and mechanical theme density (weighted 60%)
    # If the deck has few creatures (e.g. spellslinger), we rely entirely on the mechanical theme density.
    if creatures_count < 10:
        cohesion_score = min(100, theme_density * 1.5)
    else:
        cohesion_score = min(100, (subtype_density * 0.4) + (theme_density * 0.9))
        
    return {
        "cohesion_score": int(cohesion_score),
        "dominant_subtype": dominant_subtype,
        "subtype_density": int(subtype_density),
        "dominant_theme": dominant_theme,
        "theme_density": int(theme_density),
        "subtype_counts": dict(sorted(subtype_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
        "theme_counts": dict(sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:5])
    }

def analyze_flavor_clashes(deck_names: list, db: dict) -> dict:
    """
    Analyze the deck for Vorthos flavor clashes based on sets/planes of origin.
    """
    plane_counts = defaultdict(int)
    card_planes = {}
    
    for name in deck_names:
        card_info = db.get(name.lower())
        if not card_info:
            continue
            
        set_code = card_info.get("set", "").lower()
        plane = SET_TO_PLANE.get(set_code)
        if plane:
            plane_counts[plane] += 1
            card_planes[card_info["name"]] = plane
            
    if not plane_counts:
        return {"dominant_plane": "Unknown", "dominant_plane_count": 0, "clashing_cards": []}
        
    dominant_plane = max(plane_counts, key=plane_counts.get)
    dominant_plane_count = plane_counts[dominant_plane]
    
    clashing_cards = []
    # We only run clash warning if the deck has a strong plane thematic presence (>= 8 cards from dominant plane)
    if dominant_plane_count >= 8:
        forbidden_planes = PLANE_CLASHES.get(dominant_plane, set())
        for card_name, plane in card_planes.items():
            if plane in forbidden_planes:
                clashing_cards.append({
                    "card": card_name,
                    "card_plane": plane,
                    "dominant_plane": dominant_plane
                })
                
    return {
        "dominant_plane": dominant_plane,
        "dominant_plane_count": dominant_plane_count,
        "plane_counts": dict(plane_counts),
        "clashing_cards": clashing_cards
    }


def main():
    parser = argparse.ArgumentParser(description="Generate an objective MTG Commander deck from your tagged collection.")
    parser.add_argument("--commander", required=True, help="Name of the commander to build around")
    parser.add_argument("--collection", default="data/collection_tagged_bulk.csv", help="Path to tagged collection CSV")
    parser.add_argument("--oracle", default="scripts/oracle-cards.json", help="Path to Scryfall oracle cards JSON")
    parser.add_argument("--intent", default="data/intent_profile.json", help="Path to Intent Profile JSON config")
    parser.add_argument("--output", help="Optional path to output the generated deck list")
    
    args = parser.parse_args()

    collection_path = Path(args.collection)
    oracle_path = Path(args.oracle)
    intent_path = Path(args.intent)

    if not collection_path.exists():
        print(f"Error: Collection file does not exist: {collection_path}")
        sys.exit(1)
    if not oracle_path.exists():
        print(f"Error: Oracle DB file does not exist: {oracle_path}")
        sys.exit(1)

    print("Loading databases...")
    oracle_db = load_oracle_database(oracle_path)
    collection = load_collection(collection_path)
    intent_profile = load_intent_profile(intent_path)

    print(f"Loaded {len(oracle_db)} cards from Oracle DB.")
    print(f"Loaded {len(collection)} owned cards from Collection.")
    print(f"Loaded Intent Profile: {intent_profile.get('target_ix', 'None')} (Bracket {intent_profile.get('bracket_level', 2)}).")

    try:
        deck = generate_deck(args.commander, collection, oracle_db, intent_profile)
    except ValueError as e:
        print(e)
        sys.exit(1)

    # Output formatting
    report = []
    report.append("==================================================")
    report.append(f" COMMANDER: {deck['commander']['name']}")
    report.append(f" Color Identity: {', '.join(deck['commander']['color_identity'])}")
    report.append(f" Detected Keywords: {', '.join(deck['keywords'])}")
    report.append("==================================================")

    categories = [
        ("Lands", deck["lands"]),
        ("Ramp Spells", deck["ramp"]),
        ("Draw Spells", deck["draw"]),
        ("Removal / Interaction", deck["removal"]),
        ("Thematic Synergy / Core", deck["synergy"])
    ]

    total_cards = 0
    all_non_lands_instances = []

    for title, card_list in categories:
        report.append(f"\n## {title} ({len(card_list)})")
        counts = defaultdict(int)
        for c in card_list:
            counts[c["name"]] += 1
            total_cards += 1
            if title != "Lands":
                all_non_lands_instances.append(c)
        
        for name, count in sorted(counts.items()):
            qty_str = f"{count}x" if count > 1 else "1 "
            report.append(f"  {qty_str} {name}")

    # Spice analysis results
    report.append("\n==================================================")
    report.append(" SPICE ANALYSIS REPORT")
    report.append("==================================================")
    report.append(f" Overall Deck Spice Score: {deck['average_spice']:.2f}")
    
    unique_non_lands = {}
    for card in all_non_lands_instances:
        name_lower = card["name"].lower()
        if name_lower not in unique_non_lands:
            score, deep_cut = deck["spice_data"][name_lower]
            unique_non_lands[name_lower] = (card["name"], score, deep_cut)
            
    sorted_unique_spices = sorted(unique_non_lands.values(), key=lambda x: x[1], reverse=True)
    
    report.append("\n## Top 5 Spiciest Cuts:")
    for name, score, deep_cut in sorted_unique_spices[:5]:
        deep_cut_tag = " [Deep Cut Overlap]" if deep_cut else ""
        report.append(f"  * {name} (Spice Score: {score:.2f}){deep_cut_tag}")

    # Advanced Analysis results
    report.append("\n==================================================")
    report.append(" ADVANCED ENGINE ANALYSIS")
    report.append("==================================================")
    report.append("## 1. Fragility Indexing")
    report.append(f"   * Average Permanent Fragility: {deck['avg_fragility']:.2f}")
    report.append(f"   * Protection Spells Detected: {deck['protection_count']}")
    report.append(f"   * Adjusted Fragility Score: {deck['adjusted_fragility']:.2f}")
    report.append(f"   * Fragility Rating: {deck['fragility_rating']}")
    if deck['fragility_rating'] == "High Fragility":
        report.append("     [!] WARNING: Core engine relies on vulnerable permanent types. Consider adding protection.")
        
    report.append("\n## 2. Multiplayer Table-Pressure")
    report.append(f"   * Table-Pressure Score: {deck['table_pressure_score']} / 100")
    if deck['scaling_spells']:
        report.append("   * Scaling Cards:")
        unique_scaling = sorted(list(set(c["name"] for c in deck["scaling_spells"])))
        for name in unique_scaling:
            report.append(f"     - {name}")
            
    report.append("\n## 3. Structural Engine Consistency")
    report.append(f"   * Joint Draw Probability (Turn 6): {deck['joint_prob'] * 100:.1f}%")
    report.append(f"   * Consistency Rating: {deck['consistency_rating']}")

    # Intentional Experience (IX) results
    report.append("\n==================================================")
    report.append(" INTENTIONAL EXPERIENCE (IX) REPORT")
    report.append("==================================================")
    report.append(f"## Target Playstyle (IX): {deck['intent_profile']['target_ix']}")
    report.append(f"   * Target Bracket: Bracket {deck['intent_profile']['bracket_level']}")
    
    report.append("\n## Power-Level Calibration")
    if deck['bracket_warnings']:
        for warning in deck['bracket_warnings']:
            report.append(f"   {warning}")
    else:
        report.append("   * Status: Calibrated (No bracket anomalies found)")
        
    report.append("\n## Win-Condition Auditor")
    report.append(f"   * Finishers Found: {len(deck['finishers'])} (Required: {deck['intent_profile']['win_cons_needed']})")
    if deck['finishers']:
        report.append("   * Finishers:")
        unique_finishers = sorted(list(set(c["name"] for c in deck['finishers'])))
        for name in unique_finishers:
            report.append(f"     - {name}")
            
    if deck['win_con_warnings']:
        for warning in deck['win_con_warnings']:
            report.append(f"   {warning}")
    else:
        report.append("   * Status: Balanced Win-Condition Density")

    report.append("\n==================================================")
    report.append(f" TOTAL CARDS: {total_cards + 1} (1 Commander + {total_cards} Deck)")
    report.append(f" Average CMC of Spells: {deck['avg_cmc']:.2f}")
    report.append("==================================================")

    output_str = "\n".join(report)
    print(output_str)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_str, encoding="utf-8")
        print(f"\nDeck report written to {out_path}")


if __name__ == "__main__":
    main()
