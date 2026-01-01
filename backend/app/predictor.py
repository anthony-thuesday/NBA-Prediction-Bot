import pandas as pd
import numpy as np
from datetime import datetime
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.live.nba.endpoints import scoreboard
from nba_api.stats.static import teams
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

# 1. SETUP LOOKUPS
team_lookup = {
    team['id']: team['full_name']
    for team in teams.get_teams()
}

# 2. FETCH SEASON DATA (Historical for training)
print("Fetching season data...")
games = leaguegamefinder.LeagueGameFinder(
    season_nullable='2024-25',
    league_id_nullable='00'
).get_data_frames()[0]

games = games[games['SEASON_ID'].str.startswith('2')]
games['GAME_DATE'] = pd.to_datetime(games['GAME_DATE'])
games = games.sort_values(['GAME_ID', 'TEAM_ID'])

# 3. ADD OPPONENT POINTS
opp = games[['GAME_ID', 'TEAM_ID', 'PTS']].rename(
    columns={'TEAM_ID': 'OPP_TEAM_ID', 'PTS': 'PTS_ALLOWED'}
)
games = games.merge(opp, on='GAME_ID')
games = games[games['TEAM_ID'] != games['OPP_TEAM_ID']]

# 4. CALCULATE REST AND STRENGTH
games = games.sort_values(['TEAM_ID', 'GAME_DATE'])
games['prev_game_date'] = games.groupby('TEAM_ID')['GAME_DATE'].shift(1)
games['days_rest'] = (games['GAME_DATE'] - games['prev_game_date']).dt.days
games['back_to_back'] = (games['days_rest'] == 1).astype(int)
games['point_diff'] = games['PTS'] - games['PTS_ALLOWED']

games['rolling_net'] = (
    games.groupby('TEAM_ID')['point_diff']
    .rolling(10, min_periods=3)
    .mean()
    .reset_index(level=0, drop=True)
)

# 5. SPLIT AND FEATURE ENGINEERING
home = games[games['MATCHUP'].str.contains('vs.')].copy()
away = games[games['MATCHUP'].str.contains('@')].copy()

df = home.merge(away, on='GAME_ID', suffixes=('_home', '_away'))
df['home_win'] = (df['WL_home'] == 'W').astype(int)
df['home_court'] = 1
df['rest_diff'] = df['days_rest_home'] - df['days_rest_away']
df['b2b_home'] = df['back_to_back_home']
df['b2b_away'] = df['back_to_back_away']

feature_cols = ['rolling_net_home', 'rolling_net_away', 'b2b_home', 'b2b_away', 'rest_diff', 'home_court']
df = df.dropna(subset=feature_cols)

# 6. TRAIN MODEL
print("Training model...")
X = df[feature_cols]
y = df['home_win']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

model = LogisticRegression(max_iter=1000)
model.fit(X_train, y_train)

# 7. PREDICT TODAY'S GAMES (Using Live Scoreboard V3 for stable times)
print("Fetching today's schedule...")
sb = scoreboard.ScoreBoard()
data = sb.get_dict()
games_list = data.get('scoreboard', {}).get('games', [])

if not games_list:
    print("No games today.")
    output = pd.DataFrame(columns=['HOME_TEAM', 'AWAY_TEAM', 'home_win_prob', 'game_time'])
else:
    # Build today_games from the Live V3 data
    rows = []
    for g in games_list:
        rows.append({
            'GAME_ID': g['gameId'],
            'HOME_TEAM_ID': g['homeTeam']['teamId'],
            'VISITOR_TEAM_ID': g['awayTeam']['teamId'],
            'raw_time': g['gameTimeEST']  # e.g. "2024-12-25T19:30:00Z"
        })

    today_games = pd.DataFrame(rows)

    # 1. Format the game_time to be clean (e.g. "7:30 PM ET")
    # This remains static even after the game starts
    today_games['game_time'] = pd.to_datetime(today_games['raw_time']).dt.strftime('%I:%M %p ET')

    # 2. Merge with latest strength (rolling_net) for both teams
    latest_strength = (
        games.sort_values('GAME_DATE')
        .groupby('TEAM_ID')
        .tail(1)[['TEAM_ID', 'rolling_net']]
    )

    today_games = today_games.merge(
        latest_strength, left_on='HOME_TEAM_ID', right_on='TEAM_ID'
    ).merge(
        latest_strength, left_on='VISITOR_TEAM_ID', right_on='TEAM_ID', suffixes=('_home', '_away')
    )

    # 3. Setup features for model prediction
    today_games['home_court'] = 1
    today_games['b2b_home'] = 0
    today_games['b2b_away'] = 0
    today_games['rest_diff'] = 0

    today_X = today_games[feature_cols]
    today_games['home_win_prob'] = model.predict_proba(today_X)[:, 1]

    # 4. Map IDs to Team Names
    today_games['HOME_TEAM'] = today_games['HOME_TEAM_ID'].map(team_lookup)
    today_games['AWAY_TEAM'] = today_games['VISITOR_TEAM_ID'].map(team_lookup)

    # 5. Final Output Cleanup
    output = today_games[['HOME_TEAM', 'AWAY_TEAM', 'home_win_prob', 'game_time']]

    # Sorting: Highest absolute probability (strongest favorites) first
    output['abs_prob'] = output['home_win_prob'].apply(lambda x: x if x >= 0.5 else 1 - x)
    output = output.sort_values('abs_prob', ascending=False).drop(columns=['abs_prob'])

    print("Predictions ready!")
    print(output)