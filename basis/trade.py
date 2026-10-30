"""The basis trade of a hedge fund: buy the cheapest note, sell the futures, borrow in repo.

Everything is per $1bn of notes bought. The fund's money (equity) is only what
the repo lender and the futures exchange ask as collateral:
    capital = repo haircut x notes + initial margin x number of futures
"""
import numpy as np
import pandas as pd

from basis.futures import FACE

NOTES = 1_000_000_000        # face value of notes bought
HAIRCUT = 0.01               # repo lender keeps 1% (Treasuries were often at 0-2%)


def hedge_ratio(cf):
    """Futures to sell per $1bn of notes: face / 100k x conversion factor."""
    return round(NOTES / FACE * cf)


def contract_dv01(ctd_dv01, cf):
    """$ value of 1bp for one futures contract (it moves like the CTD / CF)."""
    return ctd_dv01 / cf * FACE / 100


def ewma_vol(changes_bp, lam=0.94):
    """Daily volatility of yield changes, RiskMetrics style (recent days count more)."""
    return np.sqrt((changes_bp ** 2).ewm(alpha=1 - lam).mean())


def initial_margin(yields_10y, dv01_contract, lam=0.94):
    """Simple model of the exchange margin: a 99% move over 2 days.

    margin = 2.33 x sqrt(2) x daily vol (bp) x DV01 of one contract
    The exchange rarely lowers margins quickly, so I keep the running
    maximum of the last 60 days.
    """
    vol = ewma_vol(100 * yields_10y.diff().dropna(), lam)
    margin = 2.33 * np.sqrt(2) * vol * dv01_contract
    return margin.rolling(60, min_periods=1).max()


def capital_needed(n_futures, margin_per_contract, price):
    return HAIRCUT * NOTES * price / 100 + n_futures * margin_per_contract


def return_on_capital(spread_bp, capital, price):
    """Yearly profit / capital, if the implied repo is spread_bp above the repo rate."""
    profit = NOTES * price / 100 * spread_bp / 10_000
    return profit / capital
