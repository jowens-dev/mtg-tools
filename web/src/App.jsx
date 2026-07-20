import React, { useState } from 'react';
import { fetchCardsMetadata } from './utils/scryfall';
import { parseDecklistText, calculateCohesionScore, analyzeFlavorClashes } from './utils/themeEngine';
import { analyzeStress } from './utils/stressTester';

function App() {
  const [activeTab, setActiveTab] = useState('input');
  const [commander, setCommander] = useState('Kozilek, the Great Distortion');
  const [bracket, setBracket] = useState(2);
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

  const handleAnalyze = async () => {
    if (!decklist.trim()) return;
    setLoading(true);
    
    try {
      // Parse deck lists
      const parsedNames = parseDecklistText(decklist);
      
      // Batch fetch card details from Scryfall API
      const db = await fetchCardsMetadata(parsedNames);
      
      // Run theme engine calculations
      const cohesion = calculateCohesionScore(parsedNames, db);
      const flavor = analyzeFlavorClashes(parsedNames, db);
      
      // Run stress-tester engine calculations
      const stress = analyzeStress(parsedNames, db);
      
      setResults({
        cohesion,
        flavor,
        stress,
        totalCards: parsedNames.length
      });
      setAnalyzed(true);
      setActiveTab('cohesion');
    } catch (error) {
      alert("Error analyzing deck list. Check API connectivity.");
      console.error(error);
    } finally {
      setLoading(false);
    }
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
                <label className="form-label">Target Power Bracket (Tier: {bracket})</label>
                <input 
                  type="range" 
                  min="1" 
                  max="4" 
                  className="text-input" 
                  value={bracket}
                  onChange={(e) => setBracket(parseInt(e.target.value))}
                  style={{ height: '8px', padding: 0 }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginTop: '4px', color: 'var(--text-accent)' }}>
                  <span>Tier 1: Casual</span>
                  <span>Tier 2: Focused</span>
                  <span>Tier 3: High Power</span>
                  <span>Tier 4: cEDH</span>
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
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-accent)', marginTop: '8px' }}>
                      Core Ingestion: Lands ({results.stress.landsCount}/37 target) | Ramp ({results.stress.rampCount}/10 target) | Draw ({results.stress.drawCount}/10 target)
                    </p>
                  </div>
                </div>
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
      </nav>
    </div>
  );
}

export default App;
