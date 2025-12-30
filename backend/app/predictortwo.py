import pandas as pd
import numpy as np
from nba_api.stats.endpoints import leaguegamefinder, scoreboardv2
from sklearn.linear_model import LogisticRegression
from datetime import datetime

# 1. Load & Clean Data
def load_season(s):
    df = leaguegamefinder.LeagueGameFinder(season_nullable=s, league_id_nullable='00').get_data_frames()[0]
    df = df[df['SEASON_ID'].str.startswith('2')].copy()
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    return df

games = pd.concat([load_season('2023-24'), load_season('2024-25'), load_season('2025-26')]).drop_duplicates(subset=['GAME_ID', 'TEAM_ID'])
games['season_weight'] = np.where(games['SEASON_ID'].str.contains('2025'), 1.5, 1.0)

# 2. Add Opponent Points & Rolling Stats
opp = games[['GAME_ID', 'TEAM_ID', 'PTS']].rename(columns={'TEAM_ID': 'OPP_TEAM_ID', 'PTS': 'PTS_ALLOWED'})
games = games.merge(opp, on='GAME_ID')
games = games[games['TEAM_ID'] != games['OPP_TEAM_ID']].drop_duplicates(subset=['GAME_ID', 'TEAM_ID'])
games = games.sort_values(['TEAM_ID', 'GAME_DATE'])
games['days_rest'] = games.groupby('TEAM_ID')['GAME_DATE'].diff().dt.days
games['back_to_back'] = (games['days_rest'] == 1).astype(int)
games['rolling_net'] = games.groupby('TEAM_ID')['PTS'].transform(lambda x: (x - games.loc[x.index, 'PTS_ALLOWED']).rolling(10, min_periods=3).mean())

# 3. Create Feature Matrix (Home vs Away)
home = games[games['MATCHUP'].str.contains('vs.')].copy()
away = games[games['MATCHUP'].str.contains('@')].copy()
df = home.merge(away, on='GAME_ID', suffixes=('_home', '_away'))
df['home_win'], df['home_court'], df['rest_diff'] = (df['WL_home'] == 'W').astype(int), 1, (df['days_rest_home'] - df['days_rest_away']).fillna(0)
df['sample_weight'] = (df['season_weight_home'] + df['season_weight_away']) / 2

# 4. Train Model
feature_cols = ['rolling_net_home', 'rolling_net_away', 'back_to_back_home', 'back_to_back_away', 'rest_diff', 'home_court']
train_df = df.dropna(subset=feature_cols)
model = LogisticRegression(max_iter=1000).fit(train_df[feature_cols], train_df['home_win'], sample_weight=train_df['sample_weight'])

# 5. Predict Today's Games (FIXED: Added .drop_duplicates on today's games)
today = scoreboardv2.ScoreboardV2(game_date=datetime.today().strftime('%m/%d/%Y')).get_data_frames()[0]
if not today.empty:
    today = today.drop_duplicates(subset=['GAME_ID'])
    latest = games.sort_values('GAME_DATE').groupby('TEAM_ID').last().reset_index()[['TEAM_ID', 'rolling_net', 'TEAM_ABBREVIATION']]
    preds = today[['GAME_ID', 'HOME_TEAM_ID', 'VISITOR_TEAM_ID']].merge(latest, left_on='HOME_TEAM_ID', right_on='TEAM_ID').merge(latest, left_on='VISITOR_TEAM_ID', right_on='TEAM_ID', suffixes=('_home', '_away'))
    preds['home_court'], preds['back_to_back_home'], preds['back_to_back_away'], preds['rest_diff'] = 1, 0, 0, 0
    preds['home_win_prob'] = model.predict_proba(preds[feature_cols])[:, 1]
    print(preds[['TEAM_ABBREVIATION_home', 'TEAM_ABBREVIATION_away', 'home_win_prob']].rename(columns={'TEAM_ABBREVIATION_home': 'HOME', 'TEAM_ABBREVIATION_away': 'AWAY'}).sort_values('home_win_prob', ascending=False).to_string(index=False))
else: print("No games today.")