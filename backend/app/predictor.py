import pandas as pd
import numpy as np
from datetime import datetime, timezone
import pytz
from dateutil import parser
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.live.nba.endpoints import scoreboard
from nba_api.stats.static import teams
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

# 1. SETUP LOOKUPS
team_lookup = {team['id']: team['full_name'] for team in teams.get_teams()}

# 2. FETCH SEASON DATA
print("Fetching season data...")
games = leaguegamefinder.LeagueGameFinder(
    season_nullable='2024-25',
    league_id_nullable='00'
).get_data_frames()[0]

games = games[games['SEASON_ID'].str.startswith('2')]
games['GAME_DATE'] = pd.to_datetime(games['GAME_DATE'])
games = games.sort_values(['GAME_ID', 'TEAM_ID'])

# 3. ADD OPPONENT POINTS & CALCULATE REST
opp = games[['GAME_ID', 'TEAM_ID', 'PTS']].rename(
    columns={'TEAM_ID': 'OPP_TEAM_ID', 'PTS': 'PTS_ALLOWED'}
)
games = games.merge(opp, on='GAME_ID')
games = games[games['TEAM_ID'] != games['OPP_TEAM_ID']]
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

# 5. FEATURE ENGINEERING
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

# 7. PREDICT TODAY'S GAMES (Using reference Live Data logic)
print("Fetching today's schedule from Live API...")
board = scoreboard.ScoreBoard()
games_list = board.games.get_dict()

if not games_list:
    print("No games today.")
    output = pd.DataFrame(columns=['HOME_TEAM', 'AWAY_TEAM', 'home_win_prob', 'game_time'])
else:
    rows = []
    # Set the timezone to Eastern
    est_tz = pytz.timezone('US/Eastern')

    for game in games_list:
        # Convert UTC string to EST object
        # Example: '2024-12-25T19:30:00Z' -> 7:30 PM ET
        game_time_est = parser.parse(game["gameTimeUTC"]).astimezone(est_tz)
        formatted_time = game_time_est.strftime('%I:%M %p ET')

        rows.append({
            'GAME_ID': game['gameId'],
            'HOME_TEAM_ID': game['homeTeam']['teamId'],
            'VISITOR_TEAM_ID': game['awayTeam']['teamId'],
            'game_time': formatted_time
        })

    today_games = pd.DataFrame(rows)

    latest_strength = games.sort_values('GAME_DATE').groupby('TEAM_ID').tail(1)[['TEAM_ID', 'rolling_net']]

    today_games = today_games.merge(
        latest_strength, left_on='HOME_TEAM_ID', right_on='TEAM_ID'
    ).merge(
        latest_strength, left_on='VISITOR_TEAM_ID', right_on='TEAM_ID', suffixes=('_home', '_away')
    )

    today_games['home_court'] = 1
    today_games['b2b_home'] = 0
    today_games['b2b_away'] = 0
    today_games['rest_diff'] = 0

    today_X = today_games[feature_cols]
    today_games['home_win_prob'] = model.predict_proba(today_X)[:, 1]
    today_games['HOME_TEAM'] = today_games['HOME_TEAM_ID'].map(team_lookup)
    today_games['AWAY_TEAM'] = today_games['VISITOR_TEAM_ID'].map(team_lookup)

    # Adding .copy() ensures 'output' is its own independent object
    output = today_games[
        ['HOME_TEAM', 'AWAY_TEAM', 'HOME_TEAM_ID', 'VISITOR_TEAM_ID', 'home_win_prob', 'game_time']].copy()

    # Now this line will run without the warning:
    output['abs_prob'] = output['home_win_prob'].apply(lambda x: x if x >= 0.5 else 1 - x)

    # Sorting: Highest absolute probability first
    output['abs_prob'] = output['home_win_prob'].apply(lambda x: x if x >= 0.5 else 1 - x)
    output = output.sort_values('abs_prob', ascending=False).drop(columns=['abs_prob'])

    print("Predictions ready!")
    print(output)
