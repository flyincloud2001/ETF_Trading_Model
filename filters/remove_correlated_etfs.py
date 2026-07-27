# Some different ETFs may track the same stocks, or move in the same way. This file specifically filters out ETFs that move the same way, keeping only the one with the largest market cap (or another reasonable standard) as the representative

import itertools

import pandas as pd
import yfinance as yf

# Correlation coefficient threshold; above this value the ETFs are considered to move the same way
CORRELATION_THRESHOLD = 0.95


def remove_correlated_etfs(symbols: list[str]) -> list[str]:
    """Take a list of ETF symbols and return the subset with same-moving ETFs removed."""
    if len(symbols) < 2:
        return list(symbols)

    # Fetch the past 3 years of close prices for all ETFs in one batch
    try:
        raw = yf.download(
            symbols,
            period="3y",
            auto_adjust=True,
            group_by="ticker",
        )
    except Exception:
        # If the batch fetch fails, keep all symbols
        return list(symbols)

    # Build the close-price series for each ETF; if a single symbol fails to fetch, keep it as-is and exclude it from correlation comparison
    close_prices = {}
    for symbol in symbols:
        try:
            series = raw[symbol]["Close"]
            if series is None or series.dropna().empty:
                continue
            close_prices[symbol] = series
        except Exception:
            continue

    if len(close_prices) < 2:
        return list(symbols)

    price_df = pd.DataFrame(close_prices)
    returns_df = price_df.pct_change()

    # Calculate the pairwise Pearson correlation matrix across all ETFs
    corr_matrix = returns_df.corr(method="pearson")

    valid_symbols = list(close_prices.keys())

    # Find all pairs whose correlation exceeds the threshold, and sort by correlation coefficient from high to low, for the greedy algorithm to process in order
    pairs = []
    for sym_a, sym_b in itertools.combinations(valid_symbols, 2):
        corr_value = corr_matrix.loc[sym_a, sym_b]
        if pd.notna(corr_value) and corr_value > CORRELATION_THRESHOLD:
            pairs.append((corr_value, sym_a, sym_b))
    pairs.sort(key=lambda item: item[0], reverse=True)

    total_assets_cache = {}

    def get_total_assets(symbol):
        # Look up and cache totalAssets, to avoid looking up the same symbol repeatedly
        if symbol not in total_assets_cache:
            try:
                total_assets_cache[symbol] = yf.Ticker(symbol).info.get("totalAssets")
            except Exception:
                total_assets_cache[symbol] = None
        return total_assets_cache[symbol]

    excluded = set()

    # Greedy algorithm: process pairs starting from the highest correlation; symbols already excluded no longer participate in subsequent comparisons
    for _corr_value, sym_a, sym_b in pairs:
        if sym_a in excluded or sym_b in excluded:
            continue

        assets_a = get_total_assets(sym_a)
        assets_b = get_total_assets(sym_b)

        if assets_a is not None and assets_b is not None:
            # Keep the one with the larger totalAssets
            if assets_a >= assets_b:
                excluded.add(sym_b)
            else:
                excluded.add(sym_a)
        elif assets_a is not None:
            excluded.add(sym_b)
        elif assets_b is not None:
            excluded.add(sym_a)
        else:
            # Neither has a totalAssets value; keep the one whose symbol comes first alphabetically
            if sym_a < sym_b:
                excluded.add(sym_b)
            else:
                excluded.add(sym_a)

    # Return in the original input order, with symbols in the excluded set removed
    return [symbol for symbol in symbols if symbol not in excluded]
