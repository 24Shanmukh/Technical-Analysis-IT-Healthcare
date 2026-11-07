import yfinance as yf               # downloads market data from Yahoo Finance
import pandas as pd                 # tables of data
import os                           # folders

os.makedirs("data", exist_ok=True)  # make sure the data folder exists

# STEP 1: DOWNLOAD (Nifty IT and Nifty Bank from Yahoo Finance)
tickers = {                         # Yahoo Finance code : index name
    "^CNXIT": "Nifty IT",
    "^NSEBANK": "Nifty Bank",
}

raw = yf.download(list(tickers), start="2024-10-17", end="2025-10-18", progress=False)  # end date is not included
data = raw["Close"]                                 # keep only the closing prices
data = data.rename(columns=tickers)                 # replace codes with names
data.columns.name = None                            # remove the leftover "Ticker" label

# Nifty Healthcare is not on Yahoo for this period, so read it from the file in the data folder
health = pd.read_csv("data/nifty_healthcare.csv", index_col="Date", parse_dates=True)
data["Nifty Healthcare"] = health["Close"]          # add it, matched by date

data = data[["Nifty IT", "Nifty Healthcare", "Nifty Bank"]]   # put the columns in our order
data.to_csv("data/raw_prices.csv")                  # save the raw data, untouched
print("Downloaded", len(data), "rows")

# STEP 2: CLEAN
print("Missing values before cleaning:")
print(data.isnull().sum())

data = data.sort_index()                            # oldest date first
data = data[~data.index.duplicated()]               # remove any repeated dates
data = data.where(data > 0)                         # treat zero or negative prices as missing
data = data.dropna(how="all")                       # remove days with no prices at all (holidays)
data = data.ffill()                                 # fill a missing price with the previous day's price
data = data.dropna()                                # remove rows still empty at the very start

big_moves = data.pct_change().abs() > 0.10          # flag daily moves above 10% (possible data errors)
print("Days with a move above 10% (check these):", int(big_moves.sum().sum()))

data = data.round(2)                                # 2 decimal places
data.index.name = "Date"
data.to_csv("data/clean_prices.csv")                # save the clean data

# STEP 3: CHECK
print("Missing values after cleaning:", int(data.isnull().sum().sum()))
print("From", data.index[0].date(), "to", data.index[-1].date(), "|", len(data), "trading days")
print(data.head())
print("Saved data/clean_prices.csv")