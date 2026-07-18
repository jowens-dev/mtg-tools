#!/usr/bin/env python3
"""Flavor parsing engine and Vorthos Clash Analyzer for Magic: The Gathering cards."""

import re

# --- SET CODE TO PLANE MAPPINGS ---
SET_PLANE_MAP = {
    # Innistrad (Gothic Horror)
    "isd": "Innistrad", "dka": "Innistrad", "avr": "Innistrad",
    "soi": "Innistrad", "emn": "Innistrad", "mid": "Innistrad",
    "vow": "Innistrad", "sis": "Innistrad",
    
    # Kamigawa (Cyberpunk / Feudal)
    "chk": "Kamigawa", "bok": "Kamigawa", "sok": "Kamigawa",
    "neo": "Kamigawa",
    
    # Ravnica (Guild City)
    "rav": "Ravnica", "gpt": "Ravnica", "dis": "Ravnica",
    "rtr": "Ravnica", "gtc": "Ravnica", "dgm": "Ravnica",
    "grn": "Ravnica", "rna": "Ravnica", "war": "Ravnica",
    "mkm": "Ravnica", "rvr": "Ravnica",
    
    # Mirrodin / New Phyrexia (Metal/Bio-mechanical)
    "mrd": "Mirrodin", "dst": "Mirrodin", "5dn": "Mirrodin",
    "som": "Mirrodin", "mbs": "Mirrodin", "nph": "Mirrodin",
    "one": "Mirrodin", "mom": "Mirrodin",
    
    # Zendikar (Adventure/Eldrazi)
    "zen": "Zendikar", "wwk": "Zendikar", "roe": "Zendikar",
    "bfz": "Zendikar", "ogw": "Zendikar", "znr": "Zendikar",
    
    # Tarkir (Warlords/Dragons)
    "ktk": "Tarkir", "frf": "Tarkir", "dtk": "Tarkir",
    
    # Theros (Greek Myth)
    "ths": "Theros", "bng": "Theros", "jou": "Theros",
    "thb": "Theros",
    
    # Kaladesh (Aetherpunk/Sci-Fi)
    "kld": "Kaladesh", "aer": "Kaladesh",
    
    # Amonkhet (Egyptian Myth)
    "akh": "Amonkhet", "hou": "Amonkhet",
    
    # Ixalan (Dinosaurs/Pirates/Mesoamerican)
    "xln": "Ixalan", "rix": "Ixalan", "lci": "Ixalan",
    
    # Eldraine (Fairy Tale/Camelot)
    "eld": "Eldraine", "woe": "Eldraine",
    
    # Capenna (1920s Art Deco Mobsters)
    "snc": "Capenna",
    
    # Dominaria (Classic High Fantasy)
    "dom": "Dominaria", "dmu": "Dominaria", "bro": "Dominaria",
    "ice": "Dominaria", "all": "Dominaria", "csp": "Dominaria",
    "usg": "Dominaria", "ulg": "Dominaria", "uds": "Dominaria",
    "inv": "Dominaria", "apc": "Dominaria", "pls": "Dominaria",
    "ody": "Dominaria", "tor": "Dominaria", "jud": "Dominaria",
    "ons": "Dominaria", "lgn": "Dominaria", "scg": "Dominaria",
    "tsp": "Dominaria", "plc": "Dominaria", "fut": "Dominaria"
}

