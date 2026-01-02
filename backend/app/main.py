from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from nba_api.stats.endpoints import scoreboardv2, teamgamelogs
from functools import lru_cache
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=32)
def fetch_team_logs(team_id: int):
    logs = teamgamelogs.TeamGameLogs(
        team_id_nullable=team_id,
        season_nullable='2025-26',
        season_type_nullable='Regular Season'
    )
    return logs.get_data_frames()[0]


@app.get("/predict/today")
def predict_today():
    # Your existing prediction logic here
    return {
        "games": [
            {"home_team": "LAL", "home_id": 1610612747, "away_team": "GSW", "away_id": 1610612744,
             "home_win_prob": 55.2, "game_time": "7:30 PM"},
            {"home_team": "BOS", "home_id": 1610612738, "away_team": "MIA", "away_id": 1610612748,
             "home_win_prob": 62.1, "game_time": "8:00 PM"}
        ]
    }


@app.get("/team-history/{team_id}")
def get_team_history(team_id: int):
    try:
        df = fetch_team_logs(team_id)
        df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
        df = df.sort_values('GAME_DATE', ascending=False).head(10)
        history = []
        for _, row in df.iterrows():
            matchup = row['MATCHUP']
            location = "@" if " @ " in matchup else ""
            opponent = matchup.split(' @ ')[-1] if "@" in location else matchup.split(' vs. ')[-1]
            history.append({
                "date": row['GAME_DATE'].strftime('%m/%d'),
                "location": location,
                "opponent": opponent,
                "wl": row['WL'],
                "score": f"{row['PTS']} - {int(row['PTS'] - row['PLUS_MINUS'])}"
            })
        return {"history": history}
    except Exception as e:
        return {"history": []}


@app.get("/results/yesterday")
def get_yesterday_results():
    try:
        # Get yesterday's date
        yesterday = (datetime.now() - timedelta(1)).strftime('%Y-%m-%d')
        sb = scoreboardv2.ScoreboardV2(game_date=yesterday)
        data = sb.get_dict()['resultSets'][0]
        headers = data['headers']
        rows = data['rowSet']

        results = []
        for row in rows:
            g = dict(zip(headers, row))
            results.append({
                "game_id": g['GAME_ID'],
                "home_team": g['HOME_TEAM_ABBREVIATION'],
                "home_id": g['HOME_TEAM_ID'],
                "home_score": g['HOME_PTS'] or 0,
                "away_team": g['VISITOR_TEAM_ABBREVIATION'],
                "away_id": g['VISITOR_TEAM_ID'],
                "away_score": g['VISITOR_PTS'] or 0,
                "status": g['GAME_STATUS_TEXT']
            })
        return {"results": results}
    except Exception as e:
        return {"results": [], "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)