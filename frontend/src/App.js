import React, { useState, useEffect } from 'react';
import './App.css';

const HistoryTable = ({ title, data }) => (
  <div className="history-col">
    <h4>{title}</h4>
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Opp</th>
          <th>Res</th>
          <th style={{ textAlign: 'right' }}>Score</th>
        </tr>
      </thead>
      <tbody>
        {(data || []).length > 0 ? (
          (data || []).map((g, i) => (
            <tr key={i}>
              <td>{g.date}</td>
              <td className="opp-cell">{g.opponent}</td>
              <td className={g.wl === 'W' ? 'win' : 'loss'}>{g.wl}</td>
              <td style={{ textAlign: 'right' }}>{g.score}</td>
            </tr>
          ))
        ) : (
          <tr><td colSpan="4">Loading 2025-26 Data...</td></tr>
        )}
      </tbody>
    </table>
  </div>
);

function App() {
  const [games, setGames] = useState([]);
  const [selectedGame, setSelectedGame] = useState(null);
  const [teamHistory, setTeamHistory] = useState({ home: [], away: [] });

  const API_BASE = "http://localhost:8000";
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
  });

  useEffect(() => {
    fetch(`${API_BASE}/predict/today`)
      .then(res => res.json())
      .then(data => setGames(data.games || []))
      .catch(err => console.error(err));
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
    <div className="App">
      <header className="main-header">
        <h1>🏀 NBA Prediction Center</h1>
        <p className="current-date">{today}</p>
      </header>

      <div className="games-grid">
        {games.map((game, i) => {
          const isHomeFav = game.home_win_prob >= 50;
          const favoriteName = isHomeFav ? game.home_team : game.away_team;
          const displayProb = isHomeFav ? game.home_win_prob : (100 - game.home_win_prob).toFixed(1);

          return (
            <div key={i} className="game-card" onClick={() => handleMatchupClick(game)}>
              <div className="card-top">
                <span className="tbd-badge">{game.game_time}</span>
                {displayProb > 75 && <span className="conf-badge">HIGH CONFIDENCE</span>}
              </div>

              <div className="matchup-row">
                <div className="team-container">
                  <span className="team-label">HOME</span>
                  <img src={`https://cdn.nba.com/logos/nba/${game.home_id}/global/L/logo.svg`} alt="home" />
                  <h2 className="team-name">{game.home_team}</h2>
                </div>
                <div className="vs-divider">VS</div>
                <div className="team-container">
                  <span className="team-label">AWAY</span>
                  <img src={`https://cdn.nba.com/logos/nba/${game.away_id}/global/L/logo.svg`} alt="away" />
                  <h2 className="team-name">{game.away_team}</h2>
                </div>
              </div>

              <div className="prob-line">
                <div className="prob-bg"><div className="prob-fill" style={{ width: `${displayProb}%` }}></div></div>
              </div>

              <div className="prediction-box">
                <p className="predict-label">PREDICTED WINNER</p>
                <h3 className="winner-name">{favoriteName}</h3>
                <p className="winner-percent">{displayProb}% Chance</p>
              </div>
            </div>
          );
        })}
      </div>

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
  );
}

export default App;