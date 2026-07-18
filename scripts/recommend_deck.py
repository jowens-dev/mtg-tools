#!/usr/bin/env python3
"""Recommend a rules-based, objective 99-card Commander deck list from an owned collection, including flavor/Vorthos alignment analysis."""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Import flavor engine functions
from flavor_engine import resolve_card_plane, check_aesthetic_clash

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


def load_oracle_database(filepath: Path) -> dict:
    """Load Scryfall oracle cards from a JSON file into a name-keyed lookup dictionary."""
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

    for card in raw_data:
        name = card.get("name", "")
        if not name:
            continue

        name_lower = name.lower()
        color_identity = card.get("color_identity", [])
        cmc = card.get("cmc", 0.0)
        set_code = card.get("set", "")
        flavor_text = card.get("flavor_text", "")

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
            "flavor_text": flavor_text or ""
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
        # Match word boundaries or general containment
        score += len(re.findall(rf"\b{re.escape(kw)}\b", text_lower))
        if kw in type_lower:
            score += 1

    return score


def generate_deck(
    commander_name: str,
    collection_cards: list[str],
    oracle_db: dict,
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

    # Filter collection to valid card identities & map to oracle records
    valid_pool = []
    seen = defaultdict(int)

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

    pool_scored = []
    for card in valid_pool:
        score = calculate_synergy_score(card, comm_keywords)
        pool_scored.append((card, score))

    # Sort all non-lands by synergy score (descending) and then cmc (ascending)
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

    # --- FLAVOR & VORTHOS ANALYSIS ---
    comm_plane = resolve_card_plane(commander)
    clashes = []
    spells_with_planes = 0
    spells_matching_plane = 0

    all_non_lands = selected_ramp + selected_draw + selected_removal + selected_synergy
    for card in all_non_lands:
        card_plane = resolve_card_plane(card)
        if card_plane:
            spells_with_planes += 1
            if comm_plane and card_plane == comm_plane:
                spells_matching_plane += 1
            
            # Check for aesthetic clashes
            clash, msg = check_aesthetic_clash(comm_plane, card_plane)
            if clash:
                clashes.append((card["name"], card_plane, msg))

    cohesion_score = None
    if comm_plane and spells_with_planes > 0:
        cohesion_score = (spells_matching_plane / spells_with_planes) * 100.0

    return {
        "commander": commander,
        "commander_plane": comm_plane,
        "keywords": comm_keywords,
        "lands": selected_lands,
        "ramp": selected_ramp,
        "draw": selected_draw,
        "removal": selected_removal,
        "synergy": selected_synergy,
        "cohesion_score": cohesion_score,
        "clashes": clashes
    }


def main():
    parser = argparse.ArgumentParser(description="Generate an objective MTG Commander deck from your tagged collection.")
    parser.add_argument("--commander", required=True, help="Name of the commander to build around")
    parser.add_argument("--collection", default="data/collection_tagged_bulk.csv", help="Path to tagged collection CSV")
    parser.add_argument("--oracle", default="scripts/oracle-cards.json", help="Path to Scryfall oracle cards JSON")
    parser.add_argument("--output", help="Optional path to output the generated deck list")
    
    args = parser.parse_args()

    collection_path = Path(args.collection)
    oracle_path = Path(args.oracle)

    if not collection_path.exists():
        print(f"Error: Collection file does not exist: {collection_path}")
        sys.exit(1)
    if not oracle_path.exists():
        print(f"Error: Oracle DB file does not exist: {oracle_path}")
        sys.exit(1)

    print("Loading databases...")
    oracle_db = load_oracle_database(oracle_path)
    collection = load_collection(collection_path)

    print(f"Loaded {len(oracle_db)} cards from Oracle DB.")
    print(f"Loaded {len(collection)} owned cards from Collection.")

    try:
        deck = generate_deck(args.commander, collection, oracle_db)
    except ValueError as e:
        print(e)
        sys.exit(1)

    # Output formatting
    report = []
    report.append("==================================================")
    report.append(f" COMMANDER: {deck['commander']['name']}")
    report.append(f" Color Identity: {', '.join(deck['commander']['color_identity'])}")
    report.append(f" Detected Keywords: {', '.join(deck['keywords'])}")
    
    # Flavor mapping info
    comm_plane_str = deck['commander_plane'] if deck['commander_plane'] else "Unknown / Generic"
    report.append(f" Home Plane/Setting: {comm_plane_str}")
    report.append("==================================================")

    categories = [
        ("Lands", deck["lands"]),
        ("Ramp Spells", deck["ramp"]),
        ("Draw Spells", deck["draw"]),
        ("Removal / Interaction", deck["removal"]),
        ("Thematic Synergy / Core", deck["synergy"])
    ]

    total_cards = 0
    spells_cmc = 0
    spells_count = 0

    for title, card_list in categories:
        report.append(f"\n## {title} ({len(card_list)})")
        counts = defaultdict(int)
        for c in card_list:
            counts[c["name"]] += 1
            total_cards += 1
            if title != "Lands":
                spells_cmc += c.get("cmc", 0)
                spells_count += 1
        
        for name, count in sorted(counts.items()):
            qty_str = f"{count}x" if count > 1 else "1 "
            report.append(f"  {qty_str} {name}")

    # Flavor evaluation results
    report.append("\n==================================================")
    report.append(" VORTHOS FLAVOR & COHESION ANALYSIS")
    report.append("==================================================")
    if deck["cohesion_score"] is not None:
        report.append(f" Flavor Cohesion Score: {deck['cohesion_score']:.1f}%")
    else:
        report.append(" Flavor Cohesion Score: N/A (Commander's Plane Unknown)")

    if deck["clashes"]:
        report.append(f"\n[!] Vorthos Clashes Detected ({len(deck['clashes'])}):")
        for card_name, plane, msg in deck["clashes"]:
            report.append(f"  * {card_name} ({plane}) -> {msg}")
    else:
        report.append("\n[x] No Vorthos aesthetic clashes detected.")

    avg_cmc = (spells_cmc / spells_count) if spells_count > 0 else 0.0
    report.append("\n==================================================")
    report.append(f" TOTAL CARDS: {total_cards + 1} (1 Commander + {total_cards} Deck)")
    report.append(f" Average CMC of Spells: {avg_cmc:.2f}")
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
