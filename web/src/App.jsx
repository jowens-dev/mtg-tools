import React, { useState } from 'react';
import { fetchCardsMetadata } from './utils/scryfall';
import { parseDecklistText, calculateCohesionScore, analyzeFlavorClashes, analyzeIntentionalExperience } from './utils/themeEngine';
import { analyzeStress } from './utils/stressTester';
import { detectBrokenChains, fetchSpiceRecommendations } from './utils/spiceInjector';

function App() {
  const [activeTab, setActiveTab] = useState('input');
  const [commander, setCommander] = useState('Kozilek, the Great Distortion');
  const [bracket, setBracket] = useState(2);
  const [targetIX, setTargetIX] = useState('Aggro-Combat');
  const [decklist, setDecklist] = useState(
    `// Commander\n` +
    `1 Kozilek, the Great Distortion\n\n` +
    `// Lands\n` +
    `37 Wastes\n\n` +
    `// Spells\n` +
    `1 Sol Ring\n` +
    `1 Mana Vault\n` +
    `1 Thran Dynamo\n` +
    `1 Mind Stone\n` +
    `1 Worn Powerstone\n` +
    `1 Everflowing Chalice\n` +
    `1 Hedron Archive\n` +
    `1 Kozilek's Channeler\n` +
    `1 Palladium Myr\n` +
    `1 Gilded Lotus\n` +
    `1 Kozilek's Command\n` +
    `1 Endbringer\n` +
    `1 Solemn Simulacrum\n` +
    `1 All Is Dust\n` +
    `1 Titan's Presence\n` +
    `1 Not of This World\n` +
    `1 Introduction to Prophecy\n` +
    `1 Warping Wail\n` +
    `1 Spatial Contortion\n` +
    `1 Swiftfoot Boots\n` +
    `1 Lightning Greaves\n` +
    `1 Soul of New Phyrexia`
  );
  
  const [loading, setLoading] = useState(false);
  const [analyzed, setAnalyzed] = useState(false);
  const [results, setResults] = useState(null);
  
  const [brokenChains, setBrokenChains] = useState([]);
  const [spiceRecommendations, setSpiceRecommendations] = useState([]);
  const [spiceLoading, setSpiceLoading] = useState(false);
  const [selectedChainIndex, setSelectedChainIndex] = useState(0);

  const handleAnalyze = async () => {
    if (!decklist.trim()) return;
    setLoading(true);
    
    try {
      // 1. Fetch Commander details dynamically from Scryfall
      let commanderCardInfo = null;
      try {
        const res = await fetch(`https://api.scryfall.com/cards/named?exact=${encodeURIComponent(commander)}`);
        if (res.ok) {
          const data = await res.json();
          let types = [];
          let subtypes = [];
          const typeLine = data.type_line || "";
          if (typeLine) {
            const parts = typeLine.split("—");
            types = parts[0].trim().split(" ").map(t => t.toLowerCase());
            if (parts[1]) {
              subtypes = parts[1].trim().split(" ").filter(Boolean).map(s => s.toLowerCase());
            }
          }
          commanderCardInfo = {
            name: data.name,
            raw_type: typeLine,
            types,
            subtypes,
            oracle_text: data.oracle_text || "",
            colors: data.color_identity || []
          };
        }
      } catch (e) {
        console.error("Could not fetch commander info from Scryfall:", e);
      }

      // 2. Parse deck lists
      const parsedNames = parseDecklistText(decklist);
      
      // 3. Batch fetch card details from Scryfall API
      const db = await fetchCardsMetadata(parsedNames);
      
      // 4. Run theme calculations
      const cohesion = calculateCohesionScore(parsedNames, db);
      const flavor = analyzeFlavorClashes(parsedNames, db);
      const ix = analyzeIntentionalExperience(parsedNames, db, targetIX, bracket);
      
      // 5. Run stress-tester engine calculations
      const stress = analyzeStress(parsedNames, db, commanderCardInfo, cohesion);
      
      // 6. Broken chain detection
      const chains = detectBrokenChains(parsedNames, db);
      setBrokenChains(chains);
      setSelectedChainIndex(0);
      setSpiceRecommendations([]);
      
      setResults({
        cohesion,
        flavor,
        ix,
        stress,
        totalCards: parsedNames.length,
        commanderInfo: commanderCardInfo
      });
      setAnalyzed(true);

      // Trigger spice fetch for first broken chain
      if (chains.length > 0) {
        setSpiceLoading(true);
        const firstChain = chains[0];
        const colorIdentity = commanderCardInfo ? commanderCardInfo.colors : [];
        const recs = await fetchSpiceRecommendations(firstChain.queryKeyword, colorIdentity);
        setSpiceRecommendations(recs);
        setSpiceLoading(false);
      }
      
      setActiveTab('cohesion');
    } catch (error) {
      alert("Error analyzing deck list. Check API connectivity.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectChain = async (index) => {
    setSelectedChainIndex(index);
    setSpiceLoading(true);
    setSpiceRecommendations([]);
    const chain = brokenChains[index];
    const colorIdentity = results?.commanderInfo ? results.commanderInfo.colors : [];
    const recs = await fetchSpiceRecommendations(chain.queryKeyword, colorIdentity);
    setSpiceRecommendations(recs);
    setSpiceLoading(false);
  };

  const getCohesionStyleClass = (score) => {
    if (score >= 75) return 'cohesion-excellent';
    if (score >= 50) return 'cohesion-moderate';
    return 'cohesion-low';
  };

  const getCohesionText = (score) => {
    if (score >= 75) return 'Excellent';
    if (score >= 50) return 'Moderate';
    return 'Low Cohesion';
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <img src="/logo.png" alt="Loreweaver Logo" className="logo-img" />
        <h1 className="app-title">Loreweaver</h1>
      </header>

      {/* Main Tab Switcher */}
      <main className="tab-content">
        {activeTab === 'input' && (
          <div className="tab-panel">
            <h2>Deck Analysis Input</h2>
            
            <div className="card">
              <div className="form-group">
                <label className="form-label">Commander Name</label>
                <input 
                  type="text" 
                  className="text-input" 
                  value={commander}
                  onChange={(e) => setCommander(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Target Intentional Experience (IX)</label>
                <select 
                  className="text-input"
                  value={targetIX}
                  onChange={(e) => setTargetIX(e.target.value)}
                >
                  <option value="Aggro-Combat">Aggro-Combat (Combat focused, damage modifiers)</option>
                  <option value="Grindy Value Engine">Grindy Value Engine (Graveyard, draw, end-step triggers)</option>
                  <option value="Deterministic Combo">Deterministic Combo (Infinite loops, tutors, untapping)</option>
                  <option value="Political/Interactive">Political/Interactive (Voting, choices, group play)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Target Power Bracket (Tier: {bracket})</label>
                <input 
                  type="range" 
                  min="1" 
                  max="5" 
                  className="text-input" 
                  value={bracket}
                  onChange={(e) => setBracket(parseInt(e.target.value))}
                  style={{ height: '8px', padding: 0 }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', marginTop: '4px', color: 'var(--text-accent)' }}>
                  <span>1: Battlecruiser</span>
                  <span>2: Precon+</span>
                  <span>3: Focused</span>
                  <span>4: Optimized</span>
                  <span>5: cEDH</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Paste Decklist</label>
                <textarea 
                  className="textarea-input"
                  value={decklist}
                  onChange={(e) => setDecklist(e.target.value)}
                  placeholder="1 Sol Ring&#10;1 Mana Crypt..."
                />
              </div>

              <button 
                className="btn-action" 
                onClick={handleAnalyze}
                disabled={loading}
              >
                {loading ? 'Analyzing...' : 'Analyze Deck'}
              </button>
            </div>
          </div>
        )}

        {activeTab === 'cohesion' && (
          <div className="tab-panel">
            <h2>Thematic Cohesion Dashboard</h2>

            {!analyzed ? (
              <div className="empty-state">
                <div className="empty-icon">🔮</div>
                <p>No analysis loaded. Go to the Input tab and run "Analyze Deck" first.</p>
              </div>
            ) : loading ? (
              <div className="loader-container">
                <div className="loader-spinner"></div>
                <p>Ingesting data and calculating themes...</p>
              </div>
            ) : (
              <div>
                {/* Intentional Experience Warning Alerts */}
                {results.ix.alerts.length > 0 && (
                  <div className="card" style={{ border: '1px solid var(--color-orange)', backgroundColor: 'rgba(230, 126, 34, 0.05)' }}>
                    <div className="form-label" style={{ color: 'var(--color-orange)' }}>⚠️ Experience Warnings</div>
                    {results.ix.alerts.map((alert, i) => (
                      <div key={i} style={{ marginBottom: '8px', fontSize: '0.85rem', lineHeight: '1.4' }}>
                        <span style={{ fontWeight: 'bold', color: alert.type === 'warning' ? 'var(--color-red)' : 'var(--color-orange)' }}>
                          [{alert.title}]
                        </span>{' '}
                        {alert.message}
                      </div>
                    ))}
                  </div>
                )}

                {/* Cohesion Score card */}
                <div className="card" style={{ textAlign: 'center' }}>
                  <div className="form-label">Theme Cohesion Score</div>
                  <div className={`score-badge ${getCohesionStyleClass(results.cohesion.cohesion_score)}`}>
                    {results.cohesion.cohesion_score}/100
                  </div>
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-accent)' }}>
                    Rating: {getCohesionText(results.cohesion.cohesion_score)}
                  </p>
                </div>

                {/* Vorthos Flavor Profile card */}
                <div className="card">
                  <div className="form-label">Flavor Profile</div>
                  {results.flavor.dominant_plane_count >= 8 ? (
                    <div>
                      <p style={{ fontWeight: 'bold', color: results.flavor.clashing_cards.length > 0 ? 'var(--color-red)' : 'var(--color-green)' }}>
                        {results.flavor.dominant_plane} Centric ({results.flavor.dominant_plane_count} Cards)
                        {results.flavor.clashing_cards.length > 0 ? ' | Vorthos Clash Detected' : ' | Flavor Cohesive'}
                      </p>
                      
                      {results.flavor.clashing_cards.length > 0 && (
                        <div style={{ marginTop: '12px' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--color-red)' }}>Outliers:</span>
                          <div style={{ marginTop: '6px' }}>
                            {results.flavor.clashing_cards.map((c, i) => (
                              <div key={i} className="clash-card-item">
                                <span className="clash-card-name">{c.card}</span> ({c.card_plane} card in a {c.dominant_plane} deck)
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p style={{ color: 'var(--text-white)', fontWeight: 'bold' }}>Diverse (Mixed Planes)</p>
                  )}
                </div>

                {/* Theme Breakdowns card */}
                <div className="card">
                  <div className="form-label">Thematic Clusters</div>
                  
                  <div className="list-header">Creature Subtypes</div>
                  {Object.keys(results.cohesion.subtype_counts).length > 0 ? (
                    Object.entries(results.cohesion.subtype_counts).map(([sub, count]) => (
                      <div key={sub} className="theme-row">
                        <span style={{ textTransform: 'capitalize' }}>{sub}</span>
                        <span className="theme-count">{count}</span>
                      </div>
                    ))
                  ) : (
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-accent)', padding: '6px 0' }}>None</p>
                  )}

                  <div className="list-header">Mechanical Themes</div>
                  {Object.keys(results.cohesion.theme_counts).length > 0 ? (
                    Object.entries(results.cohesion.theme_counts).map(([theme, count]) => (
                      <div key={theme} className="theme-row">
                        <span>{theme}</span>
                        <span className="theme-count">{count}</span>
                      </div>
                    ))
                  ) : (
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-accent)', padding: '6px 0' }}>None</p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'stress' && (
          <div className="tab-panel">
            <h2>Engine Stress-Tester Dashboard</h2>

            {!analyzed ? (
              <div className="empty-state">
                <div className="empty-icon">📊</div>
                <p>No analysis loaded. Go to the Input tab and run "Analyze Deck" first.</p>
              </div>
            ) : loading ? (
              <div className="loader-container">
                <div className="loader-spinner"></div>
                <p>Calculating engine statistics...</p>
              </div>
            ) : (
              <div>
                {/* CDI Dashboard card */}
                <div className="card">
                  <div className="metric-row">
                    <div className="metric-header">
                      <span className="metric-title" style={{ color: 'var(--text-accent)' }}>Commander Dependency (CDI)</span>
                      <span className="metric-value" style={{ color: results.stress.cdiRating === 'HIGH' ? 'var(--color-red)' : results.stress.cdiRating === 'MEDIUM' ? 'var(--color-orange)' : 'var(--color-green)' }}>
                        {results.stress.cdiRating} ({results.stress.cdiScore}/100)
                      </span>
                    </div>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-main)', marginTop: '4px', lineHeight: '1.4' }}>
                      Maps how heavily the 99 payoffs rely on the commander generator to execute their strategy.
                    </p>

                    {results.stress.glassCannonAlert && (
                      <div style={{ marginTop: '12px', padding: '10px', backgroundColor: 'rgba(226, 74, 74, 0.1)', border: '1px solid var(--color-red)', borderRadius: '6px', fontSize: '0.8rem', color: 'var(--color-red)', fontWeight: 'bold' }}>
                        [!] Glass Cannon Alert: High CDI, but deck has less than 8 protection spells ({results.stress.protectionCount} found). Add more protective cards!
                      </div>
                    )}
                  </div>
                </div>

                {/* 1. Fragility Index card */}
                <div className="card">
                  <div className="metric-row">
                    <div className="metric-header">
                      <span className="metric-title" style={{ color: 'var(--text-accent)' }}>1. Fragility Index</span>
                      <span className="metric-value" style={{ color: results.stress.fragilityColor }}>
                        {results.stress.fragilityRating}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.9rem', marginBottom: '8px', color: 'var(--text-main)' }}>
                      Adjusted Score: {results.stress.adjustedFragility.toFixed(2)} (Average: {results.stress.avgFragility.toFixed(2)})
                    </p>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-accent)', lineHeight: '1.4' }}>
                      Permanents: Creatures ({results.stress.creaturesCount}) | Artifacts ({results.stress.artifactsCount}) | Enchantments ({results.stress.enchantmentsCount}) | Planeswalkers ({results.stress.planeswalkersCount}) | Protection Spells ({results.stress.protectionCount})
                    </p>
                    
                    {results.stress.adjustedFragility >= 0.6 && (
                      <div style={{ marginTop: '12px', padding: '10px', backgroundColor: 'rgba(226, 74, 74, 0.1)', border: '1px solid var(--color-red)', borderRadius: '6px', fontSize: '0.8rem', color: 'var(--color-red)', fontWeight: 'bold' }}>
                        [!] WARNING: High risk of board wipe disruption. Consider adding more protection.
                      </div>
                    )}
                  </div>
                </div>

                {/* 2. Multiplayer Table-Pressure card */}
                <div className="card">
                  <div className="metric-row">
                    <div className="metric-header">
                      <span className="metric-title" style={{ color: 'var(--text-accent)' }}>2. Multiplayer Table-Pressure</span>
                      <span className="metric-value">{results.stress.tablePressureScore}%</span>
                    </div>
                    
                    <div className="progress-container" style={{ margin: '8px 0 16px 0' }}>
                      <div 
                        className="progress-fill" 
                        style={{ 
                          width: `${results.stress.tablePressureScore}%`,
                          backgroundColor: results.stress.tablePressureScore >= 70 ? 'var(--color-red)' : results.stress.tablePressureScore >= 40 ? 'var(--color-orange)' : 'var(--color-green)'
                        }}
                      ></div>
                      <span className="progress-text">Pressure Rating: {results.stress.tablePressureScore}%</span>
                    </div>
                    
                    <div className="form-label" style={{ fontSize: '0.8rem', marginBottom: '6px' }}>Scaling Multiplayer Spells ({results.stress.scalingSpells.length})</div>
                    {results.stress.scalingSpells.length > 0 ? (
                      <div className="scrolling-list">
                        {results.stress.scalingSpells.map((spell, i) => (
                          <div key={i} className="list-item">{spell}</div>
                        ))}
                      </div>
                    ) : (
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-accent)' }}>None found.</p>
                    )}
                  </div>
                </div>

                {/* 3. Draw Consistency card */}
                <div className="card">
                  <div className="metric-row">
                    <div className="metric-header">
                      <span className="metric-title" style={{ color: 'var(--text-accent)' }}>3. Engine Consistency</span>
                      <span className="metric-value" style={{ color: results.stress.consistencyColor }}>
                        {results.stress.consistencyRating}
                      </span>
                    </div>
                    <p style={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'var(--text-white)', margin: '4px 0' }}>
                      Draw Probability: {(results.stress.jointProb * 100).toFixed(1)}%
                    </p>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-accent)', lineHeight: '1.4' }}>
                      Probability of drawing &ge;3 lands, &ge;1 ramp spell, and &ge;1 draw spell by turn 6 (sample of 13 cards).
                    </p>

                    {(results.stress.commanderFulfillsRamp || results.stress.commanderFulfillsDraw) && (
                      <div style={{ margin: '10px 0', padding: '8px', backgroundColor: 'rgba(39, 174, 96, 0.08)', borderRadius: '6px', fontSize: '0.8rem', color: 'var(--color-green)' }}>
                        {results.stress.commanderFulfillsRamp && "✓ Commander fulfills RAMP engine (Guaranteed Turn 0 draw: reduced 99 requirement by 25%)\n"}
                        {results.stress.commanderFulfillsDraw && "✓ Commander fulfills DRAW engine (Guaranteed Turn 0 draw: reduced 99 requirement by 25%)"}
                      </div>
                    )}

                    <p style={{ fontSize: '0.8rem', color: 'var(--text-accent)', marginTop: '8px' }}>
                      Core Ingestion: Lands ({results.stress.landsCount}/37 target) | Ramp ({results.stress.rampCount}/{results.stress.rampTarget} target) | Draw ({results.stress.drawCount}/{results.stress.drawTarget} target)
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'spice' && (
          <div className="tab-panel">
            <h2>Proactive Spice Injector</h2>

            {!analyzed ? (
              <div className="empty-state">
                <div className="empty-icon">🌶️</div>
                <p>No analysis loaded. Go to the Input tab and run "Analyze Deck" first.</p>
              </div>
            ) : loading ? (
              <div className="loader-container">
                <div className="loader-spinner"></div>
                <p>Searching for broken chains...</p>
              </div>
            ) : brokenChains.length === 0 ? (
              <div className="card" style={{ textAlign: 'center', padding: '30px 20px' }}>
                <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>✓</div>
                <h3>All Theme Chains Intact</h3>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-accent)', marginTop: '8px' }}>
                  Your generators (cards placing counters/creating tokens) and payoffs (doubling season/aristocrat outlets) are perfectly balanced!
                </p>
              </div>
            ) : (
              <div>
                {/* Selector for broken chains */}
                <div className="form-group">
                  <label className="form-label">Select Broken Chain to Fix</label>
                  <select 
                    className="text-input"
                    value={selectedChainIndex}
                    onChange={(e) => handleSelectChain(parseInt(e.target.value))}
                  >
                    {brokenChains.map((chain, i) => (
                      <option key={i} value={i}>{chain.theme}: {chain.reason}</option>
                    ))}
                  </select>
                </div>

                <div className="card" style={{ border: '1px solid var(--color-orange)', backgroundColor: 'rgba(230, 126, 34, 0.03)' }}>
                  <div className="form-label" style={{ color: 'var(--color-orange)' }}>Broken Chain Analysis</div>
                  <p style={{ fontSize: '0.9rem', lineHeight: '1.4' }}>
                    Loreweaver identified that your deck supports the <strong>{brokenChains[selectedChainIndex].theme}</strong> theme, but lacks sufficient <strong>{brokenChains[selectedChainIndex].missingType}s</strong> to execute it reliably.
                  </p>
                </div>

                {/* Spice recommendations carousel */}
                <div className="form-label" style={{ marginBottom: '8px' }}>Recommended Niche Alternatives (Anti-Staple Filter Active)</div>
                {spiceLoading ? (
                  <div className="loader-container">
                    <div className="loader-spinner"></div>
                    <p>Consulting Scryfall for niche cards...</p>
                  </div>
                ) : spiceRecommendations.length > 0 ? (
                  <div className="carousel-container" style={{ display: 'flex', overflowX: 'auto', gap: '16px', paddingBottom: '12px' }}>
                    {spiceRecommendations.map((card, idx) => (
                      <div 
                        key={idx} 
                        className="card" 
                        style={{ 
                          flex: '0 0 280px', 
                          marginBottom: 0, 
                          border: '1px solid var(--border-purple)',
                          backgroundColor: 'var(--bg-panel)'
                        }}
                      >
                        {card.image_url && (
                          <img 
                            src={card.image_url} 
                            alt={card.name} 
                            style={{ width: '100%', borderRadius: '8px', marginBottom: '12px', display: 'block' }} 
                          />
                        )}
                        <h3 style={{ fontSize: '1rem', color: 'var(--text-white)', display: 'flex', justifyContent: 'space-between' }}>
                          <span>{card.name}</span>
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-accent)' }}>{card.mana_cost}</span>
                        </h3>
                        <p style={{ fontSize: '0.75rem', color: 'var(--text-accent)', marginBottom: '8px', fontStyle: 'italic' }}>
                          {card.type_line} (Rank #{card.edhrec_rank})
                        </p>
                        <p style={{ fontSize: '0.8rem', lineHeight: '1.4', color: 'var(--text-main)' }}>
                          {card.oracle_text}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-accent)' }}>Could not load recommendations. Check internet connection.</p>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Bottom Nav tabs bar */}
      <nav className="bottom-nav">
        <button 
          className={`nav-tab ${activeTab === 'input' ? 'active' : ''}`}
          onClick={() => setActiveTab('input')}
        >
          <span className="nav-icon">📥</span>
          <span>Input</span>
        </button>
        <button 
          className={`nav-tab ${activeTab === 'cohesion' ? 'active' : ''}`}
          onClick={() => setActiveTab('cohesion')}
        >
          <span className="nav-icon">🔮</span>
          <span>Cohesion</span>
        </button>
        <button 
          className={`nav-tab ${activeTab === 'stress' ? 'active' : ''}`}
          onClick={() => setActiveTab('stress')}
        >
          <span className="nav-icon">📊</span>
          <span>Stress</span>
        </button>
        <button 
          className={`nav-tab ${activeTab === 'spice' ? 'active' : ''}`}
          onClick={() => setActiveTab('spice')}
        >
          <span className="nav-icon">🌶️</span>
          <span>Spice</span>
        </button>
      </nav>
    </div>
  );
}

export default App;
