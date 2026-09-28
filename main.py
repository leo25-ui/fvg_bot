import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import yfinance as yf

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDCAD": "CAD=X",
}

sent_fvgs = set()

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_check_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

def send_telegram_message(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Помилка: відсутній TELEGRAM_BOT_TOKEN або TELEGRAM_CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Помилка надсилання в Telegram: {e}")

def check_fvgs():
    for name, ticker in SYMBOLS.items():
        try:
            df = yf.download(tickers=ticker, period="7d", interval="1h", progress=False)
            if df.empty or len(df) < 12:
                continue

            df_4h = df.resample('4h').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last'
            }).dropna()

            if len(df_4h) < 3:
                continue

            # Розширене логування для відлагодження
            print(f"=== Сканування {name} | Всього 4H свічок: {len(df_4h)} ===")
            for idx in range(-3, 0):
                c = df_4h.iloc[idx]
                print(f"  [4H Свічка {df_4h.index[idx]}] Open: {c['Open']:.5f} | High: {c['High']:.5f} | Low: {c['Low']:.5f} | Close: {c['Close']:.5f}")

            # Перевіряємо всі закриті свічки в історії
            for i in range(2, len(df_4h) - 1):
                c1 = df_4h.iloc[i - 2]
                c3 = df_4h.iloc[i]
                candle_time = str(df_4h.index[i])

                high1 = float(c1['High'])
                low1 = float(c1['Low'])
                high3 = float(c3['High'])
                low3 = float(c3['Low'])

                # 1. Бичачий FVG (Bullish FVG: Low3 > High1)
                if low3 > high1:
                    fvg_id = f"{name}_BULL_{candle_time}"
                    if fvg_id not in sent_fvgs:
                        is_filled = False
                        for j in range(i + 1, len(df_4h)):
                            if float(df_4h.iloc[j]['Low']) <= high1:
                                is_filled = True
                                break
                        
                        if not is_filled:
                            gap_size = round(low3 - high1, 5)
                            print(f"-> ЗНАЙДЕНО АКТИВНИЙ BULLISH FVG на {name} ({candle_time}): Top={low3}, Bottom={high1}")
                            msg = (
                                f"🟢 <b>Active Bullish 4H FVG!</b>\n\n"
                                f"<b>Pair:</b> {name}\n"
                                f"<b>Zone Top (Low3):</b> {round(low3, 5)}\n"
                                f"<b>Zone Bottom (High1):</b> {round(high1, 5)}\n"
                                f"<b>Gap Size:</b> {gap_size}\n"
                                f"<b>Time:</b> {candle_time}"
                            )
                            send_telegram_message(msg)
                            sent_fvgs.add(fvg_id)

                # 2. Ведмежий FVG (Bearish FVG: High3 < Low1)
                elif high3 < low1:
                    fvg_id = f"{name}_BEAR_{candle_time}"
                    if fvg_id not in sent_fvgs:
                        is_filled = False
                        for j in range(i + 1, len(df_4h)):
                            if float(df_4h.iloc[j]['High']) >= low1:
                                is_filled = True
                                break
                        
                        if not is_filled:
                            gap_size = round(low1 - high3, 5)
                            print(f"-> ЗНАЙДЕНО АКТИВНИЙ BEARISH FVG на {name} ({candle_time}): Top={low1}, Bottom={high3}")
                            msg = (
                                f"🔴 <b>Active Bearish 4H FVG!</b>\n\n"
                                f"<b>Pair:</b> {name}\n"
                                f"<b>Zone Top (Low1):</b> {round(low1, 5)}\n"
                                f"<b>Zone Bottom (High3):</b> {round(high3, 5)}\n"
                                f"<b>Gap Size:</b> {gap_size}\n"
                                f"<b>Time:</b> {candle_time}"
                            )
                            send_telegram_message(msg)
                            sent_fvgs.add(fvg_id)

        except Exception as e:
            print(f"Помилка обробки {name}: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_health_check_server, daemon=True).start()
    
    send_telegram_message("🤖 <b>4H FVG Debug Bot Started!</b>\nЛогування цін активовано.")
    while True:
        check_fvgs()
        time.sleep(300)
