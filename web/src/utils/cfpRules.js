// Official Commander Format Panel (CFP) Game Changers List (40 cards)
export const GAME_CHANGERS = new Set([
  // Tutors
  "enlightened tutor", "mystical tutor", "demonic tutor", "vapiric tutor", "vampiric tutor", "imperial seal", "survival of the fittest",
  // Lockout / Stax
  "drannith magistrate", "opposition agent", "trinisphere", "glacial chasm", "the tabernacle at pendrell vale",
  // Fast Mana
  "chrome mox", "grim monolith", "mox diamond", "mana vault", "ancient tomb",
  // Resource advantage
  "smothering tithe", "trouble in pairs", "rhystic study", "the one ring", "jeska's will", "bolas's citadel",
  // Mana denial
  "vorinclex, voice of hunger",
  // Combo / Storm
  "lion's eye diamond", "underworld breach", "ad nauseam",
  // High-powered lands
  "gaea's cradle", "serra's sanctum",
  // Game ending outliers
  "thassa's oracle", "cyclonic rift", "expropriate",
  // Cheating / resource engines
  "jin-gitaxias, core augur",
  // Free Counterspells
  "fierce guardianship", "force of will",
  // Powerful commanders
  "kinnan, bonder prodigy", "yuriko, the tiger's shadow", "winota, joiner of forces", "grand arbiter augustin iv", "tergrid, god of fright", "urza, lord high artificer"
]);

// Mass Land Denial card names
const LAND_DENIAL_NAMES = new Set([
  "armageddon", "ruination", "sunder", "winter orb", "blood moon", "back to basics", 
  "ravages of war", "cataclysm", "obliterate", "jokulhaups", "mana vortex"
]);

// Mass Land Denial oracle regex
const LAND_DENIAL_REGEX = /(destroy|exile|bounce) all lands|lands don't untap|lands are (swamps|mountains|plains|forests|islands|wastes)/i;

// Non-land tutor oracle regex
const TUTOR_REGEX = /search your library for a (card|creature|artifact|enchantment|instant|sorcery|planeswalker)/i;

// Extra turn oracle regex
const EXTRA_TURN_REGEX = /take an extra turn/i;

export const isGameChanger = (name) => {
  if (!name) return false;
  return GAME_CHANGERS.has(name.toLowerCase().trim());
};

export const isMassLandDenial = (card) => {
  if (!card) return false;
  const name = (card.name || "").toLowerCase().trim();
  if (LAND_DENIAL_NAMES.has(name)) return true;
  const text = card.oracle_text || "";
  return LAND_DENIAL_REGEX.test(text);
};

export const isTutor = (card) => {
  if (!card) return false;
  const text = card.oracle_text || "";
  return TUTOR_REGEX.test(text);
};

export const isExtraTurn = (card) => {
  if (!card) return false;
  const text = card.oracle_text || "";
  return EXTRA_TURN_REGEX.test(text);
};
