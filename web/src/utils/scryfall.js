/**
 * Fetches card metadata in batches from Scryfall's Collection lookup endpoint.
 * Respects rate limits and splits list into chunks of 75.
 * 
 * @param {string[]} cardNames List of card names
 * @returns {Promise<Object>} Map of lowercase card names to card metadata objects
 */
export async function fetchCardsMetadata(cardNames) {
  const uniqueNames = [...new Set(cardNames.map(name => name.trim().toLowerCase()))].filter(Boolean);
  if (uniqueNames.length === 0) return {};

  const chunks = [];
  const chunkSize = 75;
  for (let i = 0; i < uniqueNames.length; i += chunkSize) {
    chunks.push(uniqueNames.slice(i, i + chunkSize));
  }

  const database = {};

  for (const chunk of chunks) {
    const body = {
      identifiers: chunk.map(name => ({ name }))
    };

    try {
      const response = await fetch("https://api.scryfall.com/cards/collection", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json;q=0.9,*/*;q=0.8",
          "User-Agent": "Loreweaver/1.0"
        },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        throw new Error(`Scryfall API error: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.data) {
        for (const card of data.data) {
          const name = card.name;
          if (!name) continue;
          
          // Parse types and subtypes from type_line (e.g., "Legendary Creature — Human Wizard")
          let types = [];
          let subtypes = [];
          const typeLine = card.type_line || "";
          if (typeLine) {
            const parts = typeLine.split("—");
            const typePart = parts[0].trim();
            types = typePart.split(" ").map(t => t.toLowerCase());
            
            if (parts[1]) {
              subtypes = parts[1].trim().split(" ").filter(Boolean).map(s => s.toLowerCase());
            }
          }
          
          database[name.toLowerCase()] = {
            name: name,
            raw_type: typeLine,
            types: types,
            subtypes: subtypes,
            oracle_text: card.oracle_text || "",
            mana_cost: card.mana_cost || "",
            cmc: card.cmc || 0,
            colors: card.colors || [],
            set: card.set || "",
            image_url: card.image_uris ? (card.image_uris.normal || card.image_uris.small) : "",
            edhrec_rank: card.edhrec_rank
          };
        }
      }
      
      // Delay to respect Scryfall rate limit recommendations (600ms between calls)
      if (chunks.length > 1) {
        await new Promise(resolve => setTimeout(resolve, 600));
      }
    } catch (error) {
      console.error("Error fetching Scryfall data chunk:", error);
    }
  }

  return database;
}
