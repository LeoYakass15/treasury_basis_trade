"""Basic Treasury note maths: price, accrued interest, DV01, CME conversion factor.

Coupons are semi-annual. Coupon and yield are in %, prices per 100 of face value.
"""
import pandas as pd


def coupon_dates(maturity, settle):
    """Previous coupon date and all future coupon dates (every 6 months back from maturity)."""
    maturity, settle = pd.Timestamp(maturity), pd.Timestamp(settle)
    dates = [maturity]
    while dates[-1] > settle:
        dates.append(maturity - pd.DateOffset(months=6 * len(dates)))
    previous = dates[-1]
    return previous, sorted(d for d in dates if d > settle)


def accrued(coupon, maturity, settle):
    previous, future = coupon_dates(maturity, settle)
    period = (future[0] - previous).days
    return coupon / 2 * (pd.Timestamp(settle) - previous).days / period


def price(coupon, maturity, settle, ytm):
    """Clean price from the yield to maturity (street convention)."""
    previous, future = coupon_dates(maturity, settle)
    w = (future[0] - pd.Timestamp(settle)).days / (future[0] - previous).days   # part of period left
    y = ytm / 200
    dirty = sum((coupon / 2 + (100 if d == future[-1] else 0)) / (1 + y) ** (i + w)
                for i, d in enumerate(future))
    return dirty - accrued(coupon, maturity, settle)


def dv01(coupon, maturity, settle, ytm):
    """Price change for a 1bp fall in yield, per 100 face."""
    return price(coupon, maturity, settle, ytm - 0.005) - price(coupon, maturity, settle, ytm + 0.005)


def conversion_factor(coupon, maturity, delivery_month_start):
    """CME conversion factor for the 10Y note futures (TY).

    = price of 1$ of the note if it yielded 6%, with the remaining time measured
    from the first day of the delivery month and rounded down to a quarter.
    Formula from the CME note "Calculating U.S. Treasury Futures Conversion Factors".
    """
    m = pd.Timestamp(maturity)
    start = pd.Timestamp(delivery_month_start)
    months = (m.year - start.year) * 12 + (m.month - start.month) - (m.day < start.day)
    n, z = divmod(months, 12)
    z = 3 * (z // 3)                     # round down to the quarter
    c = coupon / 100
    v = z if z < 7 else 3
    a = 1 / 1.03 ** (v / 6)
    b = c / 2 * (6 - v) / 6
    cc = 1 / 1.03 ** (2 * n) if z < 7 else 1 / 1.03 ** (2 * n + 1)
    d = c / 0.06 * (1 - cc)
    return round(a * (c / 2 + cc + d) - b, 4)
