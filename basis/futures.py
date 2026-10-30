"""The 10Y Treasury note futures (TY), June 2020 contract: basket, CTD, basis, implied repo.

Deliverable notes: 6.5 to 10 years left on the first day of the delivery month.
I keep the 10Y notes issued from Feb 2017 to Feb 2020 and the three 7Y notes that
were long enough (all issued before 14 Feb 2020, the date of the example).
"""
import pandas as pd

from basis import bonds
from basis.data import curve_yield

CONTRACT = "TYM0 (June 2020)"
MONTH_START = pd.Timestamp("2020-06-01")
DELIVERY = pd.Timestamp("2020-06-30")       # short delivers on the last day (latest possible)
FACE = 100_000                             # face value of one contract

BASKET = [  # (coupon %, maturity)
    (2.250, "2027-02-15"), (2.375, "2027-05-15"), (2.250, "2027-08-15"), (2.250, "2027-11-15"),
    (2.750, "2028-02-15"), (2.875, "2028-05-15"), (2.875, "2028-08-15"), (3.125, "2028-11-15"),
    (2.625, "2029-02-15"), (2.375, "2029-05-15"), (1.625, "2029-08-15"), (1.750, "2029-11-15"),
    (1.500, "2030-02-15"),
    (1.750, "2026-12-31"), (1.500, "2027-01-31"), (1.125, "2027-02-28"),   # 7Y notes
]


def coupons_until(coupon, maturity, settle, delivery):
    """Coupons paid between settlement and delivery (per 100 face)."""
    _, future = bonds.coupon_dates(maturity, settle)
    return coupon / 2 * sum(1 for d in future if d <= delivery)


def forward_price(bond, settle, clean, repo):
    """Clean price for delivery in June, if bought today and financed in repo.

    Simple version: no interest earned on the coupon received before delivery.
    """
    coupon, maturity = bond
    days = (DELIVERY - settle).days
    dirty = clean + bonds.accrued(coupon, maturity, settle)
    return (dirty * (1 + repo / 100 * days / 360)
            - coupons_until(coupon, maturity, settle, DELIVERY)
            - bonds.accrued(coupon, maturity, DELIVERY))


def implied_repo(bond, settle, clean, futures):
    """Return (%, annual, act/360) of: buy the note, sell the futures, deliver it."""
    coupon, maturity = bond
    days = (DELIVERY - settle).days
    cf = bonds.conversion_factor(coupon, maturity, MONTH_START)
    paid = clean + bonds.accrued(coupon, maturity, settle)
    received = (futures * cf + bonds.accrued(coupon, maturity, DELIVERY)
                + coupons_until(coupon, maturity, settle, DELIVERY))
    return 100 * (received / paid - 1) * 360 / days


def basket_table(curve_row, settle, repo, futures=None, futures_rich_bp=0.0):
    """One line per deliverable note.

    Prices come from the Treasury curve of the day. If no futures price is given,
    I use the fair price of the cheapest note, set so that its implied repo is
    `futures_rich_bp` above the repo rate (0 = no arbitrage).
    """
    settle = pd.Timestamp(settle)
    rows = []
    for coupon, maturity in BASKET:
        bond = (coupon, maturity)
        years = (pd.Timestamp(maturity) - settle).days / 365.25
        ytm = curve_yield(curve_row, years)
        clean = bonds.price(coupon, maturity, settle, ytm)
        cf = bonds.conversion_factor(coupon, maturity, MONTH_START)
        fwd_repo = forward_price(bond, settle, clean, repo)
        fwd_rich = forward_price(bond, settle, clean, repo + futures_rich_bp / 100)
        rows.append({"coupon": coupon, "maturity": maturity, "yield": ytm, "price": clean,
                     "cf": cf, "fwd": fwd_repo, "fwd_rich": fwd_rich,
                     "dv01": bonds.dv01(coupon, maturity, settle, ytm)})
    t = pd.DataFrame(rows)
    if futures is None:
        futures = (t["fwd_rich"] / t["cf"]).min()
    t["gross_basis"] = t["price"] - futures * t["cf"]       # in points (1 point = 32 ticks)
    t["carry"] = t["price"] - t["fwd"]
    t["net_basis"] = t["gross_basis"] - t["carry"]
    t["implied_repo"] = [implied_repo((c, m), settle, p, futures)
                         for c, m, p in zip(t["coupon"], t["maturity"], t["price"])]
    t["ctd"] = t["implied_repo"] == t["implied_repo"].max()
    return t.drop(columns="fwd_rich"), futures


def ctd_vs_yield_level(curve_row, settle, repo, shifts_bp=range(-200, 501, 25)):
    """Which note is cheapest to deliver if the whole curve moves up or down?"""
    out = []
    for s in shifts_bp:
        t, _ = basket_table(curve_row + s / 100, settle, repo)
        ctd = t[t["ctd"]].iloc[0]
        out.append({"shift_bp": s, "10Y_yield": curve_row["10Y"] + s / 100,
                    "ctd": f"{ctd['coupon']:.3f}% {ctd['maturity'][:7]}",
                    "ctd_maturity_years": (pd.Timestamp(ctd["maturity"]) - pd.Timestamp(settle)).days / 365.25})
    return pd.DataFrame(out)
