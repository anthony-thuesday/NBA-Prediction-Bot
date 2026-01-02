from datetime import datetime

from nba_api.stats.endpoints import leaguegamefinder, scoreboardv2
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from nba_api.stats.static import teams
import pandas as pd

# Build TEAM_ID -> TEAM_NAME lookup
team_lookup = {
    team['id']: team['full_name']
    for team in teams.get_teams()
}

# Example: apply to any dataframe that has TEAM_ID
# df['TEAM_NAME'] = df['TEAM_ID'].map(team_lookup)



games = leaguegamefinder.LeagueGameFinder(
    season_nullable='2024-25',
    league_id_nullable='00'
).get_data_frames()[0]

# regular season only
games = games[games['SEASON_ID'].str.startswith('2')]

games['GAME_DATE'] = pd.to_datetime(games['GAME_DATE'])
games = games.sort_values(['GAME_ID', 'TEAM_ID'])

# -------------------------
# 2. ADD OPPONENT POINTS (CRITICAL FIX)
# -------------------------
opp = games[['GAME_ID', 'TEAM_ID', 'PTS']].rename(
    columns={'TEAM_ID': 'OPP_TEAM_ID', 'PTS': 'PTS_ALLOWED'}
)

games = games.merge(
    opp,
    on='GAME_ID'
)

games = games[games['TEAM_ID'] != games['OPP_TEAM_ID']]

# -------------------------
# 3. REST + BACK-TO-BACK
# -------------------------
games = games.sort_values(['TEAM_ID', 'GAME_DATE'])

games['prev_game_date'] = games.groupby('TEAM_ID')['GAME_DATE'].shift(1)
games['days_rest'] = (games['GAME_DATE'] - games['prev_game_date']).dt.days
games['back_to_back'] = (games['days_rest'] == 1).astype(int)

# -------------------------
# 4. TEAM STRENGTH (ROLLING NET)
# -------------------------
games['point_diff'] = games['PTS'] - games['PTS_ALLOWED']

games['rolling_net'] = (
    games.groupby('TEAM_ID')['point_diff']
    .rolling(10, min_periods=3)
    .mean()
    .reset_index(level=0, drop=True)
)

# -------------------------
# 5. HOME / AWAY SPLIT
# -------------------------
home = games[games['MATCHUP'].str.contains('vs.')].copy()
away = games[games['MATCHUP'].str.contains('@')].copy()

df = home.merge(
    away,
    on='GAME_ID',
    suffixes=('_home', '_away')
)

df['home_win'] = (df['WL_home'] == 'W').astype(int)
df['home_court'] = 1
df['rest_diff'] = df['days_rest_home'] - df['days_rest_away']
df['b2b_home'] = df['back_to_back_home']
df['b2b_away'] = df['back_to_back_away']

# -------------------------
# 6. FEATURE MATRIX
# -------------------------
feature_cols = [
    'rolling_net_home',
    'rolling_net_away',
    'b2b_home',
    'b2b_away',
    'rest_diff',
    'home_court'
]

df = df.dropna(subset=feature_cols)

X = df[feature_cols]
y = df['home_win']

# -------------------------
# 7. TRAIN MODEL
# -------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, shuffle=False
)

model = LogisticRegression(max_iter=1000)
model.fit(X_train, y_train)


# -------------------------
# 8. PREDICT TODAY'S GAMES
# -------------------------
today = scoreboardv2.ScoreboardV2(
    game_date=datetime.today().strftime('%m/%d/%Y')
).get_data_frames()[0]

if today.empty:
    print("No games today.")
else:
    today_games = today[['GAME_ID', 'HOME_TEAM_ID', 'VISITOR_TEAM_ID']]

    latest_strength = (
        games.sort_values('GAME_DATE')
        .groupby('TEAM_ID')
        .tail(1)[['TEAM_ID', 'rolling_net']]
    )

    today_games = today_games.merge(
        latest_strength,
        left_on='HOME_TEAM_ID',
        right_on='TEAM_ID'
    ).merge(
        latest_strength,
        left_on='VISITOR_TEAM_ID',
        right_on='TEAM_ID',
        suffixes=('_home', '_away')
    )

    today_games['home_court'] = 1
    today_games['b2b_home'] = 0
    today_games['b2b_away'] = 0
    today_games['rest_diff'] = 0

    today_X = today_games[feature_cols]

    today_games['home_win_prob'] = model.predict_proba(today_X)[:, 1]

today_games['HOME_TEAM'] = today_games['HOME_TEAM_ID'].map(team_lookup)
today_games['AWAY_TEAM'] = today_games['VISITOR_TEAM_ID'].map(team_lookup)

output = (
    today_games[
        ['HOME_TEAM', 'AWAY_TEAM', 'home_win_prob']
    ]
    .sort_values('home_win_prob', ascending=False)
)

print(output)