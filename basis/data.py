"""Load the FRED data (yields, swap rates, SOFR) and build the swap spreads."""
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
MATURITIES = {"1Y": 1, "2Y": 2, "3Y": 3, "5Y": 5, "7Y": 7, "10Y": 10, "20Y": 20, "30Y": 30}


def load(name, folder=DATA):
    return pd.read_csv(Path(folder) / f"{name}.csv", index_col="date", parse_dates=True)


def swap_spreads(folder=DATA):
    """Swap rate minus Treasury yield of the same maturity, in bp (2000-2016)."""
    swaps = load("swap_rates", folder)
    tsy = load("treasury_yields", folder).reindex(swaps.index)
    return (100 * (swaps - tsy[swaps.columns])).dropna().round(1)


def curve_yield(row, years):
    """Treasury yield (%) for any maturity, by linear interpolation of the curve."""
    x = [MATURITIES[c] for c in MATURITIES]
    return float(np.interp(years, x, row[list(MATURITIES)].astype(float)))


def spread_stats(spreads):
    """Average swap spread by period, plus when it first went below zero."""
    periods = {"2000-2007": ("2000", "2007"), "2008-2009 (crisis)": ("2008", "2009"),
               "2010-2014": ("2010", "2014"), "2015-2016": ("2015", "2016")}
    table = pd.DataFrame({name: spreads.loc[a:b].mean() for name, (a, b) in periods.items()}).T
    table.loc["minimum"] = spreads.min()
    table.loc["% of days < 0 (2015-16)"] = 100 * (spreads.loc["2015":] < 0).mean()
    monthly = spreads.resample("ME").mean()      # monthly average, to skip one-day blips
    first = {c: (monthly[c][monthly[c] < 0].index[0].strftime("%b %Y")
                 if (monthly[c] < 0).any() else "never") for c in monthly}
    return table.round(1), pd.Series(first, name="first_month_below_zero")
