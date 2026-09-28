import os
import requests
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

# Заміни значення нижче на свої реальні Token та Chat ID (у лапках)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "ТВІЙ_BOT_TOKEN_СЮДИ")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "ТВІЙ_CHAT_ID_СЮДИ")

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    return response.json()

@app.get("/")
def read_root():
    return {"status": "FVG Webhook Bot is running!"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.body()
        message = body.decode("utf-8")
        
        if not message:
            raise HTTPException(status_code=400, detail="Empty body")
        
        res = send_telegram_message(message)
        return {"status": "success", "telegram_response": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
