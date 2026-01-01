from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse  # Updated import

# This remains the same
from .predictor import output

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. MOVE THIS TO THE TOP
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/predict/today")

# 2. YOUR DATA ROUTE
@app.get("/predict/today")
def get_predictions():
    raw_data = output.to_dict(orient="records")
    formatted_games = []
    for game in raw_data:
        formatted_games.append({
            "home_team": game.get("HOME_TEAM"),
            "away_team": game.get("AWAY_TEAM"),
            "home_win_prob": float(game.get("home_win_prob", 0))
        })
    return {"games": formatted_games}