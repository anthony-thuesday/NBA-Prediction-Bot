# regular season only
games = games[games['SEASON_ID'].str.startswith('2')]
print(games.head(5))
for col in games.columns:
    print(col)