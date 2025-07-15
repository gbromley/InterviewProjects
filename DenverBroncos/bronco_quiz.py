
import polars as pl
import requests
import json

def calc_passer_rating(df: pl.DataFrame):
        qb_stats = (
        df
        .with_columns([
            # Completion percentage component
            ((pl.col('Completions') / pl.col('Attempts') - 0.3) * 5).alias('a_component'),
            ((pl.col('Yards')/ pl.col('Attempts') - 3.0) * 0.25).alias('b_component'),
            ((pl.col("Touchdowns") / pl.col('Attempts'))*20.0).alias("c_component"),
            (2.375-(pl.col("Interceptions")/pl.col("Attempts") * 25)).alias("d_component")
        ])
        .with_columns([
            # Cap each component between 0 and 2.375
            pl.col('a_component').clip(0, 2.375).alias('a_final'),
            pl.col('b_component').clip(0, 2.375).alias('b_final'),
            pl.col('c_component').clip(0, 2.375).alias('c_final'),
            pl.col('d_component').clip(0, 2.375).alias('d_final')
        ])
        .with_columns(
            # Calculate final passer rating
            ((pl.col('a_final') + pl.col('b_final') + 
            pl.col('c_final') + pl.col('d_final')) / 6 * 100).alias('PasserRating')
        )
        .sort(pl.col('PasserRating'), descending=True)
        .drop(['a_component', 'b_component', 'c_component', 'd_component',
            'a_final', 'b_final', 'c_final', 'd_final'])
    )

        return qb_stats.sort('PasserRating', descending=True)


