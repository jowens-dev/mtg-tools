import csv
import json
from collections import defaultdict
from pathlib import Path

def analyze_commanders():
    inventory_path = Path('data/collection_tagged_bulk.csv')
    oracle_path = Path('data/oracle-cards.json')
    output_path = Path('data/commander_analysis.csv')

    # 1. Load Oracle Data for quick lookup
    print("Loading Oracle Data...")
    with oracle_path.open(encoding='utf-8') as f:
        cards = [json.loads(line) for line in f if line.strip()]
    
    oracle_db = {}
    for card in cards:
        name = card.get('name')
        if name and name not in oracle_db:
            oracle_db[name] = card

    # 2. Load Inventory
    print("Loading Inventory...")
    with inventory_path.open(newline='', encoding='utf-8') as f:
        inventory = list(csv.DictReader(f))

    # 3. Identify owned Legendary Creatures and total card pool by color
    owned_commanders = []
    pool_by_color = defaultdict(list)
    
    for row in inventory:
        name = row.get('Product Name', '')
        card_data = oracle_db.get(name)
        if not card_data:
            continue
            
        type_line = card_data.get('type_line', '')
        color_id = row.get('Color Identity', '')
        
        # Add to color pool for support checking
        pool_by_color[color_id].append(card_data)
        
        # Check if it can be a commander
        if 'Legendary' in type_line and 'Creature' in type_line:
            owned_commanders.append({
                'Name': name,
                'Color Identity': color_id,
                'Oracle Text': card_data.get('oracle_text', '').replace('\n', ' '),
                'Type': type_line
            })

    # 4. Search for mechanical synergies
    print(f"Found {len(owned_commanders)} potential commanders. Analyzing synergies...")
    
    # Common build-around keywords to look for in commander text
    themes = ['artifact', 'enchantment', 'graveyard', 'token', 'sacrifice', '+1/+1 counter', 'historic', 'dragon', 'zombie', 'goblin', 'elf']
    
    results = []
    for cmdr in owned_commanders:
        text = cmdr['Oracle Text'].lower()
        cmdr_themes = [t for t in themes if t in text]
        
        # Count potential support cards in the same color identity
        support_count = 0
        matching_pool = pool_by_color.get(cmdr['Color Identity'], [])
        
        if cmdr_themes:
            for support_card in matching_pool:
                support_text = support_card.get('oracle_text', '').lower()
                support_type = support_card.get('type_line', '').lower()
                
                # If the support card shares a mechanical theme with the commander
                if any(t in support_text or t in support_type for t in cmdr_themes):
                    support_count += 1
                    
        cmdr['Themes'] = ', '.join(cmdr_themes)
        cmdr['Support Cards Owned'] = support_count
        results.append(cmdr)

    # Sort by the highest number of synergistic support cards
    results.sort(key=lambda x: x['Support Cards Owned'], reverse=True)

    # 5. Export Results
    with output_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Name', 'Color Identity', 'Type', 'Themes', 'Support Cards Owned', 'Oracle Text'])
        writer.writeheader()
        writer.writerows(results)

    print(f"Analysis complete. Wrote {len(results)} commanders to {output_path}")
    
    # Print top 10 most supported thematic commanders
    print("\nTop 10 Highly Supported Build-Around Commanders:")
    for cmdr in results[:10]:
        if cmdr['Support Cards Owned'] > 0:
            print(f"- {cmdr['Name']} ({cmdr['Color Identity']}): {cmdr['Themes']} ({cmdr['Support Cards Owned']} support cards)")

if __name__ == '__main__':
    analyze_commanders()
