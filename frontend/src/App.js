import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Dynamic Date Formatting
  const today = new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  }).format(new Date());

  useEffect(() => {
    // Replace with your actual Render URL
    const API_URL = "https://nbapredictbot3.onrender.com/predict/today";

    const fetchPredictions = async () => {
      try {
        setLoading(true);
        const response = await fetch(API_URL);

        if (!response.ok) {
          throw new Error("Backend is waking up... Please refresh in 30 seconds.");
        }

        const data = await response.json();
        let fetchedGames = data.games || [];

        // SORTING: Organize by the highest certainty (safest bets first)
        fetchedGames.sort((a, b) => {
          const probA = Math.max(a.home_win_prob, 1 - a.home_win_prob);
          const probB = Math.max(b.home_win_prob, 1 - b.home_win_prob);
          return probB - probA;
        });

        setGames(fetchedGames);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchPredictions();
  }, []);

  return (
    <div className="App">
      <header>
        <h1>🏀 NBA Prediction Center</h1>
        <p className="current-date">{today}</p>
      </header>

      <main className="container">
        {loading && <div className="loader">Analyzing Season Data...</div>}

        {error && (
          <div className="error-message">
            <p><strong>Connection Issue:</strong> {error}</p>
          </div>
        )}

        {!loading && !error && games.length === 0 && (
          <div className="no-games">
            <p>No games scheduled for today.</p>
          </div>
        )}

        <div className="games-grid">
          {games.map((game, index) => {
            // Determine Favorite and Win Percentage
            const isHomeFavorite = game.home_win_prob >= 0.5;
            const favoriteTeam = isHomeFavorite ? game.home_team : game.away_team;
            const winChance = isHomeFavorite
              ? (game.home_win_prob * 100)
              : ((1 - game.home_win_prob) * 100);

            return (
              <div key={index} className="game-card">
                {/* Game Header: Time and Confidence Badge */}
                <div className="card-header">
                  <div className="game-time-tag">
                    {game.game_time || "TBD"}
                  </div>
                  {winChance > 70 && <div className="confidence-badge">High Confidence</div>}
                </div>

                {/* Team Matchup: Home on Left */}
                <div className="teams">
                  <div className="team-block">
                    <span className="team-label">HOME</span>
                    <span className="team-name">{game.home_team}</span>
                  </div>

                  <span className="vs">VS</span>

                  <div className="team-block">
                    <span className="team-label">AWAY</span>
                    <span className="team-name">{game.away_team}</span>
                  </div>
                </div>

                {/* Probability Visuals */}
                <div className="probability-container">
                  <div className="probability-bar">
                    <div
                      className="fill"
                      style={{ width: `${(game.home_win_prob * 100)}%` }}
                    ></div>
                  </div>

                  <div className="prediction-tag">
                    <span className="predicted-label">PREDICTED WINNER</span>
                    <span className="winner-name">{favoriteTeam}</span>
                    <span className="winner-percent">{winChance.toFixed(1)}% Chance</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}

export default App;