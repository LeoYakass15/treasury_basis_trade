"""Bonus with real Bloomberg data (29 Oct 2026): should Yakass enter the trade today?

Rule: enter only if the CTD implied repo beats the repo rate by at least 10bp
(the margin that pays for costs and the risk of a squeeze).
"""
from pathlib import Path

import pandas as pd

from basis.data import DATA, load

MIN_EDGE_BP = 10


def price_from_32nds(text):
    """'97-27.25' -> 97 + 27.25/32"""
    whole, ticks = str(text).split("-")
    return int(whole) + float(ticks) / 32


def load_dlv(contract, folder=DATA):
    t = pd.read_csv(Path(folder) / f"dlv_{contract}.csv")
    t["price"] = t["price_32nds"].map(price_from_32nds)
    return t


def decision(dlv, notes=1_000_000_000):
    ctd = dlv.loc[dlv["implied_repo"].idxmax()]
    edge = 100 * (ctd["implied_repo"] - ctd["repo"])
    return {"ctd": ctd["bond"], "conversion_factor": ctd["cf"],
            "implied_repo_%": ctd["implied_repo"], "repo_%": ctd["repo"],
            "edge_bp": round(edge, 1),
            "futures_to_sell_per_$1bn": round(notes / 100_000 * ctd["cf"]),
            "pnl_if_held_$k": round(-ctd["net_basis_32nds"] / 32 / 100 * notes / 1e3),
            "next_cheapest": dlv.sort_values("implied_repo").iloc[-2]["bond"],
            "decision": "ENTER" if edge >= MIN_EDGE_BP else "WAIT"}


def swap_spreads_today(folder=DATA, day="2026-10-29"):
    """SOFR swap rate (Bloomberg) minus Treasury yield (FRED, last day before)."""
    swaps = pd.read_csv(Path(folder) / f"sofr_swaps_{day}.csv", index_col="tenor")["sofr_swap"]
    tsy = load("treasury_yields", folder).loc[:day].iloc[-1]
    out = pd.DataFrame({"sofr_swap": swaps, "treasury": tsy[swaps.index]})
    out["spread_bp"] = (100 * (out["sofr_swap"] - out["treasury"])).round(1)
    return out, tsy.name
