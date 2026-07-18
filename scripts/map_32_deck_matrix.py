import csv
import json
from collections import defaultdict
from pathlib import Path

# The 32-Deck Philosophy Framework
PHILOSOPHIES = {
    '': ('Tier 0 - Colorless', ['artifact', 'eldrazi', 'equipment', 'vehicle', 'colorless']),
    'B,G,R,U,W': ('Tier 0 - Five-Color', ['choose', 'all colors', 'domain', 'wubrg']),
    'W': ('Tier 1 - White (Structure/Peace)', ['protection', 'token', 'life', 'prevent', 'exile', 'human', 'rule']),
    'U': ('Tier 1 - Blue (Knowledge/Perfection)', ['draw', 'counter', 'return', 'flying', 'artifact', 'instant', 'sorcery']),
    'B': ('Tier 1 - Black (Power/Self-Interest)', ['sacrifice', 'graveyard', 'destroy', 'discard', 'lose life', 'zombie', 'pay life']),
    'R': ('Tier 1 - Red (Freedom/Impulse)', ['damage', 'haste', 'discard', 'treasure', 'goblin', 'dragon', 'combat', 'random']),
    'G': ('Tier 1 - Green (Growth/Acceptance)', ['land', 'token', '+1/+1', 'trample', 'elf', 'fight', 'mana', 'nature']),
    'U,W': ('Tier 2 - Azorius (Calculated Structure)', ['flying', 'draw', 'exile', 'prevent', 'tap', 'artifact', 'tax']),
    'B,U': ('Tier 2 - Dimir (Calculated Self-Interest)', ['mill', 'discard', 'draw', 'graveyard', 'rogue', 'ninja', 'unblockable', 'look']),
    'B,R': ('Tier 2 - Rakdos (Uninhibited Hedonism)', ['sacrifice', 'damage', 'discard', 'lose life', 'treasure', 'demon', 'random']),
    'G,R': ('Tier 2 - Gruul (Untamed Ferocity)', ['trample', 'damage', 'land', '+1/+1', 'fight', 'power', 'attack']),
    'G,W': ('Tier 2 - Selesnya (Altruistic Community)', ['token', '+1/+1', 'life', 'human', 'enchantment', 'convoke', 'populate']),
    'B,W': ('Tier 2 - Orzhov (Institutionalized Ambition)', ['life', 'sacrifice', 'graveyard', 'token', 'return', 'cleric', 'extort']),
    'R,U': ('Tier 2 - Izzet (Unpredictable Innovation)', ['instant', 'sorcery', 'draw', 'damage', 'artifact', 'copy', 'dice']),
    'B,G': ('Tier 2 - Golgari (Cycle of Life/Death)', ['graveyard', 'sacrifice', 'return', 'token', '+1/+1', 'insect', 'fungus', 'mill']),
    'R,W': ('Tier 2 - Boros (Passionate Justice)', ['combat', 'equipment', 'haste', 'token', 'attack', 'damage', 'extra combat']),
    'G,U': ('Tier 2 - Simic (Guided Evolution)', ['+1/+1', 'draw', 'land', 'token', 'copy', 'mutant', 'evolve', 'counters']),
    'G,U,W': ('Tier 3 - Bant (Perfect Utopia)', ['enchantment', '+1/+1', 'exile', 'draw', 'flying', 'exalted']),
    'B,U,W': ('Tier 3 - Esper (Ruthless Perfection)', ['artifact', 'flying', 'draw', 'exile', 'graveyard', 'control']),
    'B,R,U': ('Tier 3 - Grixis (Self-Indulgence)', ['graveyard', 'damage', 'instant', 'sorcery', 'discard', 'sacrifice']),
    'B,G,R': ('Tier 3 - Jund (Pure Darwinism)', ['sacrifice', 'graveyard', 'damage', 'token', '+1/+1', 'devour']),
    'G,R,W': ('Tier 3 - Naya (Primal Community)', ['token', '+1/+1', 'trample', 'combat', 'land', 'power 5']),
    'B,G,W': ('Tier 3 - Abzan (Enduring Survival)', ['+1/+1', 'graveyard', 'token', 'life', 'exile', 'outlast']),
    'R,U,W': ('Tier 3 - Jeskai (Enlightened Strategy)', ['instant', 'sorcery', 'flying', 'prowess', 'damage']),
    'B,G,U': ('Tier 3 - Sultai (Ruthless Exploitation)', ['graveyard', 'draw', 'mill', 'token', '+1/+1', 'delve']),
    'B,R,W': ('Tier 3 - Mardu (Brutal Conquest)', ['combat', 'sacrifice', 'token', 'damage', 'equipment', 'attack']),
    'G,R,U': ('Tier 3 - Temur (Savage Instinct)', ['elemental', 'damage', 'draw', 'land', 'trample', 'power 4']),
    'B,R,U,W': ('Tier 4 - Yore-Tiller (Artificial Progress)', ['artifact', 'sacrifice', 'damage', 'thopter', 'return']),
    'B,G,R,U': ('Tier 4 - Glint-Eye (Unbound Chaos)', ['cascade', 'draw', 'damage', 'graveyard', 'random']),
    'B,G,R,W': ('Tier 4 - Dune-Brood (Visceral Aggression)', ['combat', 'damage', 'token', '+1/+1', 'attack']),
    'G,R,U,W': ('Tier 4 - Ink-Treader (Pure Altruism)', ['draw', 'land', 'token', 'prevent', 'each player']),
    'B,G,U,W': ('Tier 4 - Witch-Maw (Stagnation/Growth)', ['proliferate', '+1/+1', 'counter', 'planeswalker', 'exile'])
}

