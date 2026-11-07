import pandas as pd                 # tables of data
import numpy as np                  # maths functions
import matplotlib.pyplot as plt     # charts
import os                           # folders

os.makedirs("outputs", exist_ok=True)   # folder for all results
pd.set_option("display.width", 200)     # show wide tables in full in the terminal
pd.set_option("display.max_columns", 20)

# ============================================================
# PART 1: LOAD DATA, RETURNS AND RISK
# ============================================================
data = pd.read_csv("data/clean_prices.csv", index_col="Date", parse_dates=True)   # the clean data

returns = data.pct_change()                                        # daily % change

summary = pd.DataFrame({
    "Start price": data.iloc[0],                                   # first day's close
    "End price": data.iloc[-1],                                    # last day's close
    "Total return %": (data.iloc[-1] / data.iloc[0] - 1) * 100,    # gain or loss over the year
    "Volatility %": returns.std() * np.sqrt(252) * 100,            # yearly volatility (risk)
    "Max drawdown %": (data / data.cummax() - 1).min() * 100,      # worst fall from a peak
}).round(2)

print("RETURNS AND RISK")
print(summary)
summary.to_csv("outputs/summary.csv")                              # save the table

growth = data / data.iloc[0] * 100                                 # every index starts at 100
growth.plot(figsize=(12, 5), title="Growth of 100 invested on 17 Oct 2024")
plt.axhline(100, color="grey", linestyle="--")                     # starting level
plt.ylabel("Value")
plt.grid(alpha=0.3)
plt.savefig("outputs/growth_of_100.png", dpi=120)                  # save the chart
plt.close()                                                        # close it (we save, not show)
print("Saved outputs/summary.csv and outputs/growth_of_100.png")

# ============================================================
# PART 2: GOLDEN AND DEATH CROSSES
# ============================================================
crosses = []                                              # list to collect every cross

for name in data.columns:                                 # repeat for each index
    sma20 = data[name].rolling(20).mean()                 # short-term average
    sma50 = data[name].rolling(50).mean()                 # long-term average
    above = (sma20 > sma50)[sma50.notna()]                # True when SMA20 is above SMA50 (only where SMA50 exists)
    change = above.astype(int).diff()                     # +1 = golden cross, -1 = death cross, 0 = no change

    for date, value in change[change != 0].dropna().items():          # every day the order changed
        price = data[name][date]
        later = data[name].shift(-20)[date]                           # price 20 trading days later
        crosses.append({
            "Index": name,
            "Date": date.date(),
            "Signal": "Golden cross (buy)" if value == 1 else "Death cross (sell)",
            "Price": round(price, 2),
            "Move after 20 days %": round((later / price - 1) * 100, 2),   # did the price go the right way?
        })

crosses = pd.DataFrame(crosses)
print("\nGOLDEN AND DEATH CROSSES")
print(crosses.to_string(index=False))
crosses.to_csv("outputs/crosses.csv", index=False)       # save the table

# ============================================================
# PART 3: CHARTS (price, moving averages, Bollinger Bands, crosses, MACD)
# ============================================================
for name in data.columns:                                 # one chart per index
    close = data[name]
    sma20 = close.rolling(20).mean()                      # moving averages
    sma50 = close.rolling(50).mean()
    upper = sma20 + 2 * close.rolling(20).std()           # Bollinger upper band
    lower = sma20 - 2 * close.rolling(20).std()           # Bollinger lower band
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()   # MACD line
    signal = macd.ewm(span=9, adjust=False).mean()        # MACD signal line

    golden = crosses[(crosses["Index"] == name) & (crosses["Signal"] == "Golden cross (buy)")]   # this index's golden crosses
    death = crosses[(crosses["Index"] == name) & (crosses["Signal"] == "Death cross (sell)")]    # this index's death crosses

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)   # two charts, one above the other
    top.plot(close, color="black", label="Close")
    top.plot(sma20, color="green", label="SMA 20")
    top.plot(sma50, color="orange", label="SMA 50")
    top.fill_between(close.index, lower, upper, alpha=0.1, label="Bollinger Bands")
    top.scatter(pd.to_datetime(golden["Date"]), golden["Price"], marker="^", color="green", s=120, label="Golden cross")
    top.scatter(pd.to_datetime(death["Date"]), death["Price"], marker="v", color="red", s=120, label="Death cross")
    top.set_title(name + ": golden and death crosses")
    top.legend()

    bottom.plot(macd, color="blue", label="MACD")
    bottom.plot(signal, color="red", label="Signal line")
    bottom.axhline(0, color="black", linewidth=0.5)
    bottom.set_title("MACD")
    bottom.legend()

    plt.savefig("outputs/" + name.replace(" ", "_") + "_chart.png", dpi=120)   # e.g. outputs/Nifty_IT_chart.png
    plt.close()

