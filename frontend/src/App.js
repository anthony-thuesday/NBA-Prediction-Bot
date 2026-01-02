import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';

const API_BASE = "http://localhost:8000";

// --- Sub-component: Team History Table ---
const HistoryTable = ({ title, data }) => (
  <div className="history-col">
    <h4>{title}</h4>
    <table>
      <thead>
        <tr><th>Date</th><th>Opp</th><th>Res</th><th style={{ textAlign: 'right' }}>Score</th></tr>
      </thead>
      <tbody>
        {data.length > 0 ? data.map((g, i) => (
          <tr key={i}>
            <td>{g.date}</td>
            <td className="opp-cell"><span className="loc-symbol">{g.location}</span> {g.opponent}</td>
            <td className={g.wl === 'W' ? 'win' : 'loss'}>{g.wl}</td>
            <td style={{ textAlign: 'right' }}>{g.score}</td>
          </tr>
        )) : <tr><td colSpan="4" className="loading-text">Loading 2025-26 History...</td></tr>}
      </tbody>
    </table>
  </div>
);

// --- Sub-component: Team Display ---
const TeamDisplay = ({ label, id, name, score, isWinner }) => (
  <div className="team-container">
    <span className="team-label">{label}</span>
    <img src={`https://cdn.nba.com/logos/nba/${id}/global/L/logo.svg`} alt={name} />
    <h2 className="team-name" style={{ color: isWinner === false ? '#94a3b8' : 'white' }}>{name}</h2>
    {score !== undefined && <div className="final-pts">{score}</div>}
  </div>
);

const Navbar = () => (
  <nav className="navbar">
    <div className="nav-container">
      <Link to="/" className="nav-logo">🏀 PREDICT<span>NBA</span></Link>
      <div className="nav-links">
        <Link to="/" className="nav-item">Today's Predictions</Link>
        <Link to="/results" className="nav-item">Yesterday's Results</Link>
      </div>
    </div>
  </nav>
);

const YesterdayResults = () => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/results/yesterday`)
      .then(res => res.json())
      .then(data => {
        setResults(data.results || []);
        setLoading(false);
      });
  }, []);

  return (
    <div className="page-content">
      <header className="main-header">
        <h1>Yesterday's Scores</h1>
        <p className="current-date">Final results from NBA Action</p>
      </header>
      <div className="games-grid">
        {loading ? <p className="loading-text">Loading Scores...</p> :
          results.map((game, i) => (
            <div key={i} className="game-card no-hover">
              <div className="card-top"><span className="tbd-badge">FINAL</span></div>
              <div className="matchup-row">
                <TeamDisplay label="HOME" id={game.home_id} name={game.home_team} score={game.home_score} isWinner={game.home_score > game.away_score}/>
                <div className="vs-divider">VS</div>
                <TeamDisplay label="AWAY" id={game.away_id} name={game.away_team} score={game.away_score} isWinner={game.away_score > game.home_score}/>
              </div>
              <div className="prediction-box result-box">
                <p className="predict-label">WINNER</p>
                <h3 className="winner-name">{game.home_score > game.away_score ? game.home_team : game.away_team}</h3>
              </div>
            </div>
          ))
        }
      </div>
    </div>
  );
};

function App() {
  const [games, setGames] = useState([]);
  const [selectedGame, setSelectedGame] = useState(null);
  const [teamHistory, setTeamHistory] = useState({ home: [], away: [] });

  useEffect(() => {
    fetch(`${API_BASE}/predict/today`)
      .then(res => res.json())
      .then(data => {
        setGames(data.games || []);
        // Prefetch logic
        data.games?.forEach(g => {
          fetch(`${API_BASE}/team-history/${g.home_id}`);
          fetch(`${API_BASE}/team-history/${g.away_id}`);
        });
      });
  }, []);

  const handleMatchupClick = async (game) => {
    setSelectedGame(game);
    setTeamHistory({ home: [], away: [] });
    try {
      const [hRes, aRes] = await Promise.all([
        fetch(`${API_BASE}/team-history/${game.home_id}`),
        fetch(`${API_BASE}/team-history/${game.away_id}`)
      ]);
      const hData = await hRes.json();
      const aData = await aRes.json();
      setTeamHistory({ home: hData.history || [], away: aData.history || [] });
    } catch (err) { console.error(err); }
  };

  return (
    <Router>
      <div className="App">
        <Navbar />
        <Routes>
          <Route path="/" element={
            <div className="page-content">
              <header className="main-header">
                <h1>Daily Predictions</h1>
                <p className="current-date">{new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}</p>
              </header>
              <div className="games-grid">
                {games.map((game, i) => {
                  const isHomeFav = game.home_win_prob >= 50;
                  const prob = isHomeFav ? game.home_win_prob : (100 - game.home_win_prob).toFixed(1);
                  return (
                    <div key={i} className="game-card" onClick={() => handleMatchupClick(game)}>
                      <div className="card-top"><span className="tbd-badge">{game.game_time}</span></div>
                      <div className="matchup-row">
                        <TeamDisplay label="HOME" id={game.home_id} name={game.home_team} />
                        <div className="vs-divider">VS</div>
                        <TeamDisplay label="AWAY" id={game.away_id} name={game.away_team} />
                      </div>
                      <div className="prediction-box">
                        <p className="predict-label">PREDICTED WINNER</p>
                        <h3 className="winner-name">{isHomeFav ? game.home_team : game.away_team}</h3>
                        <p className="winner-percent">{prob}% Chance</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          } />
          <Route path="/results" element={<YesterdayResults />} />
        </Routes>

        {selectedGame && (
          <div className="modal-overlay" onClick={() => setSelectedGame(null)}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <h2 className="modal-title">Recent Performance</h2>
              <p className="modal-subtitle">2025-26 REGULAR SEASON</p>
              <div className="history-split">
                <HistoryTable title={selectedGame.home_team} data={teamHistory.home} />
                <HistoryTable title={selectedGame.away_team} data={teamHistory.away} />
              </div>
              <button className="close-btn" onClick={() => setSelectedGame(null)}>Close</button>
            </div>
          </div>
        )}
      </div>
    </Router>
  );
}

export default App;