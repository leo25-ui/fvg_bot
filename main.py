import os
import time
import requests
import pandas as pd
from tvdatafeed import TvDatafeed, Interval

# Змінні оточення з Render
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Перелік пар для відстеження 4H FVG
SYMBOLS = [
    ("EURUSD", "FX_IDC"),
    ("GBPUSD", "FX_IDC"),
    ("USDCAD", "FX_IDC"),
]

# Сховище вже відправлених FVG, щоб не повторювати сповіщення
sent_fvgs = set()

def send_telegram_message(message: str):
    """Відправка сповіщення в Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending message to Telegram: {e}")

def check_fvgs():
    """Перевірка наявності 4H FVG"""
    tv = TvDatafeed()
    for symbol, exchange in SYMBOLS:
        try:
            # Отримуємо останні 10 свічок на 4-годинному таймфреймі
            df = tv.get_hist(symbol=symbol, exchange=exchange, interval=Interval.in_4_hour, n_bars=10)
            if df is None or len(df) < 3:
                continue

            # Аналізуємо останні сформовані 3 свічки (ігноруємо поточну незакриту)
            c1 = df.iloc[-4] # Свічка 1
            c3 = df.iloc[-2] # Свічка 3
            candle_time = str(df.index[-2])

            # Bullish FVG (Low свічки 3 > High свічки 1)
            if c3['low'] > c1['high']:
                fvg_id = f"{symbol}_BULL_{candle_time}"
                if fvg_id not in sent_fvgs:
                    gap_size = round(c3['low'] - c1['high'], 5)
                    msg = (
                        f"🟢 <b>Bullish 4H FVG Detected!</b>\n\n"
                        f"<b>Pair:</b> {symbol}\n"
                        f"<b>Zone Top (Low3):</b> {c3['low']}\n"
                        f"<b>Zone Bottom (High1):</b> {c1['high']}\n"
                        f"<b>Gap Size:</b> {gap_size}\n"
                        f"<b>Time:</b> {candle_time}"
                    )
                    send_telegram_message(msg)
                    sent_fvgs.add(fvg_id)

            # Bearish FVG (High свічки 3 < Low свічки 1)
            elif c3['high'] < c1['low']:
                fvg_id = f"{symbol}_BEAR_{candle_time}"
                if fvg_id not in sent_fvgs:
                    gap_size = round(c1['low'] - c3['high'], 5)
                    msg = (
                        f"🔴 <b>Bearish 4H FVG Detected!</b>\n\n"
                        f"<b>Pair:</b> {symbol}\n"
                        f"<b>Zone Top (Low1):</b> {c1['low']}\n"
                        f"<b>Zone Bottom (High3):</b> {c3['high']}\n"
                        f"<b>Gap Size:</b> {gap_size}\n"
                        f"<b>Time:</b> {candle_time}"
                    )
                    send_telegram_message(msg)
                    sent_fvgs.add(fvg_id)

        except Exception as e:
            print(f"Error processing {symbol}: {e}")

if __name__ == "__main__":
    send_telegram_message("🤖 <b>4H FVG Autonomous Bot Started!</b>\nМоніторинг 4H FVG активовано.")
    while True:
        check_fvgs()
        # Перевірка кожні 5 хвилин
        time.sleep(300)
