# Mocking a tiny slice of the Scryfall Oracle DB structure
mock_oracle_db = {
    "lightning bolt": {"mana_cost": "{R}", "colors": ["R"]},
    "counterspell": {"mana_cost": "{U}{U}", "colors": ["U"]},
    "edgar markov": {"mana_cost": "{3}{R}{W}{B}", "colors": ["R", "W", "B"]},
    "sol ring": {"mana_cost": "{1}", "colors": []} 
}

def get_card_color(card_name: str) -> str:
    data = mock_oracle_db.get(card_name.lower())
    if not data:
        return "#CCCCCC" # Default gray for not found
        
    colors = data.get("colors", [])
    
    if len(colors) == 0:
        return "#A0A0A0" # Colorless (Artifacts/Lands)
    elif len(colors) > 1:
        return "#D4AF37" # Gold (Multicolor)
    else:
        # Map single MTG colors to nice UI hex codes
        color_map = {
            "W": "#F8E7B9", 
            "U": "#4A90E2", 
            "B": "#4B4B4B", 
            "R": "#E24A4A", 
            "G": "#4AE27A"
        }
        return color_map.get(colors[0], "#CCCCCC")

print("--- Testing Color Extraction ---")
print(f"Lightning Bolt: {get_card_color('lightning bolt')}")
print(f"Edgar Markov:   {get_card_color('edgar markov')}")
print(f"Sol Ring:       {get_card_color('sol ring')}")
