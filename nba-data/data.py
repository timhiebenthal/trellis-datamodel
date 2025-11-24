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
    teams_df.to_csv("nba-data/teams.csv", index=False)
    teams_df.head()
    return


@app.cell
def _(pd):
    def save_endpoint_data(endpoint, file_name):
        df = pd.DataFrame(endpoint)
        df.to_csv(f"nba-data/{file_name}.csv", index=False)
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
def _(leaguegamefinder):
    seasons_to_fetch = ['2025-26', '2024-25']

    def get_season_games():
        all_games = []

        for season in seasons_to_fetch:
            print(f"Fetching game IDs for the {season} season...")

            gamefinder = leaguegamefinder.LeagueGameFinder(
                season_nullable=season,
                player_or_team_abbreviation='T' 
            )

            season_games = (gamefinder.get_data_frames()[0]
                .drop_duplicates()
                [["GAME_DATE", "GAME_ID"]]
                .assign(season=season)
                .to_dict(orient="records")
                  )

            all_games += season_games
            print(f"Found {len(season_games)} unique games for the season ...")

        print(f"Completed iteration for total of {len(all_games)} games")
        return all_games
    return (get_season_games,)


@app.cell
def _(get_season_games):
    all_games = get_season_games()
    return (all_games,)


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
def _():
    from tqdm import tqdm
    import time as t
    return t, tqdm


@app.cell
def _(all_games, get_gamestats, pd, t, tqdm):
    def get_all_gamestats():
        all_stats = []
        for game in tqdm(all_games[500:]):
            game_data = get_gamestats(game["GAME_ID"])
            all_stats.append(game_data)
            t.sleep(0.8)

        return pd.json_normalize(all_stats, record_path="player_stats", meta="game_id")

    all_stats_df = get_all_gamestats()
    return (all_stats_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Loop & Save data
    """)
    return


@app.cell
def _(all_stats_df, get_season_games, players, save_endpoint_data, teams):

    endpoints = [
        (teams.get_teams(), "teams"),
        (players.get_players(), "players"),
        (get_season_games(), "games"),
        (all_stats_df, "game_stats")
    ]

    for e in endpoints:
        save_endpoint_data(endpoint=e[0], file_name=e[1])
        #time.sleep(1)
        print("---")
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
