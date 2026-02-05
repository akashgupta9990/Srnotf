import yfinance as yf
import ta
import requests
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

STOCKS = [
    "HDFCSILVER.NS",    # HDFC Silver ETF
    "ICICIGOLD.NS",     # ICICI Gold ETF
    "IDEA.NS",          # Vodafone Idea
    "ADANIENT.NS",      # Adani Enterprises

    # Added strong, liquid stocks
    "ICICIBANK.NS",
    "RELIANCE.NS"
]

def send_alert(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

alerts = []

for symbol in STOCKS:
    df = yf.download(symbol, period="6mo", interval="1d", progress=False)
    if df.empty or len(df) < 60:
        continue

    # ---------- INDICATORS ----------
    df["rsi"] = ta.momentum.RSIIndicator(df["Close"], 14).rsi()
    df["ma20"] = df["Close"].rolling(20).mean()
    df["ma50"] = df["Close"].rolling(50).mean()

    macd = ta.trend.MACD(df["Close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    df["vol_avg"] = df["Volume"].rolling(20).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    buy_score = 0
    sell_score = 0
    reasons = []

    # ---------- METHOD 1: RSI ----------
    if last["rsi"] < 35:
        buy_score += 1
        reasons.append("RSI oversold")

    if last["rsi"] > 70:
        sell_score += 1
        reasons.append("RSI overbought")

    # ---------- METHOD 2: TREND ----------
    if last["ma20"] > last["ma50"]:
        buy_score += 1
        reasons.append("Uptrend (MA20 > MA50)")
    else:
        sell_score += 1
        reasons.append("Downtrend (MA20 < MA50)")

    # ---------- METHOD 3: MACD + VOLUME ----------
    if (
        last["macd"] > last["macd_signal"] and
        prev["macd"] <= prev["macd_signal"] and
        last["Volume"] > 1.2 * last["vol_avg"]
    ):
        buy_score += 1
        reasons.append("MACD bullish + Volume surge")

    if last["macd"] < last["macd_signal"]:
        sell_score += 1
        reasons.append("MACD bearish")

    # ---------- FINAL DECISION ----------

    alerts.append(start)
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

# ---------- SEND ALERT ----------
if alerts:
    send_alert("📊 STOCK ANALYSIS ALERT (Hourly)\n\n" + "\n\n".join(alerts))
