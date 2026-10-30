"""Charts saved to results/."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

T = pd.Timestamp

BLUE, ORANGE, AQUA, YELLOW, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a8984"
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e6e5e1", "grid.linewidth": 0.6,
                     "font.size": 10, "lines.linewidth": 1.6})


def save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_swap_spreads(spreads, path):
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for col, color in zip(["2Y", "5Y", "10Y", "30Y"], [BLUE, ORANGE, AQUA, YELLOW]):
        s = spreads[col].rolling(5).mean()
        ax.plot(s.index, s, color=color, label=col)
    ax.axhline(0, color="black", lw=0.8)
    ax.annotate("Lehman: 30Y spread\ngoes negative", (T("2008-11-15"), -40), (
        T("2003-06-01"), -45), arrowprops={"arrowstyle": "->", "color": GREY}, fontsize=9)
    ax.set_title("USD swap spreads: swap rate minus Treasury yield (bp, 5-day average)")
    ax.set_ylabel("bp")
    ax.legend(ncol=4, frameon=False, loc="upper right")
    save(fig, path)


def plot_basket(table, repo, path):
    t = table.sort_values("maturity")
    labels = [f"{c:.3f}% {m[:7]}" for c, m in zip(t["coupon"], t["maturity"])]
    colors = [ORANGE if ctd else BLUE for ctd in t["ctd"]]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=True)
    axes[0].barh(labels, 32 * t["net_basis"], color=colors)
    axes[0].axvline(0, color="black", lw=0.8)
    axes[0].set_title("Net basis (32nds): lowest = cheapest to deliver")
    axes[1].barh(labels, t["implied_repo"], color=colors)
    axes[1].axvline(repo, color="black", lw=0.8, ls="--")
    axes[1].text(repo, len(t) - 0.5, f" repo (SOFR) {repo:.2f}%", fontsize=9, va="bottom")
    axes[1].set_xlim(left=max(t["implied_repo"].min(), -6))
    axes[1].set_title("Implied repo rate (%): highest = CTD")
    axes[0].invert_yaxis()
    fig.suptitle("10Y note futures, June 2020 contract, deliverable basket on 14 Feb 2020 (orange = CTD)")
    save(fig, path)


def plot_ctd_switch(switch, path):
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.step(switch["10Y_yield"], switch["ctd_maturity_years"], where="mid", color=BLUE)
    ax.axvline(6, color=GREY, ls="--", lw=1)
    ax.text(6.05, 8.5, "6% = yield used by\nthe conversion factors", fontsize=9, color=GREY)
    ax.set_xlabel("10Y Treasury yield if the whole curve moves (%)")
    ax.set_ylabel("Years to maturity of the CTD")
    ax.set_title("The cheapest-to-deliver switches from short to long notes above 6%")
    save(fig, path)


def plot_march_2020(yields, sofr, margin, path):
    a, b = "2019-07-01", "2020-06-30"
    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    axes[0].plot(yields.loc[a:b, "10Y"], color=BLUE)
    axes[0].axvspan(T("2020-03-09"), T("2020-03-18"), color=ORANGE, alpha=0.15)
    axes[0].text(T("2020-03-20"), 1.65, "9-18 March: stocks crash\nbut 10Y yield goes UP\n0.54% -> 1.18%", fontsize=9)
    axes[0].set_title("10Y Treasury yield (%): the 'dash for cash'")
    axes[1].plot(sofr.loc[a:b, "SOFR"], color=AQUA)
    axes[1].text(T("2019-09-20"), 4.8, "17 Sep 2019: repo spike to 5.25%", fontsize=9)
    axes[1].set_title("Repo rate the fund pays (SOFR, %)")
    axes[2].plot(margin.loc[a:b], color=ORANGE)
    axes[2].set_title("Model initial margin per 10Y futures contract ($)")
    for ax in axes:
        ax.axvspan(T("2020-03-09"), T("2020-03-18"), color=ORANGE, alpha=0.15)
    save(fig, path)


def plot_yakass(results, path, path_out):
    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    axes[0].plot(path["net_basis_32"], color=GREY)
    axes[0].set_title("Net basis of the CTD (32nds, MADE-UP path): lower = notes cheaper than futures")
    colors = {"Yakass aggressive": ORANGE, "Yakass prudent": BLUE}
    for name, df in results.items():
        c = colors[name]
        axes[1].plot(df["equity"] / 1e6, color=c, label=f"{name}: money left")
        axes[1].plot(df["capital_needed"] / 1e6, color=c, ls="--", lw=1, label=f"{name}: money required")
        axes[2].plot(df["position_%"], color=c, label=name)
    axes[1].set_title("Money left vs money required by repo lender + exchange ($m)")
    axes[1].legend(frameon=False, fontsize=8, ncol=2, loc="center right")
    axes[2].set_title("Position kept (% of the $1bn trade)")
    axes[2].set_ylim(0, 105)
    axes[2].legend(frameon=False, fontsize=9)
    for ax in axes:
        ax.axvspan(T("2020-03-09"), T("2020-03-23"), color=ORANGE, alpha=0.12)
    save(fig, path_out)


def plot_screen(dlv, title, path):
    t = dlv.sort_values("implied_repo")
    colors = [ORANGE if i == t["implied_repo"].idxmax() else BLUE for i in t.index]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.barh(t["bond"], t["implied_repo"], color=colors)
    repo = t["repo"].iloc[0]
    ax.axvline(repo, color="black", ls="--", lw=1)
    ax.text(repo, -0.9, f" repo {repo:.2f}%", fontsize=9)
    ax.set_xlim(right=repo + 0.6)
    ax.set_xlabel("Implied repo rate (%)")
    ax.set_title(title)
    save(fig, path)