# --- KEYWORD LORE TO PLANE MAPPINGS ---
LORE_KEYWORDS = {
    "Innistrad": [
        "markov", "falkenrath", "voldaren", "stromkirk", "thraben", "ulrich",
        "thalia", "gisa", "gerald", "avacyn", "sigarda", "brunela", "gisela",
        "ludevic", "runo", "edgar", "geist", "nephalia", "gavony", "kessig",
        "stensia", "halana", "alena", "odric"
    ],
    "Kamigawa": [
        "umezawa", "konda", "toshiro", "o-kagachi", "kyodai", "hidetsugu",
        "michiko", "chishiro", "kotose", "neon", "jukai", "futurist", "boseiju",
        "towashi", "yamazaki", "nashi", "imperial palace"
    ],
    "Ravnica": [
        "boros", "dimir", "selesnya", "golgari", "izzet", "gruul", "orzhov",
        "simic", "azorius", "rakdos", "niv-mizzet", "teysa", "lasav", "szadek",
        "karlov", "ruric", "feather", "isperia", "obzedat", "vitu-ghazi",
        "pizzic", "lavinia", "lazav", "guild"
    ],
    "Mirrodin": [
        "phyrexia", "mirrodin", "karn", "glissa", "elesh norn", "jin-gitaxias",
        "sheoldred", "urabrask", "vorinclex", "yawgmoth", "melira", "ezuri",
        "koth", "memnarch", "ichor", "compleat", "panharmonicon", "tangle"
    ],
    "Zendikar": [
        "roil", "hedron", "tazri", "anowon", "nahiri", "kiora", "nissa",
        "drana", "kozilek", "ulamog", "emrakul", "eldrazi", "bala ged",
        "tazeem", "ondure", "guul draz", "akoum", "murasa"
    ],
    "Tarkir": [
        "abzan", "jeskai", "sultai", "mardu", "temur", "zurgo", "narset",
        "sidisi", "anfenza", "surrak", "sarkhan", "silumgar", "kolaghan",
        "atarka", "dromoka", "ojutai", "khan", "ojutai", "clan"
    ],
    "Theros": [
        "heliod", "thassa", "erebos", "purphoros", "nylea", "elspeth",
        "xenagos", "ajani", "ashiok", "daxos", "anax", "tymaret", "akros",
        "meletis", "setessa", "nyx", "eidolon", "underworld"
    ],
    "Kaladesh": [
        "consulate", "aetherworks", "ghirapur", "rashmi", "saheeli", "depala",
        "kari zev", "baral", "renegade", "aetherflux", "peema"
    ],
    "Amonkhet": [
        "hazoret", "oketra", "kefnet", "bontu", "locust god", "scarab god",
        "scorpion god", "samut", "djeru", "temmet", "bolas", "heckma"
    ],
    "Ixalan": [
        "huatli", "angrath", "tishana", "vona", "gishath", "kumena", "zacama",
        "sun empire", "river heralds", "dusk legion", "brazen coalition",
        "adanto", "torrezon", "chupacabra"
    ],
    "Eldraine": [
        "kenrith", "garruk", "rowan", "will", "syr konrad", "syr gwyn",
        "ayara", "yorvo", "linden", "chulane", "locthwain", "ardenvale",
        "vantress", "embereth", "garenbrig"
    ],
    "Capenna": [
        "obscura", "maestros", "riveteers", "cabaretti", "brokers", "xander",
        "ziatora", "falco", "jetmir", "raffine", "halo", "capenna", "crescendo"
    ],
    "Dominaria": [
        "jodah", "teferi", "multani", "urza", "mishra", "barrin", "gerrard",
        "sisay", "crovax", "squee", "radha", "shanna", "jaria", "llanowar",
        "keld", "benalia", "tolaria", "zhalfir", "urborg", "yavimaya"
    ]
}

# --- AESTHETIC CLASSIFICATIONS ---
AESTHETIC_TYPES = {
    # Modern / Futuristic / Industrial Settings
    "Kamigawa": "Cyberpunk/Futuristic",
    "Capenna": "Art Deco/1920s Industrial",
    "Kaladesh": "Aetherpunk/Steampunk",
    "Mirrodin": "Bio-mechanical/Phyrexian",
    
    # Traditional / Mythic / Medieval Settings
    "Innistrad": "Gothic Horror",
    "Theros": "Ancient Mythic",
    "Amonkhet": "Ancient Mythic",
    "Eldraine": "Fairy Tale Fantasy",
    "Ixalan": "Mesoamerican Fantasy",
    "Tarkir": "Warlord Fantasy",
    
    # Classic High Fantasy Settings (generally neutral/broad compatibility)
    "Dominaria": "Classic High Fantasy",
    "Ravnica": "Classic High Fantasy",
    "Zendikar": "Classic High Fantasy"
}


def resolve_card_plane(card: dict) -> str | None:
    """Resolve the plane of a card by checking set mapping or lore keywords in text/name."""
    # 1. Check printing set code (direct mapping)
    set_code = card.get("set", "").lower()
    if set_code in SET_PLANE_MAP:
        return SET_PLANE_MAP[set_code]

    # 2. Check name and flavor text for lore associations
    name_lower = card.get("name", "").lower()
    flavor_lower = card.get("flavor_text", "").lower()
    oracle_lower = card.get("oracle_text", "").lower()

    for plane, keywords in LORE_KEYWORDS.items():
        for kw in keywords:
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, name_lower) or re.search(pattern, flavor_lower) or re.search(pattern, oracle_lower):
                return plane

    return None


def check_aesthetic_clash(commander_plane: str | None, card_plane: str | None) -> tuple[bool, str]:
    """Check if the card plane is a stark aesthetic clash with the commander plane."""
    if not commander_plane or not card_plane or commander_plane == card_plane:
        return False, ""

    comm_aesthetic = AESTHETIC_TYPES.get(commander_plane)
    card_aesthetic = AESTHETIC_TYPES.get(card_plane)

    if not comm_aesthetic or not card_aesthetic:
        return False, ""

    # Contrast matrix rules:
    # Futuristic/Industrial settings clash with traditional/historical settings
    modern_styles = {"Cyberpunk/Futuristic", "Art Deco/1920s Industrial", "Aetherpunk/Steampunk"}
    traditional_styles = {"Gothic Horror", "Ancient Mythic", "Fairy Tale Fantasy", "Mesoamerican Fantasy", "Warlord Fantasy"}

    if comm_aesthetic in traditional_styles and card_aesthetic in modern_styles:
        return True, f"Aesthetic Clash: '{card_aesthetic}' card in '{comm_aesthetic}' deck."
    if comm_aesthetic in modern_styles and card_aesthetic in traditional_styles:
        return True, f"Aesthetic Clash: '{card_aesthetic}' card in '{comm_aesthetic}' deck."

    return False, ""
