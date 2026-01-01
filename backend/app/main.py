from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# IMPORTANT: This line must be active for the data to load!
from predictor import output

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/predict/today")
def get_predictions():
    # Convert the Pandas DataFrame from predictor.py into JSON
    raw_data = output.to_dict(orient="records")

    formatted_games = []
    for game in raw_data:
        formatted_games.append({
            "home_team": game.get("HOME_TEAM"),
            "away_team": game.get("AWAY_TEAM"),
            "home_win_prob": float(game.get("home_win_prob", 0))
        })

    return {"games": formatted_games}

if __name__ == "__main__":
    import uvicorn
    import os
    # Cloud services provide a 'PORT' variable automatically
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)