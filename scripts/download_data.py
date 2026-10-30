"""Download the data from FRED into data/.

- treasury_yields.csv : constant maturity Treasury yields, daily, in % (2000-today)
- swap_rates.csv      : USD swap rates vs Libor, daily, in % (FRED stopped them in 2016)
- sofr.csv            : overnight repo rate (SOFR), daily, in % (starts April 2018)
Run: python scripts/download_data.py
"""
import pandas as pd

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
FILES = {
    "treasury_yields": {"1Y": "DGS1", "2Y": "DGS2", "3Y": "DGS3", "5Y": "DGS5",
                        "7Y": "DGS7", "10Y": "DGS10", "20Y": "DGS20", "30Y": "DGS30"},
    "swap_rates": {"2Y": "DSWP2", "5Y": "DSWP5", "10Y": "DSWP10", "30Y": "DSWP30"},
    "sofr": {"SOFR": "SOFR"},
}

for file, series in FILES.items():
    cols = []
    for name, code in series.items():
        s = pd.read_csv(URL.format(code), index_col=0, parse_dates=True, na_values=".")
        cols.append(s.iloc[:, 0].rename(name))
    df = pd.concat(cols, axis=1, sort=True)
    df = df.loc["2000":].dropna(how="all")
    if file != "treasury_yields":
        df = df.dropna()
    df.index.name = "date"
    df.to_csv(f"data/{file}.csv")
    print(f"{file}: {len(df)} days, {df.index[0]:%Y-%m-%d} to {df.index[-1]:%Y-%m-%d}")
