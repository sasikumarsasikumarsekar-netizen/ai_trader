import yfinance as yf
import pandas as pd

symbol = "^NSEI"   # NIFTY 50
data = yf.download(
    tickers=symbol,
    interval="5m",
    period="1d"
)

print(data.tail())
