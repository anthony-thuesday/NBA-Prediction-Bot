import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

# Use an absolute import since we set PYTHONPATH=backend/app
import predictor

app = FastAPI(title="NBA Prediction Bot API")

# 1. CORS Middleware: Allows your React frontend to access this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Redirect Route: Sends users from "/" to "/predict/today" automatically
@app.get("/", include_in_schema=False)
async def root():
    """
    Redirects the base URL to the prediction endpoint.
    """
    return RedirectResponse(url="/predict/today")

# 3. Data Route: The actual endpoint your React app will fetch from
@app.get("/predict/today")
def get_predictions():
    """
    Fetches today's NBA predictions from the model logic in predictor.py.
    """
    try:
        # Convert the Pandas DataFrame from predictor.py into a list of dictionaries
        raw_data = predictor.output.to_dict(orient="records")

        formatted_games = []
        for game in raw_data:
            formatted_games.append({
                "home_team": game.get("HOME_TEAM"),
                "away_team": game.get("AWAY_TEAM"),
                "home_win_prob": round(float(game.get("home_win_prob", 0)), 4)
            })

        return {
            "status": "success",
            "count": len(formatted_games),
            "games": formatted_games
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 4. Local Runner (for testing on your Mac)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)