def main():
    print("=" * 50)
    print(" QB Stats Analysis - Gabriel Bromley ".center(50, "="))
    print("=" * 50)
    print()
    print("=== Aquiring and Validating Data ===\n")
    
    # Convert Google Doc URL to export URL
    doc_url = "https://docs.google.com/document/d/1dVsl2f9sL4qr1-XYMfpCwaFFFsLWwUhS0a2kl1yMu7U/edit?tab=t.0"
    doc_id = doc_url.split('d/')[1].split('/')[0] 
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"

    # Fetch the document
    response = requests.get(export_url)

    # remove google added characters
    data = json.loads(response.text.strip("'").lstrip('\ufeff'))

    df = pl.DataFrame(data).explode('Games').unnest('Games')


    ### Data CLeaning ###
    print(df.describe())

    # Making the assumption that we can replace NULL with 0

    df = df.with_columns([
        # Counting stats: null means zero occurrences
        pl.col('Interceptions').fill_null(0),
        pl.col('Touchdowns').fill_null(0),
        pl.col('Sacks').fill_null(0)
    ])


    print("=== ANSWERS ===\n")
    #### 1. Which player had the highest single game Completion Percentage?

    top_games = (
        df
        .with_columns(
            (pl.col('Completions') / pl.col('Attempts') * 100).alias('CompletionPct')
        )
        .filter(pl.col('Attempts') > 0)
        .sort('CompletionPct', descending=True)
        .head(5)
        .select(['Player', 'Game', 'Completions', 'Attempts', 'CompletionPct'])
    )
    print(f"1. Highest single game Completion Percentage: {top_games['Player'][0]} ({top_games['CompletionPct'][0]:.1f}%)")


    #### 2. Which player had the lowest single game Yards Per Attempt? 

    lowest_ypa = (
        df.with_columns((pl.col('Yards')/ pl.col('Attempts')).alias('YardsPerAttempt'))
        .filter(pl.col('Attempts') > 0)
        .sort('YardsPerAttempt')
        .head(5)
        .select(['Player', 'Game', 'Completions', 'Attempts', 'YardsPerAttempt'])
    )
    print(f"2. Lowest single game Yards Per Attempt: {lowest_ypa['Player'][0]} ({lowest_ypa['YardsPerAttempt'][0]:.2f})")


    #### 3. Which player had the least Passing Yards for the season? 

    season_passing_totals = (
        df
        .group_by('Player')
        .agg(
            pl.col('Yards').sum().alias('TotalYards')
        )
        .sort('TotalYards')
        )
    print(f"3. Least Passing Yards for the season: {season_passing_totals['Player'][0]} ({season_passing_totals['TotalYards'][0]} yards)")


    #### 4. Which player had the most Touchdowns for the season? 


    season_TD_totals = (
        df
        .group_by("Player")
        .agg(
            pl.col("Touchdowns").sum().alias('TotalTouchdowns')
        )
        .sort('TotalTouchdowns', descending=True)
    )
    print(f"4. Most Touchdowns for the season: {season_TD_totals['Player'][0]} ({season_TD_totals['TotalTouchdowns'][0]} TDs)")


    #### 5. List the player names by their Season Completion Percentage in descending order. List the names in order, separated by a comma with no spaces like this: QB1,QB2,QB3,QB4,QB5 


    player_comp_percent = (
        df
        .group_by("Player")
        .agg([
            pl.col("Completions").sum().alias('TotalCompletions'),
            pl.col("Attempts").sum().alias('TotalAttempts')
        ])
        .with_columns(
            (pl.col('TotalCompletions') / pl.col('TotalAttempts') * 100).alias('CompletionPct')
        )
        .sort('CompletionPct', descending=True)
    )

    player_list = ','.join(player_comp_percent['Player'].to_list())
    print(f"5. Completion % ranking: {player_list}")

    #### 6. Which player had the highest single game Passer Rating?

    qb_stats = calc_passer_rating(df)

    top_qb = qb_stats.head(1).select('Player').item()
    passer_rating = qb_stats.head(1).select('PasserRating').item()

    print(f"6. Highest single game Passer Rating: {top_qb}")


    #### 7. What was the value of the highest single game Passer Rating?


    print(f"7. Value of highest single game Passer Rating: {passer_rating:.1f}")

    #### 8. Which player had the lowest single game Passer Rating? 

    lowest_passer_rating_player = (qb_stats.tail(1).select(["Player"]).item())
    lowest_passer_rating = (qb_stats.tail(1).select(["PasserRating"]).item())

    print(f"8. Lowest single game Passer Rating: {lowest_passer_rating_player}")

    #### 9. What was the value of the lowest single game Passer Rating?

    print(f"9. Value of the lowest single game Passer Rating was: {lowest_passer_rating:.1f}")

    #### 10. Which player had the highest season Passer Rating? 

    season_totals = (
        df
        .group_by('Player')
        .agg([
            pl.col('Attempts').sum(),     
            pl.col('Completions').sum(),  
            pl.col('Yards').sum(),        
            pl.col('Touchdowns').sum(),   
            pl.col('Interceptions').sum() 
        ])
    )
    seasonal_passer_rating = calc_passer_rating(season_totals)

    player = (seasonal_passer_rating
            .sort(pl.col("PasserRating"), descending=True)
            .head(1).select(["Player"])
            .item())

    print(f"10. Highest season Passer Rating: {player}")


    #### 11. Which player had the highest Passer Rating through Game1, Game2 and Game3?


    game_subset = df.sort(pl.col("Game")).head(3)


    game_subset = (
        df
        .filter(pl.col('Game').is_in(['Game1', 'Game2', 'Game3']))
        .group_by('Player')
        .agg([
            pl.col('Attempts').sum(),
            pl.col('Completions').sum(),
            pl.col('Yards').sum(),
            pl.col('Touchdowns').sum(),
            pl.col('Interceptions').sum()
        ])
    )
    game_subset_stats = calc_passer_rating(game_subset)

    player = (game_subset_stats
            .sort(pl.col("PasserRating"), descending=True)
            .head(1).select(["Player"])
            .item())

    print(f"11. {player} had the highest Passer Rating through Games 1-3")



    #### 12. Excluding each player’s highest and lowest single game Passer Rating, which player had the highest Passer Rating for the season?


    df = calc_passer_rating(df)
    df_filtered = (
        df
        .with_columns(
            pl.col('PasserRating').rank().over('Player').alias('rank_asc'),
            pl.col('PasserRating').rank(descending=True).over('Player').alias('rank_desc')
        )
        .filter((pl.col('rank_asc') > 1) & (pl.col('rank_desc') > 1))
    )
    season_totals_filtered = (
        df_filtered
        .group_by('Player')
        .agg([
            pl.col('Attempts').sum(),     
            pl.col('Completions').sum(),  
            pl.col('Yards').sum(),        
            pl.col('Touchdowns').sum(),   
            pl.col('Interceptions').sum(),
        ])
    )
    qb_stats_filtered = calc_passer_rating(season_totals_filtered)
    player =  (qb_stats_filtered
            .sort(pl.col("PasserRating"), descending=True)
            .head(1).select(["Player"])
            .item())

    print(f"12. Exluding highest and lowest single game Passer Rating, {player} had the highest Passer Rating for the season")


if __name__ == "__main__":
    main()
