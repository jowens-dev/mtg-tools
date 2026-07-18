1. Put your inventory CSV and Scryfall SQLite DB into the mtg-tools folder.
2. Run the tagging step:
   /Users/yella4jella/workspace/praxis/.venv/bin/python scripts/tag_color_identity.py /path/to/mtg_canonical_inventory.csv /path/to/scryfall_cards.db --output /path/to/mtg_canonical_inventory_tagged.csv
3. Build a gauntlet candidate list:
   /Users/yella4jella/workspace/praxis/.venv/bin/python scripts/build_gauntlet.py /path/to/mtg_canonical_inventory_tagged.csv --color-identity R --max-price 1.50 --max-cards 60 --output /path/to/gauntlet_candidates.csv
