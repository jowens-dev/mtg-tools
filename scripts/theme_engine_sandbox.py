# Mocking the data we now have stored in self.oracle_db
mock_deck = [
    "edgar markov", "vampire nighthawk", "sol ring", 
    "blasphemous act", "blood artist", "counterspell"
]

mock_db = {
    "edgar markov": {"types": ["Creature", "Vampire", "Knight"], "is_legendary": True},
    "vampire nighthawk": {"types": ["Creature", "Vampire", "Shaman"], "is_legendary": False},
    "sol ring": {"types": ["Artifact"], "is_legendary": False},
    "blasphemous act": {"types": ["Sorcery"], "is_legendary": False},
    "blood artist": {"types": ["Creature", "Vampire"], "is_legendary": False},
    "counterspell": {"types": ["Instant"], "is_legendary": False}
}

def cluster_deck_by_type(deck_list: list, db: dict) -> dict:
    clusters = {}
    for card_name in deck_list:
        card_data = db.get(card_name)
        if not card_data:
            continue
            
        for card_type in card_data["types"]:
            if card_type not in clusters:
                clusters[card_type] = []
            clusters[card_type].append(card_name)
            
    return clusters

print("--- Testing Theme Clustering ---")
deck_clusters = cluster_deck_by_type(mock_deck, mock_db)

# Sort by the most common types
sorted_types = sorted(deck_clusters.items(), key=lambda item: len(item[1]), reverse=True)

for card_type, cards in sorted_types:
    print(f"{card_type} ({len(cards)}): {', '.join([c.title() for c in cards])}")