def get_normalized_identity(color_str):
    if not color_str:
        return ''
    colors = [c for c in color_str.split(',') if c]
    colors.sort()
    return ','.join(colors)

def map_commanders():
    inventory_path = Path('data/collection_tagged_bulk.csv')
    oracle_path = Path('data/oracle-cards.json')
    output_path = Path('data/32_deck_matrix.csv')

    print("Loading Oracle Data...")
    with oracle_path.open(encoding='utf-8') as f:
        cards = json.load(f)
    
    oracle_db = {card.get('name'): card for card in cards if card.get('name')}

    print("Loading Inventory...")
    with inventory_path.open(newline='', encoding='utf-8') as f:
        inventory = list(csv.DictReader(f))

    commanders = []
    pool_by_color = defaultdict(list)
    
    for row in inventory:
        name = row.get('Product Name', '')
        if not name and 'Card Name' in row:
            name = row.get('Card Name', '')
            
        card_data = oracle_db.get(name)
        if not card_data:
            continue
            
        type_line = card_data.get('type_line', '')
        raw_colors = row.get('Color Identity', '')
        norm_id = get_normalized_identity(raw_colors)
        
        # Add to exact color pool
        pool_by_color[norm_id].append(card_data)
        
        if 'Legendary' in type_line and 'Creature' in type_line:
            commanders.append({
                'Name': name,
                'Normalized ID': norm_id,
                'Oracle Text': card_data.get('oracle_text', '').replace('\n', ' '),
                'Type': type_line
            })

    print(f"Scoring {len(commanders)} commanders against the 32 philosophies...")
    results = []
    
    for cmdr in commanders:
        norm_id = cmdr['Normalized ID']
        archetype_info = PHILOSOPHIES.get(norm_id)
        
        if not archetype_info:
            continue
            
        archetype_name, phi_keywords = archetype_info
        text = cmdr['Oracle Text'].lower()
        
        # 1. Check Philosophical Alignment
        matched_keywords = [kw for kw in phi_keywords if kw in text or kw in cmdr['Type'].lower()]
        alignment_score = len(matched_keywords)
        
        # 2. Check Collection Support
        support_count = 0
        if alignment_score > 0:
            matching_pool = pool_by_color.get(norm_id, [])
            for support_card in matching_pool:
                support_text = support_card.get('oracle_text', '').lower()
                support_type = support_card.get('type_line', '').lower()
                if any(kw in support_text or kw in support_type for kw in matched_keywords):
                    support_count += 1
        
        results.append({
            'Tier/Archetype': archetype_name,
            'Color ID': norm_id,
            'Commander': cmdr['Name'],
            'Alignment Score': alignment_score,
            'Matched Philosophy': ', '.join(matched_keywords),
            'Owned Support Cards': support_count,
            'Oracle Text': cmdr['Oracle Text']
        })

    # Sort to find the best fit for each of the 32 slots
    results.sort(key=lambda x: (x['Tier/Archetype'], -x['Alignment Score'], -x['Owned Support Cards']))

    with output_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Tier/Archetype', 'Color ID', 'Commander', 'Alignment Score', 'Matched Philosophy', 'Owned Support Cards', 'Oracle Text'])
        writer.writeheader()
        writer.writerows(results)

    print(f"Analysis complete. Wrote {len(results)} mappings to {output_path}")

if __name__ == '__main__':
    map_commanders()
