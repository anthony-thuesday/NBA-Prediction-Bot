from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# We will return the data directly to avoid redirect issues
from .predictor import output

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_formatted_data():
    """Helper function to get your NBA data"""
    raw_data = output.to_dict(orient="records")
    return [{
        "home_team": game.get("HOME_TEAM"),
        "away_team": game.get("AWAY_TEAM"),
        "home_win_prob": float(game.get("home_win_prob", 0))
    } for game in raw_data]

@app.get("/")
def home():
    # If they visit the main link, give them the data immediately
    return {"status": "success", "games": get_formatted_data()}

@app.get("/predict/today")
def predict_today():
    # Keep this so your React app link still works
    return {"games": get_formatted_data()}