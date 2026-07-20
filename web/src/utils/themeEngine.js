const MECHANICAL_THEMES = {
  "Landfall / Lands": [/\blandfall\b/i, /whenever a land enters/i, /play an additional land/i],
  "Sacrifice / Aristocrats": [/sacrifice a/i, /whenever a.*dies/i, /die, you/i, /\baristocrat\b/i],
  "Graveyard / Reanimator": [/\bgraveyard\b/i, /return.*from your graveyard/i, /\breanimate\b/i, /\bdredge\b/i, /\bundergrowth\b/i],
  "Blink / Flicker": [/exile.*then return.*to the battlefield/i, /\bflicker\b/i, /\bblink\b/i, /enters the battlefield again/i],
  "Tokens": [/create.*token/i, /\bpopulate\b/i, /\bamass\b/i],
  "Counters (+1/+1 / Proliferate)": [/\+1\/\+1 counter/i, /\bproliferate\b/i, /doubling season/i, /hardened scales/i],
  "Spellslinger": [/whenever you cast an instant or sorcery/i, /instant or sorcery spell/i, /\bmagecraft\b/i],
  "Artifacts / Voltron": [/\bartifact\b/i, /\bequip\b/i, /enchant creature/i, /\baura\b/i, /\bvehicles\b/i],
  "Lifegain": [/gain life/i, /whenever you gain life/i, /\blifelink\b/i],
  "Discard / Madness": [/\bdiscard\b/i, /\bcycling\b/i, /\bmadness\b/i],
  "Planeswalkers / Superfriends": [/\bplaneswalker\b/i, /\bloyalty\b/i]
};

const SET_TO_PLANE = {
  // Innistrad (Gothic horror, vampires, werewolves)
  "isd": "Innistrad", "dka": "Innistrad", "avr": "Innistrad", "soi": "Innistrad", "emn": "Innistrad", "mid": "Innistrad", "vow": "Innistrad",
  // Kamigawa (Cyberpunk / Traditional Japanese)
  "chk": "Kamigawa", "bok": "Kamigawa", "sok": "Kamigawa", "neo": "Kamigawa",
  // Ravnica (Guild metropolis)
  "rav": "Ravnica", "gpt": "Ravnica", "dis": "Ravnica", "rtr": "Ravnica", "gtc": "Ravnica", "dgm": "Ravnica", "grn": "Ravnica", "rna": "Ravnica", "war": "Ravnica", "mkm": "Ravnica",
  // Mirrodin / New Phyrexia (Metal world)
  "mrd": "Mirrodin", "dst": "Mirrodin", "5dn": "Mirrodin", "som": "Mirrodin", "mbs": "Mirrodin", "nph": "Mirrodin", "one": "Mirrodin",
  // Zendikar (Adventure, elements, lands)
  "zen": "Zendikar", "wwk": "Zendikar", "roe": "Zendikar", "bfz": "Zendikar", "ogw": "Zendikar", "znr": "Zendikar",
  // Dominaria (High fantasy, history)
  "dom": "Dominaria", "dmu": "Dominaria", "bro": "Dominaria",
  // Theros (Greek myth, enchantments)
  "ths": "Theros", "bng": "Theros", "jou": "Theros", "thb": "Theros",
  // Eldraine (Fairy tales, knights)
  "eld": "Eldraine", "woe": "Eldraine",
  // Ixalan (Dinosaurs, Mesoamerican, pirates)
  "xln": "Ixalan", "rix": "Ixalan", "lci": "Ixalan"
};

const PLANE_CLASHES = {
  "Kamigawa": new Set(["Innistrad", "Eldraine", "Theros"]),
  "Innistrad": new Set(["Kamigawa", "Kaladesh"]),
  "Eldraine": new Set(["Kamigawa", "Mirrodin"]),
  "Mirrodin": new Set(["Eldraine", "Theros", "Ixalan"]),
  "Theros": new Set(["Kamigawa", "Mirrodin"]),
  "Ixalan": new Set(["Mirrodin", "Kamigawa"])
};

/**
 * Scan card's oracle text and types to identify matching themes
 * @param {Object} cardInfo 
 * @returns {string[]} Matching theme names
 */
