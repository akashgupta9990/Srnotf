import yfinance as yf
import ta
import requests
import os
import pandas as pd
from datetime import datetime, timezone, timedelta

# ================== TELEGRAM CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("BOT_TOKEN or CHAT_ID not set in GitHub Secrets")

def send_alert(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(
        url,
        data={"chat_id": CHAT_ID, "text": message},
        timeout=10
    )

# ================== STOCK LIST ==================
STOCKS = [
    "HDFCSILVER.NS",
    "ICICIGOLD.NS",
    "IDEA.NS",
    "ADANIENT.NS",
    "ICICIBANK.NS",
    "RELIANCE.NS"
]

# ================== START MESSAGE ==================
IST = timezone(timedelta(hours=5, minutes=30))
alerts = [
    "⏰ Hourly Stock Scan Started\n"
    f"Time: {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}\n"
]

# ================== MAIN LOGIC ==================
for symbol in STOCKS:
    try:
        df = yf.download(
            symbol,
            period="6mo",
            interval="1d",
            auto_adjust=True,
            progress=False
        )

        if df.empty or len(df) < 60:
            continue

        close = df["Close"].values.flatten()
        volume = df["Volume"].values.flatten()

        # -------- INDICATORS --------
        df["rsi"] = ta.momentum.RSIIndicator(pd.Series(close), 14).rsi()
        df["ma20"] = pd.Series(close).rolling(20).mean()
        df["ma50"] = pd.Series(close).rolling(50).mean()

        macd = ta.trend.MACD(pd.Series(close))
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()

        df["vol_avg"] = pd.Series(volume).rolling(20).mean()

        i = len(df) - 1
        p = i - 1

        # -------- SCALAR VALUES (BULLETPROOF) --------
        last_close = close[i]
        last_volume = volume[i]
        last_vol_avg = df["vol_avg"].iat[i]

        last_rsi = df["rsi"].iat[i]
        last_ma20 = df["ma20"].iat[i]
        last_ma50 = df["ma50"].iat[i]

        last_macd = df["macd"].iat[i]
        last_macd_signal = df["macd_signal"].iat[i]

        prev_macd = df["macd"].iat[p]
        prev_macd_signal = df["macd_signal"].iat[p]

        buy_score = 0
        sell_score = 0
        reasons = []

        # -------- RSI --------
        if last_rsi < 35:
            buy_score += 1
            reasons.append("RSI oversold")

        if last_rsi > 70:
            sell_score += 1
            reasons.append("RSI overbought")

        # -------- TREND --------
        if last_ma20 > last_ma50:
            buy_score += 1
            reasons.append("Uptrend (MA20 > MA50)")
        else:
            sell_score += 1
            reasons.append("Downtrend (MA20 < MA50)")

        # -------- MACD + VOLUME --------
        if (
            last_macd > last_macd_signal
            and prev_macd <= prev_macd_signal
            and last_volume > 1.2 * last_vol_avg
        ):
            buy_score += 1
            reasons.append("MACD bullish + Volume surge")

        if last_macd < last_macd_signal:
            sell_score += 1
            reasons.append("MACD bearish")

        # -------- FINAL DECISION --------
        if buy_score >= 2 and buy_score > sell_score:
            alerts.append(
                f"📈 BUY {symbol}\n"
                f"Price: ₹{last_close:.2f}\n"
                f"Score: {buy_score}/3\n"
                f"Reasons: {', '.join(reasons)}"
            )

        elif sell_score >= 2:
            alerts.append(
                f"📉 SELL {symbol}\n"
                f"Price: ₹{last_close:.2f}\n"
                f"Score: {sell_score}/3\n"
                f"Reasons: {', '.join(reasons)}"
            )

    except Exception as e:
        alerts.append(f"⚠️ Error processing {symbol}: {e}")

# ================== SEND MESSAGE (ALWAYS) ==================
if len(alerts) == 1:
    alerts.append("No BUY / SELL signals this hour.")

send_alert("📊 STOCK ANALYSIS ALERT (Hourly)\n\n" + "\n\n".join(alerts))
