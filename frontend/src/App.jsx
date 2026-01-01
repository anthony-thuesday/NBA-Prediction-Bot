import { useEffect, useState } from "react";
import "./App.css";

export default function App() {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
  const fetchData = async () => {
    try {
      // Use the Render URL directly
      const response = await fetch("https://nbapredictbot3.onrender.com/predict/today");
      const data = await response.json();
      setGames(data.games);
    } catch (error) {
      console.error("Error fetching NBA data:", error);
    }
  };
  fetchData();
}, []);

  return (
    <div style={{ maxWidth: 900, margin: "40px auto", fontFamily: "system-ui" }}>
      <h1>NBA Predictions</h1>

      {loading && <p>Loading…</p>}
      {err && <p style={{ color: "red" }}>{err}</p>}

      {!loading && !err && (
        <table width="100%" cellPadding="10" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #333" }}>
              <th>Home</th>
              <th>Away</th>
              <th>Home Win %</th>
            </tr>
          </thead>
          <tbody>
            {games.map((g, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #222" }}>
                <td>{g.home_team}</td>
                <td>{g.away_team}</td>
                <td>{Math.round(g.home_win_prob * 100)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