function scanMechanicalKeywords(cardInfo) {
  const matched = [];
  const text = cardInfo.oracle_text || "";
  const typeLine = cardInfo.raw_type || "";
  
  for (const [theme, regexes] of Object.entries(MECHANICAL_THEMES)) {
    for (const regex of regexes) {
      if (regex.test(text) || regex.test(typeLine)) {
        matched.push(theme);
        break; // Stop scanning this theme once it matches
      }
    }
  }
  return matched;
}

/**
 * Parse a full decklist and return a list of card name strings
 * @param {string} text 
 * @returns {string[]} List of card names matching quantity (e.g. 3 copies = 3 entries)
 */
export function parseDecklistText(text) {
  const cardNames = [];
  const lines = text.split("\n");
  for (let line of lines) {
    line = line.trim();
    if (!line || line.toLowerCase() === "commander" || line.toLowerCase() === "deck" || line.toLowerCase() === "sideboard" || line.toLowerCase() === "maybeboard" || line.startsWith("//")) {
      continue;
    }
    
    // Parse quantity (e.g., "1 Kozilek" or "Kozilek")
    const parts = line.split(" ");
    let qty = parseInt(parts[0], 10);
    let name = line;
    
    if (!isNaN(qty) && qty > 0) {
      name = parts.slice(1).join(" ");
    } else {
      qty = 1;
    }
    
    name = name.replace(/\(.*\)/, "").trim(); // Strip set tags like (M19)
    for (let i = 0; i < qty; i++) {
      cardNames.push(name);
    }
  }
  return cardNames;
}

/**
 * Calculates Cohesion score and builds theme breakdowns
 * @param {string[]} deckNames 
 * @param {Object} db 
 * @returns {Object} Cohesion stats
 */
