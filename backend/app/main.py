from nba_api.stats.library.parameters import SeasonAll, SeasonTypeAllPlayer


@app.get("/team-history/{team_id}")
def get_team_history(team_id: int):
    # Strictly lock to the 2025-26 Regular Season
    gamefinder = leaguegamefinder.LeagueGameFinder(
        team_id_nullable=team_id,
        season_nullable='2025-26',  # Force current season
        season_type_nullable='Regular Season',  # Exclude pre-season/playoffs
        league_id_nullable='00'  # NBA only (excludes G-League)
    )
    df = gamefinder.get_data_frames()[0]

    # Ensure we are sorting by date to get the most recent games first
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df.sort_values('GAME_DATE', ascending=False).head(10)

    history = []
    for _, row in df.iterrows():
        # Parsing the opponent from the matchup string (e.g., "LAL @ GSW")
        matchup = row['MATCHUP']
        opponent = matchup.split(' vs. ')[-1] if ' vs. ' in matchup else matchup.split(' @ ')[-1]

        # Calculate opponent score
        opp_score = int(row['PTS'] - row['PLUS_MINUS'])

        history.append({
            "date": row['GAME_DATE'].strftime('%m/%d'),  # Will now show 12/31, 12/28, etc.
            "opponent": opponent,
            "wl": row['WL'],
            "score": f"{int(row['PTS'])} - {opp_score}"
        })
    return {"history": history}