import pandas as pd
import numpy as np
from datetime import datetime
from nba_api.stats.endpoints import leaguegamefinder, scoreboardv2
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
import requests
import nba_api



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
print(games.head(5))