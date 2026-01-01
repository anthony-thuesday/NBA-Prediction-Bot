import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  // 1. Initialize states
  const [games, setGames] = useState([]);      // Start with empty array to avoid .map() error
  const [loading, setLoading] = useState(true); // Show spinner while fetching
  const [error, setError] = useState(null);    // Track if backend is down

  useEffect(() => {
    // Replace with your actual Render URL (ensure it ends with /)
    const API_URL = "https://nbapredictbot3.onrender.com/predict/today";

    const fetchPredictions = async () => {
      try {
        setLoading(true);
        const response = await fetch(API_URL);

        if (!response.ok) {
          throw new Error(`Backend Error: ${response.status}`);
        }

        const data = await response.json();

        // Ensure data.games exists before setting state
        if (data && data.games) {
          setGames(data.games);
        } else {
          setGames([]);
        }
      } catch (err) {
        console.error("Fetch failed:", err);
        setError("Could not connect to the NBA Prediction server.");
      } finally {
        setLoading(false);
      }
    };

    fetchPredictions();
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>🏀 NBA Win Predictions</h1>
      </header>

      <main className="container">
        {loading && <div className="loader">Analyzing season data...</div>}

        {error && <div className="error-message">{error}</div>}

        {!loading && !error && games.length === 0 && (
          <p>No games scheduled for today or data is being updated.</p>
        )}

        <div className="games-grid">
          {/* Using optional chaining (?.) and empty array fallback as final safety */}
          {(games || []).map((game, index) => (
            <div key={index} className="game-card">
              <div className="teams">
                <span className="away">{game.away_team}</span>
                <span className="vs">@</span>
                <span className="home">{game.home_team}</span>
              </div>
              <div className="probability-bar">
                <div
                  className="fill"
                  style={{ width: `${(game.home_win_prob * 100)}%` }}
                ></div>
              </div>
              <p className="prob-text">
                Home Win Chance: <strong>{(game.home_win_prob * 100).toFixed(1)}%</strong>
              </p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}

export default App;