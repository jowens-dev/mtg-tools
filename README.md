# MTG tools

This workspace contains a small Python pipeline for turning a canonical MTG inventory CSV into a color-tagged inventory file that can be used for gauntlet building and other card-selection workflows.

## Files

- scripts/tag_color_identity.py: adds a Color Identity column by joining your inventory against a local Scryfall SQLite database.
- tests/test_tag_color_identity.py: smoke tests for the small helper functions in the tagging script.

## Usage

```bash
python3 scripts/tag_color_identity.py /path/to/mtg_canonical_inventory.csv /path/to/scryfall_cards.db --output /path/to/mtg_canonical_inventory_tagged.csv
```

The script expects the inventory CSV to contain a card-name column such as `Card Name` or `card_name`.

MTG Thematic Deck Companion - Dependency Map

Core Philosophy: This is NOT an EDHREC clone. This app analyzes the flavor, theme, and mechanical synergy of a deck, not just raw play-rates.

🧠 AI Dispatch Protocol (Token Management)

Never burn heavy tokens on light work. Never ask a light model for heavy architecture.

The Heavyweights (Claude 3.5 Sonnet / GPT-4o): * Use for: System architecture, writing complex algorithms (like the Theme Cohesion Score), generating large boilerplate from scratch, and debugging massive traceback errors.

Limit: Strict token budgets. Only feed them exactly the code they need (e.g., just the load_oracle_database function, not the whole file).

The Local Sandbox (Praxis 3B):

Use for: Rubber-ducking, quick syntax checks, running 10-line Python sandboxes, and keeping you on task when you get distracted.

Limit: Zero token cost, but extremely low context. Never give it more than 50 lines of code at a time.

The Copilot (Cursor/GitHub Copilot):

Use for: Line-by-line autocomplete and writing docstrings.

Layer 1: The Oracle (Data Foundation)

You cannot analyze cards if you don't know what they do.

[x] Acquire Raw Data: Download bulk Scryfall Oracle JSON.

[x] Base Ingestion: Script to load oracle-cards.json into Python memory.

[x] Base Extraction: Extract name and mana_cost.

[ ] CURRENT BOTTLENECK -> Thematic Extraction: Extract type_line (Legendary, Creature types), oracle_text (mechanics), and colors. (Sandbox verified, needs integration).

[ ] Flavor Extraction: Extract flavor_text and art_tags (if available via Scryfall APIs/bulk).

Layer 2: The Ingestion Engine (User Input)

You cannot analyze a deck if you can't read the user's list.

[x] Regex/Splitter: Parse standard decklist strings (quantities + names).

[x] Quantity Aggregator: Multiply card objects by their deck quantity.

[x] DB Matcher: Safely map parsed text names to the loaded Oracle DB.

Layer 3: The Tactical Baseline (Stats)

You need a functional deck before you can make it flavorful.

[x] Mana Value Calculator: Convert {2}{U}{U} to 4.

[x] Color Mapping: Map Scryfall color arrays to UI hex codes.

[x] Curve UI: Render a stacked bar chart of the mana curve.

[ ] Cost Modifiers: Engine to dynamically alter MV (e.g., Blasphemous Act = 1). (Optional/Low Priority for MVP).

Layer 4: The Thematic Engine (The Core USP)

This is the heart of the app. It relies entirely on Layer 1 being finished.

[ ] Type Clustering: Group the deck by supertypes (Legendary) and subtypes (Vampire, Knight, Equipment).

[ ] Mechanical Keyword Scanner: Scan oracle_text for recurring themes (e.g., "sacrifice", "landfall", "historic").

[ ] Theme Scoring Algorithm: Calculate a "Theme Cohesion Score" based on how many cards share subtypes, keywords, or watermarks.

[ ] The "Vorthos" Analyzer: Flag cards that mechanically fit but flavorfully clash (e.g., a Cyberpunk Kamigawa card in a Gothic Innistrad vampire deck).

Layer 5: The UI & Presentation

Users need to see the thematic data clearly.

[x] Base Application: Tkinter window setup with input/output panes.

[ ] Thematic Dashboard: UI panels to display Top Creature Types, Dominant Keywords, and Cohesion Score.

[ ] Visual Filtering: Dropdowns to view the deck by Color, by Type, or by Custom Tag.

[ ] Export: Ability to save the thematic report to a text file or markdown.
