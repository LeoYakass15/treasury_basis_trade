import pandas as pd

from basis import bonds, futures, trade
from basis.data import load


def test_bond_at_its_coupon_yield_is_par():
    assert abs(bonds.price(2.0, "2030-02-15", "2020-02-15", 2.0) - 100) < 1e-9


def test_conversion_factor_of_a_6pct_note_is_one():
    assert abs(bonds.conversion_factor(6.0, "2028-06-01", "2020-06-01") - 1) < 1e-4
    assert bonds.conversion_factor(2.0, "2028-06-01", "2020-06-01") < 1     # low coupon < 1


def test_ctd_implied_repo_is_repo_plus_richness():
    y = load("treasury_yields").loc["2020-02-14"]
    t, _ = futures.basket_table(y, pd.Timestamp("2020-02-18"), 1.58, futures_rich_bp=30)
    ctd = t[t["ctd"]].iloc[0]
    assert abs(ctd["implied_repo"] - 1.88) < 1e-6
    assert ctd["net_basis"] < 0            # futures rich -> long basis makes money
    assert (t["net_basis"] >= ctd["net_basis"]).all()


def test_hedge_ratio():
    assert trade.hedge_ratio(0.8) == 8000


def test_aggressive_fund_is_forced_to_sell_and_prudent_is_not():
    import pandas as pd
    from basis import yakass
    days = pd.bdate_range(yakass.ENTRY, yakass.DELIVERY)
    path = yakass.daily_path(days)
    margin = pd.Series(1500.0, index=days)
    margin.loc["2020-03-12":] = 3500.0
    small = yakass.run_fund(25e6, path, margin, 8000, 105)
    big = yakass.run_fund(75e6, path, margin, 8000, 105)
    assert small["position_%"].iloc[-1] < 100
    assert big["position_%"].iloc[-1] == 100
    assert abs(big["equity"].iloc[-1] - 75e6 - 4 / 32 / 100 * 1e9) < 1     # earns the 4/32


def test_screen_reads_32nds_and_decides():
    from basis import screen
    assert screen.price_from_32nds("97-27.25") == 97 + 27.25 / 32
    d = screen.decision(screen.load_dlv("tyz6"))
    assert d["ctd"] == "T 4 1/2 08/31/33" and d["decision"] == "WAIT"
