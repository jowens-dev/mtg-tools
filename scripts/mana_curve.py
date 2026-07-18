import json
import re
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from tkinter import ttk
import sys
import os

def get_resource_path(relative_path):
    """ Get the absolute path to a resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores the path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def load_oracle_database(filepath: str) -> dict:
    database = {}
    path = Path(filepath)
    if not path.exists():
        return database
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"Error loading DB: {e}")
        return database

    for card in raw_data:
        # --- THESE 5 LINES MUST BE AT THE TOP OF THE LOOP ---
        name = card.get("name", "").lower()
        mana_cost = card.get("mana_cost", "")
        colors = card.get("colors", []) 
        type_line = card.get("type_line", "")
        oracle_text = card.get("oracle_text", "")
        
        # Scryfall double-faced cards logic
        if not mana_cost and "card_faces" in card:
            mana_cost = card["card_faces"][0].get("mana_cost", "")
            colors = card.get("colors", card["card_faces"][0].get("colors", []))
            type_line = card["card_faces"][0].get("type_line", type_line)
            oracle_text = card["card_faces"][0].get("oracle_text", oracle_text)
            
        # Define the absolute "Noise" set
        # Define the absolute "Noise" set
        noise = {
            "Legendary", "Basic", "Snow", "World", "Ongoing", 
            "Creature", "Artifact", "Enchantment", "Instant", "Sorcery", 
            "Planeswalker", "Land", "Battle", "Tribal",
            "Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"
        }
        
        # Parse and clean the Type Line
        is_legendary = "Legendary" in type_line
        clean_type_line = type_line.replace("—", " ").replace("-", " ")
        
        # Filter tokens out during ingestion
        core_types = [word for word in clean_type_line.split() if word not in noise and len(word) > 2]
            
        # Map to the database dictionary
        if name:
            database[name] = {
                "mana_cost": mana_cost, 
                "colors": colors,
                "is_legendary": is_legendary,
                "types": core_types,
                "oracle_text": oracle_text,
                "raw_type": type_line # <-- ADD THIS LINE
            }
            
    print(f"Successfully loaded {len(database)} cards into memory!\n")
    return database

def calculate_mana_value(mana_cost_string: str) -> int:
    if not mana_cost_string:
        return 0
    matches = re.findall(r'\{([^}]+)\}', mana_cost_string)
    total_mv = 0
    for m in matches:
        if m.isdigit():
            total_mv += int(m)
        elif m == 'X':
            pass
        else:
            total_mv += 1
    return total_mv

def get_card_color(colors: list) -> str:
    if not colors:
        return "#A0A0A0" # Colorless
    if len(colors) > 1:
        return "#D4AF37" # Gold
    color_map = {
        "W": "#F8E7B9", 
        "U": "#4A90E2", 
        "B": "#4B4B4B", 
        "R": "#E24A4A", 
        "G": "#4AE27A"
    }
    return color_map.get(colors[0], "#CCCCCC")

def cluster_deck_by_type(deck_names: list, db: dict) -> list:
    clusters = {}
    for name in deck_names:
        card_data = db.get(name.lower())
        if not card_data:
            continue
        for card_type in card_data.get("types", []):
            if card_type not in clusters:
                clusters[card_type] = 0
            clusters[card_type] += 1
            
    # Return sorted list of tuples: [('Creature', 30), ('Vampire', 15), ...]
    return sorted(clusters.items(), key=lambda item: item[1], reverse=True)

def parse_decklist_text(text: str) -> list[str]:
    deck_names = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.lower() in ('commander', 'deck', 'sideboard', 'maybeboard') or line.startswith('//'):
            continue
        try:
            parts = line.split(" ", 1)
            qty = int(parts[0].replace('x', '').strip())
            name = parts[1].strip()
            deck_names.extend([name] * qty)
        except ValueError:
            deck_names.append(line)
    return deck_names

class ManaCurveApp:
    def __init__(self, root, db_path):
        self.root = root
        self.root.title("MTG Mana Curve Visualizer")
        self.root.geometry("800x500")
        
        self.oracle_db = load_oracle_database(db_path)
        self.setup_ui()
        
        if not self.oracle_db:
            messagebox.showwarning("Database Missing", f"Could not load Oracle DB from {db_path}.")

    def setup_ui(self):
        left_frame = tk.Frame(self.root, padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(left_frame, text="Paste Decklist Here:", font=("Helvetica", 12, "bold")).pack(anchor=tk.W)
        
        self.text_area = tk.Text(left_frame, width=35, height=25)
        self.text_area.pack(pady=5)
        self.text_area.insert(tk.END, "1 Sol Ring\n1x Arcane Signet\n2 Counterspell\n1 Rhystic Study\n1 Smothering Tithe\n1 Blasphemous Act\nCommander\n1 Edgar Markov")
        
        calc_btn = tk.Button(left_frame, text="Calculate Curve", command=self.calculate_and_draw, bg="#4a90e2", fg="black", font=("Helvetica", 12, "bold"))
        calc_btn.pack(fill=tk.X, pady=10)
        
        right_frame = tk.Frame(self.root, padx=10, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        tk.Label(right_frame, text="Mana Curve", font=("Helvetica", 14, "bold")).pack(anchor=tk.N)
        
        self.stats_label = tk.Label(right_frame, text="Deck Stats will appear here", font=("Helvetica", 12))
        self.stats_label.pack(pady=5)
        
        self.theme_label = tk.Label(right_frame, text="Top Themes: None", font=("Helvetica", 10, "italic"), fg="#555")
        self.theme_label.pack(pady=2)
        
        self.canvas = tk.Canvas(right_frame, bg="white", width=500, height=400, highlightthickness=1, highlightbackground="gray")
        self.canvas.pack(pady=10)

        # Inside setup_ui:
        self.tree = ttk.Treeview(right_frame, columns=("Theme", "Count"), show='headings', height=5)
        self.tree.heading("Theme", text="Theme")
        self.tree.heading("Count", text="Count")
        self.tree.column("Theme", width=120)
        self.tree.column("Count", width=50)
        self.tree.pack(pady=5)
        
    def calculate_and_draw(self):
        raw_text = self.text_area.get("1.0", tk.END)
        deck_names = parse_decklist_text(raw_text)

        type_clusters = cluster_deck_by_type(deck_names, self.oracle_db)
        
        # Inside calculate_and_draw:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for theme, count in type_clusters:
            self.tree.insert("", "end", values=(theme, count))
        if not deck_names:
            messagebox.showinfo("Empty", "No valid cards found in the text area.")
            return
            
        lands_count = 0
        spells_count = 0
        total_mv = 0
        curve_data = {}
        
        for name in deck_names:
            lower_name = name.lower()
            card_info = self.oracle_db.get(lower_name, {"mana_cost": "", "colors": []})
            cost = card_info.get("mana_cost", "")
            color_hex = get_card_color(card_info.get("colors", []))
            
            if cost == "": 
                lands_count += 1
            else:
                spells_count += 1
                mv = calculate_mana_value(cost)
                total_mv += mv
                
                if mv not in curve_data:
                    curve_data[mv] = {}
                curve_data[mv][color_hex] = curve_data[mv].get(color_hex, 0) + 1
                
        avg_mv = (total_mv / spells_count) if spells_count > 0 else 0
        self.stats_label.config(text=f"Total: {len(deck_names)} | Lands: {lands_count} | Spells: {spells_count} | Avg MV: {avg_mv:.2f}")
        
        # Filter out generic MTG types to find the real flavor
        ignore_types = {"Creature", "Instant", "Sorcery", "Artifact", "Enchantment", "Land", "Planeswalker", "Battle", "Tribal"}
        # The list is already clean from the Ingestion Phase!
        # Just grab the top 4 themes directly from the cluster results.
        flavor_types = [f"{t} ({c})" for t, c in type_clusters]

        # --- TUNED HEURISTICS ENGINE ---
        macro_themes = []
        
        # Tally the structural types safely using the raw data
        pw_count = sum(1 for n in deck_names if "Planeswalker" in self.oracle_db.get(n.lower(), {}).get("raw_type", ""))
        leg_count = sum(1 for n in deck_names if "Legendary" in self.oracle_db.get(n.lower(), {}).get("raw_type", ""))
        ench_count = sum(1 for n in deck_names if "Enchantment" in self.oracle_db.get(n.lower(), {}).get("raw_type", ""))
        art_count = sum(1 for n in deck_names if "Artifact" in self.oracle_db.get(n.lower(), {}).get("raw_type", ""))
        
        # Fine-Tuned Archetype Thresholds
        if pw_count >= 12: macro_themes.append(f"Superfriends ({pw_count})")
        if leg_count >= 18: macro_themes.append(f"Legends Matter ({leg_count})")
        if ench_count >= 25: macro_themes.append(f"Enchantress ({ench_count})")
        if art_count >= 25: macro_themes.append(f"Artifacts ({art_count})")
        if lands_count >= 40: macro_themes.append(f"Lands Matter ({lands_count})")

        # Combine our Macro Themes with our Tribal Themes
        combined_themes = macro_themes + flavor_types
        # -----------------------------

        # Update this line to use combined_themes instead of flavor_types
        top_themes = ", ".join(combined_themes[:4]) if combined_themes else "None"
        self.theme_label.config(text=f"Top Themes: {top_themes}")
            
        self.draw_chart(curve_data)
        
    def draw_chart(self, curve_data):
        self.canvas.delete("all")
        if not curve_data:
            return
            
        c_width = int(self.canvas['width'])
        c_height = int(self.canvas['height'])
        padding_x = 40
        padding_y = 40
        
        max_count = max(sum(colors.values()) for colors in curve_data.values()) if curve_data else 1
        max_mana = max(curve_data.keys()) if curve_data else 1
        
        bar_width = (c_width - 2 * padding_x) / (max_mana + 1)
        
        for mana, color_counts in curve_data.items():
            total_in_slot = sum(color_counts.values())
            
            x0 = padding_x + (mana * bar_width) + (bar_width * 0.1)
            x1 = padding_x + ((mana + 1) * bar_width) - (bar_width * 0.1)
            
            current_y_bottom = c_height - padding_y
            
            for color_hex, count in color_counts.items():
                segment_height = (count / max_count) * (c_height - 2 * padding_y)
                current_y_top = current_y_bottom - segment_height
                
                self.canvas.create_rectangle(x0, current_y_top, x1, current_y_bottom, fill=color_hex, outline="black")
                current_y_bottom = current_y_top 
            
            self.canvas.create_text((x0 + x1)/2, c_height - padding_y + 15, text=str(mana), font=("Helvetica", 10, "bold"), fill="black")
            self.canvas.create_text((x0 + x1)/2, current_y_bottom - 10, text=str(total_in_slot), font=("Helvetica", 10), fill="black")

if __name__ == "__main__":
    root = tk.Tk()
    # Use the helper function to dynamically find the database
    db_path = get_resource_path("oracle-cards.json") 
    app = ManaCurveApp(root, db_path)
    root.mainloop()