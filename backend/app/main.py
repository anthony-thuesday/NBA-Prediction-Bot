from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from nba_api.stats.endpoints import scoreboardv2, teamgamelogs, leaguegamefinder
from nba_api.stats.static import teams
from sklearn.linear_model import LogisticRegression
import pandas as pd
import uvicorn
from functools import lru_cache

# --- GLOBAL VARIABLES ---
# CHANGED: We now map the ID to 'full_name' and ensure keys are strings for reliable matching
team_lookup = {str(team['id']): team['full_name'] for team in teams.get_teams()}

# ADD THIS: Create a lookup for Abbreviation -> Full Name
abbrev_lookup = {team['abbreviation']: team['full_name'] for team in teams.get_teams()}
model = LogisticRegression(max_iter=1000)
latest_stats = pd.DataFrame()
feature_cols = ['rolling_net_home', 'rolling_net_away', 'b2b_home', 'b2b_away', 'rest_diff', 'home_court']


# --- LIFESPAN HANDLER (Replaces on_event) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, latest_stats
    print("🔄 Training Model with 2024-25 Data...")

    # 1. Fetch Training Data
    try:
        games = leaguegamefinder.LeagueGameFinder(season_nullable='2024-25', league_id_nullable='00').get_data_frames()[
            0]
        games = games[games['SEASON_ID'].str.startswith('2')]
        games['GAME_DATE'] = pd.to_datetime(games['GAME_DATE'])

        # 2. Calculate Net Ratings
        opp = games[['GAME_ID', 'TEAM_ID', 'PTS']].rename(columns={'TEAM_ID': 'OPP_ID', 'PTS': 'PTS_ALLOWED'})
        games = games.merge(opp, on='GAME_ID')
        games = games[games['TEAM_ID'] != games['OPP_ID']]
        games['diff'] = games['PTS'] - games['PTS_ALLOWED']
        games['rolling_net'] = games.groupby('TEAM_ID')['diff'].transform(lambda x: x.rolling(10, min_periods=1).mean())

        # 3. Train Model
        home = games[games['MATCHUP'].str.contains('vs.')].copy()
        away = games[games['MATCHUP'].str.contains('@')].copy()
        train_df = home.merge(away, on='GAME_ID', suffixes=('_home', '_away'))

        train_df['home_win'] = (train_df['WL_home'] == 'W').astype(int)
        train_df['home_court'] = 1
        train_df['rest_diff'] = 0
        train_df['b2b_home'] = 0
        train_df['b2b_away'] = 0

        model.fit(train_df[feature_cols].dropna(), train_df['home_win'].dropna())

        # 4. Save Stats
        latest_stats = games.sort_values('GAME_DATE').groupby('TEAM_ID').tail(1)
        print("✅ Model Trained & Ready.")
    except Exception as e:
        print(f"⚠️ Model Training Failed: {e}")

    yield  # Server runs here
    print("🛑 Shutting down...")


# --- APP SETUP ---
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=32)
def fetch_team_logs(team_id: int):
    return teamgamelogs.TeamGameLogs(
        team_id_nullable=team_id,
        season_nullable='2025-26',
        season_type_nullable='Regular Season'
    ).get_data_frames()[0]


# --- ENDPOINTS ---

@app.get("/predict/today")
def predict_today():
    try:
        today_str = datetime.now().strftime('%Y-%m-%d')
        sb = scoreboardv2.ScoreboardV2(game_date=today_str)
        header = sb.game_header.get_data_frame()

        if header.empty:
            return {"games": []}

        games_list = []
        for _, row in header.iterrows():
            h_id, a_id = int(row['HOME_TEAM_ID']), int(row['VISITOR_TEAM_ID'])

            # Get stats
            h_net = latest_stats[latest_stats['TEAM_ID'] == h_id]['rolling_net'].values[0] if h_id in latest_stats[
                'TEAM_ID'].values else 0
            a_net = latest_stats[latest_stats['TEAM_ID'] == a_id]['rolling_net'].values[0] if a_id in latest_stats[
                'TEAM_ID'].values else 0

            # Predict
            features = pd.DataFrame([[h_net, a_net, 0, 0, 0, 1]], columns=feature_cols)
            prob = model.predict_proba(features)[0][1] * 100

            # CHANGED: Using str() on IDs during lookup to ensure a match for full names
            games_list.append({
                "home_team": team_lookup.get(str(h_id), "Home"), "home_id": h_id,
                "away_team": team_lookup.get(str(a_id), "Away"), "away_id": a_id,
                "home_win_prob": round(prob, 1),
                "game_time": row['GAME_STATUS_TEXT'].strip()
            })

        # ADDED: Sorting by highest probability distance from 50%
        games_list.sort(key=lambda x: abs(x["home_win_prob"] - 50), reverse=True)

        return {"games": games_list}
    except Exception as e:
        print(f"Error predicting: {e}")
        return {"games": []}


@app.get("/results/yesterday")
def get_yesterday():
    try:
        date = (datetime.now() - timedelta(1)).strftime('%Y-%m-%d')
        sb = scoreboardv2.ScoreboardV2(game_date=date)
        header = sb.game_header.get_data_frame()
        line = sb.line_score.get_data_frame()

        results = []
        if not header.empty:
            for _, row in header.iterrows():
                h_id, a_id = row['HOME_TEAM_ID'], row['VISITOR_TEAM_ID']
                h_score = line[line['TEAM_ID'] == h_id]['PTS'].values[0]
                a_score = line[line['TEAM_ID'] == a_id]['PTS'].values[0]
                results.append({
                    "home_team": team_lookup.get(str(h_id)), "home_id": int(h_id), "home_score": int(h_score),
                    "away_team": team_lookup.get(str(a_id)), "away_id": int(a_id), "away_score": int(a_score)
                })
        return {"results": results, "date": date}
    except:
        return {"results": [], "date": ""}


@app.get("/team-history/{team_id}")
def get_history(team_id: int):
  try:
    df = fetch_team_logs(team_id)
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df.sort_values('GAME_DATE', ascending=False).head(5)

    history = []
    for _, row in df.iterrows():
      matchup = row['MATCHUP']
      is_away = "@" in matchup

      # 1. Extract the abbreviation (e.g., "GSW")
      opp_abbrev = matchup.split(' @ ')[-1] if is_away else matchup.split(' vs. ')[-1]

      # 2. Use our lookup to get the Full Name (e.g., "Golden State Warriors")
      # .get() will fallback to the abbreviation if for some reason the name isn't found
      full_opp_name = abbrev_lookup.get(opp_abbrev, opp_abbrev)

      history.append({
        "date": row['GAME_DATE'].strftime('%m/%d'),
        "opponent": full_opp_name,  # Now sending the full name!
        "wl": row['WL'],
        "score": f"{row['PTS']} - {int(row['PTS'] - row['PLUS_MINUS'])}",
        "location": "@ " if is_away else "vs "
      })
    return {"history": history}
  except Exception as e:
    print(f"Error in history endpoint: {e}")
    return {"history": []}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)