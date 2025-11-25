import marimo

__generated_with = "0.18.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import json
    import os
    import pandas as pd
    return mo, pd


@app.cell
def _():
    from nba_api.stats.static import teams, players
    return players, teams


@app.cell
def _(pd, teams):
    teams_df = pd.DataFrame(teams.get_teams())
    teams_df.head()
    return


@app.cell
def _(pd):
    def save_endpoint_data(data, file_name):
        df = pd.DataFrame(data)
        df.to_csv(f"nba-data/data/{file_name}.csv", index=False)
        print(f"saved {len(df):,.0f} records for '{file_name}'")
        return df
    return (save_endpoint_data,)


@app.cell
def _(players):
    len(players.get_players())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Get Games
    """)
    return


@app.cell
def _():
    from nba_api.stats.endpoints import leaguegamefinder
    return (leaguegamefinder,)


@app.cell
def _(leaguegamefinder, pd):
    seasons_to_fetch = [
        '2025-26', 
        #'2024-25'
    ]

    START_DATE = '2025-10-01'
    END_DATE = '2025-11-30'

    def get_season_games():
        all_games = []

        for season in seasons_to_fetch:
            print(f"Fetching game IDs for the {season} season...")

            gamefinder = leaguegamefinder.LeagueGameFinder(
                season_nullable=season,
                season_type_nullable='Regular Season',
                player_or_team_abbreviation='T' 
            )

            season_games = (gamefinder.get_data_frames()[0]
                .drop_duplicates()
                [["GAME_DATE", "GAME_ID"]]
                .assign(season=season)
                .query("GAME_DATE >= @START_DATE and GAME_DATE <= @END_DATE")
                .to_dict(orient="records")
                  )

            all_games += season_games
            print(f"Found {len(season_games)} unique games for the season ...")

        print(f"Completed iteration for total of {len(all_games)} games")
        return pd.DataFrame(all_games)
    return (get_season_games,)


@app.cell
def _(get_season_games):
    all_games_df = get_season_games()
    return (all_games_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Loop & Save data
    """)
    return


@app.cell
def _(all_games_df, players, save_endpoint_data, teams):
    endpoints = [
        (teams.get_teams(), "teams"),
        (players.get_players(), "players"),
        (all_games_df, "games")
    ]

    for e in endpoints:
        save_endpoint_data(data=e[0], file_name=e[1])
        print("---")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Parse BoxScore Data
    """)
    return


@app.cell
def _():
    #boxscoretraditionalv3
    from nba_api.stats.endpoints import boxscoretraditionalv3
    return (boxscoretraditionalv3,)


@app.cell
def _(boxscoretraditionalv3):
    boxscoretraditionalv3.BoxScoreTraditionalV3(
        game_id="0022300061"
    ).get_dict().get("boxScoreTraditional")
    return


@app.cell
def _(boxscoretraditionalv3):
    def parse_player_boxscore(game_data):

        player_stats = []
        for team in ["homeTeam", "awayTeam"]:
            for player in game_data[team]["players"]:
                player_stats.append(
                    {
                     "team": game_data[team]["teamId"],
                     "player": player["personId"],
                     "stats": player["statistics"]
                    }
                 )
        return {  
            "game_id": game_data["gameId"],
            "away_team_id": game_data["awayTeamId"],
            "home_team_id": game_data["homeTeamId"],
            "player_stats": player_stats
        }

    def get_gamestats(game_id):
        stats = []
        game_data = boxscoretraditionalv3.BoxScoreTraditionalV3(
                game_id=game_id,
            ).get_dict().get("boxScoreTraditional")
        return parse_player_boxscore(game_data)
    return (get_gamestats,)


@app.cell
def _(get_gamestats):
    get_gamestats("0022500275")
    return


@app.cell
def _(all_games_df, get_gamestats, pd, save_endpoint_data):
    from tqdm import tqdm
    import time

    # iterate over games in monthly chunks
    all_games_monthly_df = all_games_df.assign(month = lambda x: x.GAME_DATE.str[:7])


    for selected_month in all_games_monthly_df["month"].unique():
        all_month_stats = []
        print(f"working on stats for month '{selected_month}' ...")

        chunk_df = all_games_monthly_df.query("month == @selected_month")
        for index, row in tqdm(chunk_df.iterrows(), total=chunk_df.shape[0]):
            game_data = get_gamestats(row["GAME_ID"])
            all_month_stats.append(game_data)

            # add small pause between iteration to avoid timeouts/rate-limits
            time.sleep(2.5)

        # expand data to player-grain and save as monthly .csv
        month_df = pd.json_normalize(all_month_stats, record_path="player_stats", meta="game_id")
        save_endpoint_data(month_df, f"game_stats_{selected_month}")
        time.sleep(10)
    return


if __name__ == "__main__":
    app.run()
