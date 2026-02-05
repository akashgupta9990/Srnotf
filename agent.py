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
    "HDFCSILVER.NS",     # HDFC Silver ETF
    "ICICIGOLD.NS",      # ICICI Gold ETF
    "IDEA.NS",           # Vodafone Idea
    "ADANIENT.NS",       # Adani Enterprises
    "ICICIBANK.NS",      # Strong liquid stock
    "RELIANCE.NS"        # Strong liquid stock
]

# ================== HELPERS ==================
def to_series(x):
    """Ensure 1D pandas Series (fixes GitHub Actions + yfinance issue)."""
    if isinstance(x, pd.DataFrame):
        return x.iloc[:, 0]
    if hasattr(x, "values") and len(x.shape) > 1:
        return x.squeeze()
    return x

# ================== START MESSAGE ==================
IST = timezone(timedelta(hours=5, minutes=30))
start_message = (
    "⏰ Hourly Stock Scan Started\n"
    f"Time: {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}\n"
)

alerts = [start_message]

# ================== MAIN LOGIC ==================
for symbol in STOCKS:
    try:
        df = yf.download(
            symbol,
            period="6mo",
            interval="1d",
            progress=False
        )

        if df.empty or len(df) < 60:
            continue

        close = to_series(df["Close"])
        volume = to_series(df["Volume"])

        # -------- INDICATORS --------
        df["rsi"] = ta.momentum.RSIIndicator(close, 14).rsi()
        df["ma20"] = close.rolling(20).mean()
        df["ma50"] = close.rolling(50).mean()

        macd = ta.trend.MACD(close)
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()

        df["vol_avg"] = volume.rolling(20).mean()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        buy_score = 0
        sell_score = 0
        reasons = []

        # -------- RSI --------
        if last["rsi"] < 35:
            buy_score += 1
            reasons.append("RSI oversold")

        if last["rsi"] > 70:
            sell_score += 1
            reasons.append("RSI overbought")

        # -------- TREND --------
        if last["ma20"] > last["ma50"]:
            buy_score += 1
            reasons.append("Uptrend (MA20 > MA50)")
        else:
            sell_score += 1
            reasons.append("Downtrend (MA20 < MA50)")

        # -------- MACD + VOLUME --------
        if (
            last["macd"] > last["macd_signal"]
            and prev["macd"] <= prev["macd_signal"]
            and last["Volume"] > 1.2 * last["vol_avg"]
        ):
            buy_score += 1
            reasons.append("MACD bullish + Volume surge")

        if last["macd"] < last["macd_signal"]:
            sell_score += 1
            reasons.append("MACD bearish")

        # -------- FINAL DECISION --------
        if buy_score >= 2 and buy_score > sell_score:
            alerts.append(
                f"📈 BUY {symbol}\n"
                f"Price: ₹{last['Close']:.2f}\n"
                f"Score: {buy_score}/3\n"
                f"Reasons: {', '.join(reasons)}"
            )

        elif sell_score >= 2:
            alerts.append(
                f"📉 SELL {symbol}\n"
                f"Price: ₹{last['Close']:.2f}\n"
                f"Score: {sell_score}/3\n"
                f"Reasons: {', '.join(reasons)}"
            )

    except Exception as e:
        alerts.append(f"⚠️ Error processing {symbol}: {e}")

# ================== SEND MESSAGE (ALWAYS) ==================
if len(alerts) == 1:
    alerts.append("No BUY / SELL signals this hour.")

send_alert("📊 STOCK ANALYSIS ALERT (Hourly)\n\n" + "\n\n".join(alerts))