print("Saved one chart per index in outputs/")

# ============================================================
# PART 4: GOLDEN-CROSS TRADES vs BUY & HOLD
# ============================================================
trades = []                                               # list to collect every trade

for name in data.columns:                                 # repeat for each index
    buy_date = None                                       # no trade open yet
    for _, row in crosses[crosses["Index"] == name].iterrows():   # go through this index's crosses in date order
        if row["Signal"] == "Golden cross (buy)":         # golden cross -> buy
            buy_date, buy_price = row["Date"], row["Price"]
        elif buy_date is not None:                        # death cross after a buy -> sell
            trades.append({"Index": name, "Buy date": str(buy_date), "Sell date": str(row["Date"]),
                           "Profit %": round((row["Price"] / buy_price - 1) * 100, 2)})
            buy_date = None
    if buy_date is not None:                              # still holding at the end -> value at the last price
        trades.append({"Index": name, "Buy date": str(buy_date), "Sell date": "still open",
                       "Profit %": round((data[name].iloc[-1] / buy_price - 1) * 100, 2)})

trades = pd.DataFrame(trades)
print("\nGOLDEN-CROSS TRADES (buy at golden cross, sell at next death cross)")
print(trades.to_string(index=False))

comparison = []
for name in data.columns:                                 # strategy vs simply holding the index
    profits = trades[trades["Index"] == name]["Profit %"] / 100
    strategy = ((1 + profits).prod() - 1) * 100           # all trades combined
    start = data[name].iloc[49]                           # buy & hold from day 50, when the first cross was possible
    hold = (data[name].iloc[-1] / start - 1) * 100
    comparison.append({"Index": name, "Trades": len(profits),
                       "Strategy return %": round(strategy, 2), "Buy & hold %": round(hold, 2)})

comparison = pd.DataFrame(comparison)
print("\nSTRATEGY vs BUY & HOLD")
print(comparison.to_string(index=False))

with pd.ExcelWriter("outputs/results.xlsx") as excel:     # all results in one Excel file
    summary.to_excel(excel, sheet_name="Returns and risk")
    crosses.to_excel(excel, sheet_name="Crosses", index=False)
    trades.to_excel(excel, sheet_name="Trades", index=False)
    comparison.to_excel(excel, sheet_name="Strategy vs hold", index=False)
print("Saved outputs/results.xlsx")

# ============================================================
# PART 5: MACD AND BOLLINGER BAND SIGNALS
# ============================================================
signal_results = []

for name in data.columns:
    close = data[name]
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()   # MACD line
    signal_line = macd.ewm(span=9, adjust=False).mean()                                         # signal line
    upper = close.rolling(20).mean() + 2 * close.rolling(20).std()                              # Bollinger upper band
    lower = close.rolling(20).mean() - 2 * close.rolling(20).std()                              # Bollinger lower band
    after_20 = (close.shift(-20) / close - 1) * 100                                             # move over next 20 days

    macd_change = (macd > signal_line).astype(int).diff()     # +1 = MACD crosses above signal, -1 = below
    macd_change.iloc[:35] = 0                                 # ignore the first 35 days (MACD still warming up)

    events = {                                                # signal name : days it happened
        "MACD bullish cross (buy)": macd_change == 1,
        "MACD bearish cross (sell)": macd_change == -1,
        "Close below lower band (buy)": (close < lower) & (close.shift(1) >= lower.shift(1)),
        "Close above upper band (sell)": (close > upper) & (close.shift(1) <= upper.shift(1)),
    }
    for label, days in events.items():
        moves = after_20[days].dropna()                       # what happened after each signal
        right = (moves > 0) if "buy" in label else (moves < 0)   # buy is right if price rose, sell if it fell
        signal_results.append({"Index": name, "Signal": label, "Times": int(days.sum()),
                               "Worked %": round(right.mean() * 100, 1) if len(moves) else None})

signal_results = pd.DataFrame(signal_results)
print("\nMACD AND BOLLINGER BAND SIGNALS (did the price move the right way within 20 days?)")
print(signal_results.to_string(index=False))
signal_results.to_csv("outputs/macd_bollinger_signals.csv", index=False)