import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Note: Use a regular import if you set PYTHONPATH, or .predictor if not
try:
    from .predictor import output
except ImportError:
    from backend.app.predictor import output
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # This allows Vercel to talk to Render
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def get_predictions():
    """Serving data directly at the root to avoid 404s"""
    raw_data = output.to_dict(orient="records")
    formatted_games = []
    for game in raw_data:
        formatted_games.append({
            "home_team": game.get("HOME_TEAM"),
            "away_team": game.get("AWAY_TEAM"),
            "home_win_prob": float(game.get("home_win_prob", 0))
        })
    return {"games": formatted_games}

# Keep this for your React fetch if you already typed the URL
@app.get("/predict/today")
def predict_today():
    return get_predictions()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)