export function calculateCohesionScore(deckNames, db) {
  let spellsCount = 0;
  let creaturesCount = 0;
  const subtypeCounts = {};
  const themeCounts = {};

  for (const name of deckNames) {
    const cardInfo = db[name.toLowerCase()];
    if (!cardInfo) continue;

    const rawType = (cardInfo.raw_type || "").toLowerCase();
    
    // Skip lands unless they are also creatures
    if (rawType.includes("land") && !rawType.includes("creature")) {
      continue;
    }

    spellsCount++;

    // Creature subtype tallying
    if (rawType.includes("creature")) {
      creaturesCount++;
      const subs = cardInfo.subtypes || [];
      for (const sub of subs) {
        subtypeCounts[sub] = (subtypeCounts[sub] || 0) + 1;
      }
    }

    // Mechanical theme tallying
    const matchedThemes = scanMechanicalKeywords(cardInfo);
    for (const theme of matchedThemes) {
      themeCounts[theme] = (themeCounts[theme] || 0) + 1;
    }
  }

  // Calculate subtype density
  let maxSubtypeCount = 0;
  let dominantSubtype = "None";
  for (const [sub, count] of Object.entries(subtypeCounts)) {
    if (count > maxSubtypeCount) {
      maxSubtypeCount = count;
      dominantSubtype = sub;
    }
  }
  const subtypeDensity = creaturesCount > 0 ? (maxSubtypeCount / creaturesCount) * 100 : 0;

  // Calculate theme density
  let maxThemeCount = 0;
  let dominantTheme = "None";
  for (const [theme, count] of Object.entries(themeCounts)) {
    if (count > maxThemeCount) {
      maxThemeCount = count;
      dominantTheme = theme;
    }
  }
  const themeDensity = spellsCount > 0 ? (maxThemeCount / spellsCount) * 100 : 0;

  // Apply blend formula
  let cohesionScore = 0;
  if (creaturesCount < 10) {
    cohesionScore = Math.min(100, themeDensity * 1.5);
  } else {
    cohesionScore = Math.min(100, (subtypeDensity * 0.4) + (themeDensity * 0.9));
  }

  // Sort subtype and theme counts for breakdown
  const sortedSubtypes = Object.entries(subtypeCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .reduce((obj, [k, v]) => ({ ...obj, [k]: v }), {});

  const sortedThemes = Object.entries(themeCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .reduce((obj, [k, v]) => ({ ...obj, [k]: v }), {});

  return {
    cohesion_score: Math.round(cohesionScore),
    dominant_subtype: dominantSubtype,
    subtype_density: Math.round(subtypeDensity),
    dominant_theme: dominantTheme,
    theme_density: Math.round(themeDensity),
    subtype_counts: sortedSubtypes,
    theme_counts: sortedThemes
  };
}

/**
 * Performs Vorthos flavor clash analysis
 * @param {string[]} deckNames 
 * @param {Object} db 
 * @returns {Object} Flavor stats
 */
export function analyzeFlavorClashes(deckNames, db) {
  const planeCounts = {};
  const cardPlanes = {};

  for (const name of deckNames) {
    const cardInfo = db[name.toLowerCase()];
    if (!cardInfo) continue;

    const setCode = (cardInfo.set || "").toLowerCase();
    const plane = SET_TO_PLANE[setCode];
    if (plane) {
      planeCounts[plane] = (planeCounts[plane] || 0) + 1;
      cardPlanes[cardInfo.name] = plane;
    }
  }

  const planeEntries = Object.entries(planeCounts);
  if (planeEntries.length === 0) {
    return { dominant_plane: "Unknown", dominant_plane_count: 0, plane_counts: {}, clashing_cards: [] };
  }

  let dominantPlane = "Unknown";
  let dominantPlaneCount = 0;
  for (const [plane, count] of planeEntries) {
    if (count > dominantPlaneCount) {
      dominantPlaneCount = count;
      dominantPlane = plane;
    }
  }

  const clashingCards = [];
  // Only trigger warnings if we have at least 8 cards establishing this plane theme
  if (dominantPlaneCount >= 8) {
    const forbiddenPlanes = PLANE_CLASHES[dominantPlane] || new Set();
    for (const [cardName, plane] of Object.entries(cardPlanes)) {
      if (forbiddenPlanes.has(plane)) {
        clashingCards.push({
          card: cardName,
          card_plane: plane,
          dominant_plane: dominantPlane
        });
      }
    }
  }

  return {
    dominant_plane: dominantPlane,
    dominant_plane_count: dominantPlaneCount,
    plane_counts: planeCounts,
    clashing_cards: clashingCards
  };
}

const FAST_MANA_LIST = new Set([
  "mana crypt", "mana vault", "grim monolith", "chrome mox", 
  "mox opal", "mox diamond", "lotus petal", "jeweled lotus", 
  "lion's eye diamond", "ancient tomb"
]);

const FINISHER_REGEX = /win the game|loses the game|extra turn|additional combat phase|craterhoof behemoth|triumph of the hordes|overwhelming stampede|beastmaster ascension|akroma's will|torment of hailfire|insurrection|exquisite blood|thassa's oracle|laboratory maniac/i;

export function analyzeIntentionalExperience(deckNames, db, targetIX, targetBracket) {
  const alerts = [];
  let fastManaFound = [];
  let finisherCount = 0;

  for (const name of deckNames) {
    const lowerName = name.trim().toLowerCase();
    const cardInfo = db[lowerName];
    
    // Logic Heuristic A: Check for fast mana
    if (FAST_MANA_LIST.has(lowerName)) {
      fastManaFound.push(name);
    }

    // Logic Heuristic B: Check for finishers
    if (cardInfo) {
      const text = cardInfo.oracle_text || "";
      const type = cardInfo.raw_type || "";
      if (FINISHER_REGEX.test(text) || FINISHER_REGEX.test(type) || FINISHER_REGEX.test(cardInfo.name)) {
        finisherCount++;
      }
    }
  }

  // Warning for fast-mana in low/med/focused brackets (Tier 1, 2 or 3)
  if (targetBracket <= 3 && fastManaFound.length > 0) {
    alerts.push({
      type: "warning",
      title: "Bracket Mismatch",
      message: `Fast-mana acceleration (${fastManaFound.join(", ")}) found in a casual/precon/focused (Tier ${targetBracket}) deck list.`
    });
  }

  // Warning for zero finishers in combat/combo decks
  if (finisherCount === 0) {
    alerts.push({
      type: "info",
      title: "Value-Pile Alert",
      message: "Value-Pile: Deck lacks deterministic closing power. Consider adding 1-2 game-ending finishers."
    });
  }

  return {
    alerts,
    finisherCount,
    fastManaFound
  };
}
