import time
from datetime import datetime, time as dtime
import pytz
import yfinance as yf
import pandas as pd
import requests

# ================= CONFIG =================
SYMBOL = "^NSEI"
TF_ENTRY = "5m"
TF_TREND = "15m"

IST = pytz.timezone("Asia/Kolkata")
MARKET_OPEN = dtime(9, 15)
MARKET_CLOSE = dtime(15, 30)

VOLUME_MULTIPLIER = 1.5
RR = 2.0
LOT_SIZE = 1

MAX_TRADES_PER_DAY = 2

BOT_TOKEN = "7517208665:AAHU4jBPS1q8DDPjKiWPvblST7o41jtUUu4"
CHAT_ID = "5511818563"

# ================= STATE =================
trades_today = 0
current_day = None

# ================= TELEGRAM =================
def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ================= MARKET TIME =================
def market_open():
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    return MARKET_OPEN <= now.time() <= MARKET_CLOSE

def wait_5m_close():
    now = datetime.now(IST)
    sec = 300 - (now.minute % 5) * 60 - now.second
    if sec > 0:
        time.sleep(sec)

# ================= DATA =================
def get_data(tf, days="5d"):
    df = yf.download(SYMBOL, interval=tf, period=days, progress=False)
    return df.dropna()

# ================= TREND FILTER =================
def trend_filter():
    df = get_data(TF_TREND)
    df["EMA20"] = df["Close"].ewm(span=20).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()

    if df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1]:
        return "BULLISH"
    elif df["EMA20"].iloc[-1] < df["EMA50"].iloc[-1]:
        return "BEARISH"
    return None

# ================= VOLATILITY FILTER =================
def atr_filter(df):
    df["TR"] = df["High"] - df["Low"]
    atr = df["TR"].rolling(14).mean().iloc[-1]
    price = df["Close"].iloc[-1]
    if atr / price < 0.002:   # too low volatility
        return False
    if atr / price > 0.02:    # too high volatility
        return False
    return True

# ================= SIDEWAYS FILTER =================
def sideways(df):
    last = df.iloc[-1]
    body = abs(last["Close"] - last["Open"])
    rng = last["High"] - last["Low"]
    if rng == 0:
        return True
    return body / rng < 0.4

# ================= ENTRY ENGINE =================
def check_entry(trend):
    df = get_data(TF_ENTRY)
    if len(df) < 30:
        return None

    if sideways(df):
        return None

    if not atr_filter(df):
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    close = last["Close"]
    vol = last["Volume"]
    avg_vol = df["Volume"].iloc[-20:].mean()

    # BUY
    if trend == "BULLISH" and close > prev["High"] and vol > avg_vol * VOLUME_MULTIPLIER:
        sl = last["Low"]
        risk = close - sl
        target = close + risk * RR
        return ("BUY", close, sl, target, "Uptrend + breakout + volume")

    # SELL
    if trend == "BEARISH" and close < prev["Low"] and vol > avg_vol * VOLUME_MULTIPLIER:
        sl = last["High"]
        risk = sl - close
        target = close - risk * RR
        return ("SELL", close, sl, target, "Downtrend + breakdown + volume")

    return None

# ================= MAIN LOOP =================
print("🔥 FUND MANAGER LEVEL AI STARTED")

while True:
    now = datetime.now(IST)

    global trades_today, current_day
    if current_day != now.date():
        trades_today = 0
        current_day = now.date()

    if not market_open():
        time.sleep(300)
        continue

    if trades_today >= MAX_TRADES_PER_DAY:
        time.sleep(300)
        continue

    wait_5m_close()

    trend = trend_filter()
    if not trend:
        continue

    signal = check_entry(trend)
    if signal:
        trades_today += 1
        side, entry, sl, target, reason = signal

        msg = (
            f"📊 NIFTY 5M TRADE SIGNAL\n\n"
            f"{'🟢 BUY' if side=='BUY' else '🔴 SELL'}\n"
            f"Entry : {round(entry,2)}\n"
            f"SL : {round(sl,2)}\n"
            f"Target : {round(target,2)}\n"
            f"Lots : {LOT_SIZE}\n\n"
            f"📌 Reason:\n"
            f"• {reason}\n"
            f"• ATR + Trend + Volume confirmed"
        )
        send(msg)

    time.sleep(5)
