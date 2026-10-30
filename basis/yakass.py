"""A made-up story: Yakass Investment Management puts on a basis trade in February 2020.

Real data: the Treasury curve and SOFR (FRED), and the futures margin model built on
real 10Y volatility. Made up: the path of the net basis and the repo haircuts, chosen
to look like what the Fed, BIS and OFR papers describe for March 2020.

Two versions of the same fund buy $1bn of the CTD note and sell the futures:
- "aggressive": just enough capital to open the trade, plus a small cushion
- "prudent": three times more capital, so it can survive a margin call
"""
import pandas as pd

from basis import trade

ENTRY, DELIVERY = "2020-02-14", "2020-06-30"

# Net basis of the CTD in 32nds (made up). Negative = futures rich = good for the trade.
# The trade earns (net basis at exit - net basis at entry); at delivery it is 0.
BASIS_PATH = {
    "2020-02-14": -4,     # entry: implied repo about 30bp above SOFR
    "2020-03-06": -4,     # calm
    "2020-03-18": -36,    # 'dash for cash': notes fall 1 point more than futures
    "2020-03-23": -36,    # Fed announces unlimited Treasury purchases
    "2020-04-30": -8,     # markets heal
    "2020-06-30": 0,      # delivery: futures and cash meet
}
HAIRCUTS = {"2020-02-14": 0.01, "2020-03-12": 0.02, "2020-05-01": 0.01}   # repo lenders get nervous (made up)
FUNDS = {"Yakass aggressive": 25e6, "Yakass prudent": 75e6}


def daily_path(dates):
    """Net basis and haircut for each trading day (straight lines between the points above)."""
    d = pd.DatetimeIndex(dates)
    pts = pd.Series(BASIS_PATH, dtype=float)
    pts.index = pd.to_datetime(pts.index)
    basis = pts.reindex(d.union(pts.index)).interpolate("time").reindex(d)
    hc = pd.Series(HAIRCUTS)
    hc.index = pd.to_datetime(hc.index)
    haircut = hc.reindex(d.union(hc.index)).ffill().reindex(d)
    return pd.DataFrame({"net_basis_32": basis, "haircut": haircut})


def run_fund(capital, path, margin, n_futures, price):
    """Mark the trade to market every day. If the money left is below what the
    repo lender and the exchange ask for, the fund must sell part of the trade."""
    size, equity, rows = 1.0, capital, []
    prev = path["net_basis_32"].iloc[0]
    for day, r in path.iterrows():
        pnl = size * (r["net_basis_32"] - prev) / 32 / 100 * trade.NOTES
        equity += pnl
        prev = r["net_basis_32"]
        need_full = r["haircut"] * trade.NOTES * price / 100 + n_futures * margin.loc[day]
        sold = 0.0
        if equity < size * need_full:              # margin call we cannot meet
            new_size = max(equity, 0) / need_full
            sold, size = size - new_size, new_size
        rows.append({"date": day, "net_basis_32": r["net_basis_32"], "pnl": pnl,
                     "equity": equity, "capital_needed": size * need_full,
                     "position_%": 100 * size, "sold_%": 100 * sold})
    return pd.DataFrame(rows).set_index("date")


def summary(results, capitals):
    out = {}
    for name, df in results.items():
        cap = capitals[name]
        out[name] = {"capital_$m": cap / 1e6,
                     "leverage_at_entry": trade.NOTES / cap,
                     "worst_equity_$m": df["equity"].min() / 1e6,
                     "position_left_%": df["position_%"].iloc[-1],
                     "final_pnl_$m": (df["equity"].iloc[-1] - cap) / 1e6,
                     "return_%": 100 * (df["equity"].iloc[-1] / cap - 1)}
    return pd.DataFrame(out).T
