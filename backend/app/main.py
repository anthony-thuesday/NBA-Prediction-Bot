import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import pytz

# Import the output dataframe from your predictor script
try:
    from .predictor import output
except ImportError:
    from backend.app.predictor import output

app = FastAPI()

# Enable CORS so your Vercel frontend can access your Render backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def get_predictions():
    """
    Converts the predictor output into a JSON format the frontend can understand.
    Includes the new 'game_time' field.
    """
    # orient="records" creates a list of dictionaries
    raw_data = output.to_dict(orient="records")
    formatted_games = []

    for game in raw_data:
        formatted_games.append({
            "home_team": game.get("HOME_TEAM"),
            "away_team": game.get("AWAY_TEAM"),
            "home_win_prob": float(game.get("home_win_prob", 0)),
            # ADDED: This pulls the formatted time from predictor.py
            "game_time": game.get("game_time", "TBD")
        })

    return {"games": formatted_games}


# This keeps your existing React fetch URL working
@app.get("/predict/today")
def predict_today():
    return get_predictions()


if __name__ == "__main__":
    # Ensure we use the correct US Eastern time for logging or debugging
    est = pytz.timezone('US/Eastern')
    today_str = datetime.now(est).strftime('%Y-%m-%d')
    print(f"Server starting for NBA date: {today_str}")

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)