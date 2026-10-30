"""Treasury basis trade and swap spreads. Run: python run_analysis.py

Part 1: swap spreads (2000-2016), the first sign that Treasuries got 'cheap'.
Part 2: the 10Y futures basket on 14 Feb 2020: conversion factors, CTD, basis, implied repo.
Part 3: the hedge fund basis trade: leverage, return, margins in March 2020.
Part 4: a made-up story, Yakass IM puts on the trade (Feb -> June 2020).
Bonus: real Bloomberg screens of 29 Oct 2026, should Yakass enter today?
Charts and tables go to results/.
"""
import os

import pandas as pd

from basis import futures, plots, screen, trade, yakass
from basis.data import load, spread_stats, swap_spreads

OUT = "results"
DAY = pd.Timestamp("2020-02-14")          # one month before the crash
SETTLE = pd.Timestamp("2020-02-18")       # T+1 (17 Feb was a holiday)
FUTURES_RICH_BP = 30                      # futures implied repo above SOFR (assumption)
pd.set_option("display.width", 160)
pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
os.makedirs(OUT, exist_ok=True)

yields, sofr = load("treasury_yields"), load("sofr")

# ---- Part 1: swap spreads --------------------------------------------------
spreads = swap_spreads()
table, first_negative = spread_stats(spreads)
print("== Swap spreads (bp) ==")
print(table)
print(first_negative.to_string())
table.to_csv(f"{OUT}/swap_spreads.csv")
plots.plot_swap_spreads(spreads, f"{OUT}/01_swap_spreads.png")

# ---- Part 2: the futures basket -------------------------------------------
repo = sofr.loc[DAY, "SOFR"]
basket, fut = futures.basket_table(yields.loc[DAY], SETTLE, repo, futures_rich_bp=FUTURES_RICH_BP)
ctd = basket[basket["ctd"]].iloc[0]
print(f"\n== {futures.CONTRACT} on {DAY:%d %b %Y}, repo {repo:.2f}% ==")
print(f"Futures price {fut:.3f}  (CTD = {ctd['coupon']:.3f}% {ctd['maturity']}, CF {ctd['cf']:.4f})")
print(basket[["coupon", "maturity", "yield", "price", "cf", "gross_basis", "carry",
              "net_basis", "implied_repo", "ctd"]].round(3).to_string(index=False))
basket.round(4).to_csv(f"{OUT}/basket.csv", index=False)
plots.plot_basket(basket, repo, f"{OUT}/02_basket.png")

switch = futures.ctd_vs_yield_level(yields.loc[DAY], SETTLE, repo)
switch.round(2).to_csv(f"{OUT}/ctd_switch.csv", index=False)
plots.plot_ctd_switch(switch, f"{OUT}/03_ctd_switch.png")

# ---- Part 3: the trade, leverage and March 2020 ---------------------------
n = trade.hedge_ratio(ctd["cf"])
dv01 = trade.contract_dv01(ctd["dv01"], ctd["cf"])
margin = trade.initial_margin(yields["10Y"], dv01)
capital = trade.capital_needed(n, margin.loc[DAY], ctd["price"])
cash = trade.NOTES * ctd["price"] / 100
print(f"\n== Basis trade, ${trade.NOTES / 1e9:.0f}bn of the CTD ==")
print(f"Sell {n:,} futures (DV01 {dv01:.0f}$ each), margin {margin.loc[DAY]:,.0f}$/contract")
print(f"Capital: ${capital / 1e6:.1f}m for ${cash / 1e9:.2f}bn of notes -> leverage {cash / capital:.0f}x")

roc = pd.DataFrame({"spread_bp": [5, 10, 20, 30, 50]})
roc["profit_$m_per_year"] = cash * roc["spread_bp"] / 1e10
roc["return_on_capital_%"] = [100 * trade.return_on_capital(s, capital, ctd["price"]) for s in roc["spread_bp"]]
print(roc.to_string(index=False))
roc.to_csv(f"{OUT}/return_on_capital.csv", index=False)

plots.plot_march_2020(yields, sofr, margin, f"{OUT}/04_march_2020.png")

# ---- Part 4: the Yakass IM story (made-up basis path) --------------------
days = yields.loc[yakass.ENTRY:yakass.DELIVERY].index
path = yakass.daily_path(days)
results = {name: yakass.run_fund(cap, path, margin, n, ctd["price"]) for name, cap in yakass.FUNDS.items()}
summ = yakass.summary(results, yakass.FUNDS)
print("\n== Yakass IM, $1bn basis trade, Feb -> June 2020 (made-up basis path) ==")
print(summ)
for name, df in results.items():
    sold = df[df["sold_%"] > 0]
    if len(sold):
        print(f"{name}: forced sales on {', '.join(f'{d:%d %b}' for d in sold.index)}")
summ.to_csv(f"{OUT}/yakass_summary.csv")
pd.concat(results, axis=1).round(0).to_csv(f"{OUT}/yakass_daily.csv")
plots.plot_yakass(results, path, f"{OUT}/05_yakass.png")

# ---- Bonus: real Bloomberg screens, 29 Oct 2026 ---------------------------
print("\n== Bonus: should Yakass enter today? (Bloomberg DLV, 29 Oct 2026) ==")
decisions = {}
for contract, label in [("tyz6", "10Y futures TYZ6"), ("fvz6", "5Y futures FVZ6")]:
    dlv = screen.load_dlv(contract)
    decisions[label] = screen.decision(dlv)
    plots.plot_screen(dlv, f"{label}, 29 Oct 2026: implied repo of each note vs repo (orange = CTD)",
                      f"{OUT}/0{6 if contract == 'tyz6' else 7}_screen_{contract}.png")
dec = pd.DataFrame(decisions)
print(dec.to_string())
dec.to_csv(f"{OUT}/screen_today.csv")
sw, tsy_day = screen.swap_spreads_today()
print(f"\nSOFR swap spreads today (Treasury yields of {tsy_day:%d %b %Y}):")
print(sw.to_string())
sw.to_csv(f"{OUT}/swap_spreads_today.csv")
