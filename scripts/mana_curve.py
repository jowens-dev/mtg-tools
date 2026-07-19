#!/usr/bin/env python3
"""MTG Deck Stress-Tester & Mana Curve Visualizer Dashboard."""

import json
import re
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from pathlib import Path
import sys
import os

# Insert current directory into path to allow local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recommend_deck import (
    load_oracle_database,
    is_land,
    is_ramp,
    is_draw,
    is_protection,
    is_multiplayer_scaling,
    calculate_fragility_weight,
    calculate_cohesion_score,
    analyze_flavor_clashes
)
from math_utils import calculate_joint_consistency


def get_resource_path(relative_path):
    """Get the absolute path to a resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


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
        return "#A0A0A0"  # Colorless
    if len(colors) > 1:
        return "#D4AF37"  # Gold
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
        self.root.title("Loreweaver - MTG Thematic Deck Companion")
        self.root.geometry("1050x650")
        
        # Set app icon
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(project_root, "assets", "app_icon.png")
        if os.path.exists(icon_path):
            try:
                self.icon_img = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, self.icon_img)
            except Exception as e:
                print(f"Could not load window icon: {e}", file=sys.stderr)
        
        # Configure modern aesthetic styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TNotebook", background="#F5F5F5")
        self.style.configure("TNotebook.Tab", font=("Helvetica", 11, "bold"), padding=[10, 5])
        
        self.oracle_db = load_oracle_database(db_path)
        self.setup_ui()
        
        if not self.oracle_db:
            messagebox.showwarning("Database Missing", f"Could not load Oracle DB from {db_path}.")

    def setup_ui(self):
        # Left Panel (Deck Input)
        left_frame = tk.Frame(self.root, padx=15, pady=15, bg="#EAEAEA", width=320)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)
        
        tk.Label(left_frame, text="Paste Decklist Here:", font=("Helvetica", 12, "bold"), bg="#EAEAEA").pack(anchor=tk.W)
        
        self.text_area = tk.Text(left_frame, width=32, height=28, font=("Courier", 10))
        self.text_area.pack(pady=5, fill=tk.BOTH, expand=True)
        
        # Set a default test deck (Kozilek Theme / Colorless & general spells)
        self.text_area.insert(
            tk.END,
            "// Commander\n"
            "1 Kozilek, the Great Distortion\n\n"
            "// Lands\n"
            "37 Wastes\n\n"
            "// Spells\n"
            "1 Sol Ring\n"
            "1 Mana Vault\n"
            "1 Thran Dynamo\n"
            "1 Mind Stone\n"
            "1 Worn Powerstone\n"
            "1 Everflowing Chalice\n"
            "1 Hedron Archive\n"
            "1 Kozilek's Channeler\n"
            "1 Palladium Myr\n"
            "1 Gilded Lotus\n"
            "1 Kozilek's Command\n"
            "1 Endbringer\n"
            "1 Solemn Simulacrum\n"
            "1 All Is Dust\n"
            "1 Titan's Presence\n"
            "1 Not of This World\n"
            "1 Introduction to Prophecy\n"
            "1 Warping Wail\n"
            "1 Spatial Contortion\n"
            "1 Swiftfoot Boots\n"
            "1 Lightning Greaves\n"
            "1 Soul of New Phyrexia"
        )
        
        calc_btn = tk.Button(
            left_frame, text="Analyze Deck", command=self.calculate_and_draw,
            bg="#2980B9", fg="black", font=("Helvetica", 12, "bold"),
            relief=tk.FLAT, bd=0, height=2
        )
        calc_btn.pack(fill=tk.X, pady=10)
        
        # Right Panel (Notebook containing Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # TAB 1: Mana Curve & Themes
        self.tab_curve = tk.Frame(self.notebook, bg="#F5F5F5", padx=15, pady=15)
        self.notebook.add(self.tab_curve, text="Mana Curve & Themes")
        
        tk.Label(self.tab_curve, text="Mana Curve Visualizer", font=("Helvetica", 14, "bold"), bg="#F5F5F5").pack(anchor=tk.N)
        
        self.stats_label = tk.Label(self.tab_curve, text="Deck Stats will appear here", font=("Helvetica", 11), bg="#F5F5F5")
        self.stats_label.pack(pady=5)
        
        self.theme_label = tk.Label(self.tab_curve, text="Top Themes: None", font=("Helvetica", 10, "italic"), fg="#555555", bg="#F5F5F5")
        self.theme_label.pack(pady=2)
        
        self.cohesion_label = tk.Label(self.tab_curve, text="Theme Cohesion Score: -", font=("Helvetica", 11, "bold"), fg="#2C3E50", bg="#F5F5F5")
        self.cohesion_label.pack(pady=2)
        
        self.flavor_label = tk.Label(self.tab_curve, text="Flavor Profile: -", font=("Helvetica", 10), fg="#555555", bg="#F5F5F5")
        self.flavor_label.pack(pady=2)
        
        self.canvas = tk.Canvas(self.tab_curve, bg="white", width=620, height=280, highlightthickness=1, highlightbackground="#CCCCCC")
        self.canvas.pack(pady=10, fill=tk.BOTH, expand=True)
        
        tk.Label(self.tab_curve, text="Subtype Clusters", font=("Helvetica", 11, "bold"), bg="#F5F5F5").pack(anchor=tk.W)
        self.tree = ttk.Treeview(self.tab_curve, columns=("Theme", "Count"), show='headings', height=5)
        self.tree.heading("Theme", text="Subtype / Keyword Theme")
        self.tree.heading("Count", text="Card Count")
        self.tree.column("Theme", width=250)
        self.tree.column("Count", width=100)
        self.tree.pack(pady=5, fill=tk.X)

        # TAB 2: Stress-Tester Dashboard
        self.tab_stress = tk.Frame(self.notebook, bg="#F5F5F5", padx=15, pady=15)
        self.notebook.add(self.tab_stress, text="Stress-Tester Dashboard")
        
        tk.Label(self.tab_stress, text="Engine Stress-Tester", font=("Helvetica", 14, "bold"), bg="#F5F5F5").pack(anchor=tk.N, pady=(0, 15))
        
        # Inner columns layout for Tab 2
        columns_frame = tk.Frame(self.tab_stress, bg="#F5F5F5")
        columns_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left Column: Fragility & Consistency
        left_col = tk.Frame(columns_frame, bg="#F5F5F5")
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 1. Fragility Indexing Frame
        self.fragility_card = tk.LabelFrame(left_col, text=" 1. Fragility Indexing ", font=("Helvetica", 11, "bold"), padx=10, pady=10, bg="#FFFFFF", fg="#2C3E50")
        self.fragility_card.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.frag_rating_label = tk.Label(self.fragility_card, text="Rating: -", font=("Helvetica", 12, "bold"), bg="#FFFFFF")
        self.frag_rating_label.pack(anchor=tk.W, pady=2)
        
        self.frag_score_label = tk.Label(self.fragility_card, text="Adjusted Score: -", font=("Helvetica", 10), bg="#FFFFFF")
        self.frag_score_label.pack(anchor=tk.W, pady=2)
        
        self.frag_breakdown_label = tk.Label(
            self.fragility_card, text="Creatures: 0 | Artifacts: 0 | Enchantments: 0 | Planeswalkers: 0",
            font=("Helvetica", 9), fg="#555555", bg="#FFFFFF"
        )
        self.frag_breakdown_label.pack(anchor=tk.W, pady=2)
        
        self.frag_protect_label = tk.Label(self.fragility_card, text="Protection Spells: 0", font=("Helvetica", 9), fg="#555555", bg="#FFFFFF")
        self.frag_protect_label.pack(anchor=tk.W, pady=2)
        
        self.frag_warn_label = tk.Label(
            self.fragility_card, text="[!] WARNING: High risk of disruption. Add protection.",
            font=("Helvetica", 9, "bold"), fg="#E24A4A", bg="#FFFFFF"
        )
        # Hidden by default
        self.frag_warn_label.pack_forget()

        # 3. Consistency Frame
        self.consistency_card = tk.LabelFrame(left_col, text=" 3. Engine Consistency ", font=("Helvetica", 11, "bold"), padx=10, pady=10, bg="#FFFFFF", fg="#2C3E50")
        self.consistency_card.pack(fill=tk.BOTH, expand=True)
        
        self.const_prob_label = tk.Label(self.consistency_card, text="Draw Probability (Turn 6): -", font=("Helvetica", 12, "bold"), bg="#FFFFFF")
        self.const_prob_label.pack(anchor=tk.W, pady=2)
        
        self.const_rating_label = tk.Label(self.consistency_card, text="Rating: -", font=("Helvetica", 10, "bold"), bg="#FFFFFF")
        self.const_rating_label.pack(anchor=tk.W, pady=2)
        
        self.const_breakdown_label = tk.Label(
            self.consistency_card, text="Lands: 0/37 | Ramp Spells: 0/10 | Draw Spells: 0/10",
            font=("Helvetica", 9), fg="#555555", bg="#FFFFFF"
        )
        self.const_breakdown_label.pack(anchor=tk.W, pady=2)
        
        # Right Column: Multiplayer Table-Pressure
        right_col = tk.Frame(columns_frame, bg="#F5F5F5")
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # 2. Table-Pressure Frame
        self.pressure_card = tk.LabelFrame(right_col, text=" 2. Multiplayer Table-Pressure ", font=("Helvetica", 11, "bold"), padx=10, pady=10, bg="#FFFFFF", fg="#2C3E50")
        self.pressure_card.pack(fill=tk.BOTH, expand=True)
        
        self.pressure_score_label = tk.Label(self.pressure_card, text="Table-Pressure Score: -", font=("Helvetica", 12, "bold"), bg="#FFFFFF")
        self.pressure_score_label.pack(anchor=tk.W, pady=2)
        
        # Custom Canvas Progress Bar
        self.pressure_canvas = tk.Canvas(self.pressure_card, bg="#FFFFFF", width=280, height=25, highlightthickness=0)
        self.pressure_canvas.pack(anchor=tk.W, pady=5)
        
        tk.Label(self.pressure_card, text="Scaling Multiplayer Spells:", font=("Helvetica", 10, "bold"), bg="#FFFFFF").pack(anchor=tk.W, pady=(10, 2))
        
        # Scrollable listbox for multiplayer scaling cards
        list_frame = tk.Frame(self.pressure_card, bg="#FFFFFF")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.scaling_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Helvetica", 9), relief=tk.FLAT, height=12)
        scrollbar.config(command=self.scaling_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.scaling_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def calculate_and_draw(self):
        raw_text = self.text_area.get("1.0", tk.END)
        deck_names = parse_decklist_text(raw_text)
        
        # Clear Treeview
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        if not deck_names:
            messagebox.showinfo("Empty", "No valid cards found in the text area.")
            return

        # Fetch Type Clusters
        type_clusters = cluster_deck_by_type(deck_names, self.oracle_db)
            
        lands_count = 0
        spells_count = 0
        total_mv = 0
        curve_data = {}
        
        # Advanced metric counters
        ramp_count = 0
        draw_count = 0
        protection_count = 0
        creatures_count = 0
        artifacts_count = 0
        enchantments_count = 0
        planeswalkers_count = 0
        scaling_spells = []
        non_land_perms = []
        
        for name in deck_names:
            lower_name = name.lower()
            card_info = self.oracle_db.get(lower_name)
            if not card_info:
                # Basic land check fallback
                if "wastes" in lower_name or "island" in lower_name or "forest" in lower_name or "swamp" in lower_name or "mountain" in lower_name or "plains" in lower_name:
                    lands_count += 1
                continue
                
            cost = card_info.get("mana_cost", "")
            color_hex = get_card_color(card_info.get("colors", []))
            
            # Lands vs Spells classification
            if is_land(card_info):
                lands_count += 1
            else:
                spells_count += 1
                mv = calculate_mana_value(cost)
                total_mv += mv
                
                if mv not in curve_data:
                    curve_data[mv] = {}
                curve_data[mv][color_hex] = curve_data[mv].get(color_hex, 0) + 1
                
                # Dynamic analytical roles classification
                if is_ramp(card_info):
                    ramp_count += 1
                if is_draw(card_info):
                    draw_count += 1
                if is_protection(card_info):
                    protection_count += 1
                if is_multiplayer_scaling(card_info):
                    scaling_spells.append(card_info["name"])
                    
                # Fragility Permanent counters
                frag_weight = calculate_fragility_weight(card_info)
                if frag_weight > 0.0:
                    non_land_perms.append(card_info)
                    raw_t = card_info.get("raw_type", "").lower()
                    if "creature" in raw_t:
                        creatures_count += 1
                    if "artifact" in raw_t:
                        artifacts_count += 1
                    if "enchantment" in raw_t:
                        enchantments_count += 1
                    if "planeswalker" in raw_t:
                        planeswalkers_count += 1

        avg_mv = (total_mv / spells_count) if spells_count > 0 else 0
        self.stats_label.config(text=f"Total: {len(deck_names)} | Lands: {lands_count} | Spells: {spells_count} | Avg MV: {avg_mv:.2f}")
        
        # Ingestion Archetype identification
        macro_themes = []
        pw_count = sum(1 for n in deck_names if "Planeswalker" in self.oracle_db.get(n.lower(), {}).get("raw_type", "").lower())
        leg_count = sum(1 for n in deck_names if "Legendary" in self.oracle_db.get(n.lower(), {}).get("raw_type", "").lower())
        ench_count = sum(1 for n in deck_names if "enchantment" in self.oracle_db.get(n.lower(), {}).get("raw_type", "").lower())
        art_count = sum(1 for n in deck_names if "artifact" in self.oracle_db.get(n.lower(), {}).get("raw_type", "").lower())
        
        if pw_count >= 12: macro_themes.append(f"Superfriends ({pw_count})")
        if leg_count >= 18: macro_themes.append(f"Legends Matter ({leg_count})")
        if ench_count >= 25: macro_themes.append(f"Enchantress ({ench_count})")
        if art_count >= 25: macro_themes.append(f"Artifacts ({art_count})")
        if lands_count >= 40: macro_themes.append(f"Lands Matter ({lands_count})")

        flavor_types = [f"{t} ({c})" for t, c in type_clusters]
        combined_themes = macro_themes + flavor_types
        top_themes = ", ".join(combined_themes[:4]) if combined_themes else "None"
        self.theme_label.config(text=f"Top Themes: {top_themes}")
        
        # Thematic Cohesion & Flavor Analysis
        cohesion_info = calculate_cohesion_score(deck_names, self.oracle_db)
        flavor_info = analyze_flavor_clashes(deck_names, self.oracle_db)

        # Update Cohesion score & Label color
        score = cohesion_info["cohesion_score"]
        if score >= 75:
            cohesion_color = "#27AE60" # Green
            cohesion_desc = "Excellent"
        elif score >= 50:
            cohesion_color = "#E67E22" # Orange
            cohesion_desc = "Moderate"
        else:
            cohesion_color = "#E24A4A" # Red
            cohesion_desc = "Low Cohesion"
        self.cohesion_label.config(
            text=f"Theme Cohesion Score: {score}/100 ({cohesion_desc})",
            fg=cohesion_color
        )

        # Update Flavor clash labels
        clashes = flavor_info["clashing_cards"]
        if clashes:
            clash_names = ", ".join(c["card"].title() for c in clashes[:2])
            clash_suffix = f" (Outliers: {clash_names})" if len(clashes) <= 2 else f" (Outliers: {clash_names} +{len(clashes)-2} more)"
            self.flavor_label.config(
                text=f"Flavor Profile: {flavor_info['dominant_plane']} centric | Vorthos Clash{clash_suffix}",
                fg="#E24A4A"
            )
        else:
            self.flavor_label.config(
                text=f"Flavor Profile: {flavor_info['dominant_plane']} centric (Cohesive)",
                fg="#27AE60"
            )

        # Also, let's update the treeview (Subtype Clusters table) to show both creature subtypes AND mechanical themes!
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Insert Creature Subtypes Header
        self.tree.insert("", "end", values=("--- Creature Types ---", ""))
        for subtype, count in cohesion_info["subtype_counts"].items():
            self.tree.insert("", "end", values=(f"  {subtype.title()}", count))

        # Insert Mechanical Themes Header
        self.tree.insert("", "end", values=("--- Mechanical Themes ---", ""))
        for theme, count in cohesion_info["theme_counts"].items():
            self.tree.insert("", "end", values=(f"  {theme}", count))
            
        self.draw_chart(curve_data)
        
        # --- UPDATE STRESS-TESTER DASHBOARD ---
        
        # 1. Fragility Index Calculations
        total_fragility = sum(calculate_fragility_weight(c) for c in non_land_perms)
        avg_fragility = (total_fragility / len(non_land_perms)) if non_land_perms else 0.0
        adjusted_fragility = avg_fragility - (protection_count * 0.05)
        
        if adjusted_fragility >= 0.6:
            fragility_rating = "High Fragility"
            fragility_color = "#E24A4A"
            self.frag_warn_label.pack(anchor=tk.W, pady=2)
        elif adjusted_fragility >= 0.35:
            fragility_rating = "Medium Fragility"
            fragility_color = "#E67E22"
            self.frag_warn_label.pack_forget()
        else:
            fragility_rating = "Low Fragility"
            fragility_color = "#27AE60"
            self.frag_warn_label.pack_forget()
            
        self.frag_rating_label.config(text=f"Rating: {fragility_rating}", fg=fragility_color)
        self.frag_score_label.config(text=f"Adjusted Score: {adjusted_fragility:.2f} (Average: {avg_fragility:.2f})")
        self.frag_breakdown_label.config(
            text=f"Creatures: {creatures_count} | Artifacts: {artifacts_count} | Enchantments: {enchantments_count} | Planeswalkers: {planeswalkers_count}"
        )
        self.frag_protect_label.config(text=f"Protection Spells: {protection_count}")
        
        # 2. Multiplayer Table-Pressure
        table_pressure_score = min(len(scaling_spells) * 10, 100)
        self.pressure_score_label.config(text=f"Table-Pressure Score: {table_pressure_score} / 100")
        
        # Clear and update Multiplayer Scaling Listbox
        self.scaling_listbox.delete(0, tk.END)
        unique_scaling = sorted(list(set(scaling_spells)))
        for item in unique_scaling:
            self.scaling_listbox.insert(tk.END, f"  {item}")
            
        # Draw table-pressure gauge / progress bar
        self.pressure_canvas.delete("all")
        self.pressure_canvas.create_rectangle(0, 0, 280, 25, fill="#E0E0E0", outline="")
        
        fill_color = "#27AE60"
        if table_pressure_score >= 70:
            fill_color = "#E24A4A"
        elif table_pressure_score >= 40:
            fill_color = "#E67E22"
            
        fill_w = int(280 * (table_pressure_score / 100.0))
        if fill_w > 0:
            self.pressure_canvas.create_rectangle(0, 0, fill_w, 25, fill=fill_color, outline="")
        self.pressure_canvas.create_text(
            140, 12, text=f"{table_pressure_score}%", font=("Helvetica", 10, "bold"),
            fill="black" if table_pressure_score < 60 else "white"
        )
        
        # 3. Engine Consistency Calculations
        joint_prob = calculate_joint_consistency(99, 13, lands_count, 3, ramp_count, 1, draw_count, 1)
        if joint_prob >= 0.70:
            consistency_rating = "High Consistency"
            consistency_color = "#27AE60"
        elif joint_prob >= 0.50:
            consistency_rating = "Medium Consistency"
            consistency_color = "#E67E22"
        else:
            consistency_rating = "Low Consistency"
            consistency_color = "#E24A4A"
            
        self.const_prob_label.config(text=f"Draw Probability (Turn 6): {joint_prob * 100:.1f}%", fg=consistency_color)
        self.const_rating_label.config(text=f"Rating: {consistency_rating}", fg=consistency_color)
        self.const_breakdown_label.config(
            text=f"Lands: {lands_count}/37 | Ramp Spells: {ramp_count}/10 | Draw Spells: {draw_count}/10"
        )

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
    
    # Dynamically find the database file in either scripts/ or root directory
    db_path = get_resource_path("oracle-cards.json")
    if not os.path.exists(db_path):
        db_path = get_resource_path("scripts/oracle-cards.json")
        
    app = ManaCurveApp(root, db_path)
    root.mainloop()