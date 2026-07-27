# Based on the definitions of x% and y% in: ETF_Trading_Model\filters\good_universe_filter.py
# Rank first by x from high to low, then by y from high to low
# Finally, output the result to "ETF_Trading_Model\data\ranked_good_universe.csv"

import pandas as pd


def rank_good_universe(df: pd.DataFrame) -> pd.DataFrame:
    """Take the good_universe DataFrame and return it ranked by x and y."""
    # Rank first by x from high to low; when x is tied, rank by y from high to low
    ranked_df = df.sort_values(by=["x", "y"], ascending=[False, False]).reset_index(drop=True)

    # Add a rank column, numbered starting from 1
    ranked_df["rank"] = ranked_df.index + 1

    return ranked_df
