import os
import telegram
from fastapi import FastAPI, Request
from pytz import timezone
from Crypto.Cipher import AES
import hashlib
import base64
from pymongo import MongoClient
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import ast

app = FastAPI()

TOKEN = os.getenv("TELE_TOKEN")
AUTH_KEY = os.getenv("AUTH_KEY_DECODER")
KEY_WORD = os.getenv("KEY_WORD")
MONGODB_URI = os.getenv("MONGODB")

client = MongoClient(MONGODB_URI)
db = client["BadmintonBookie"]
collection = db["DeleteMessages"]
collection2 = db["BookedCourts"]

sg_timezone = timezone("Asia/Singapore")
bot = telegram.Bot(token=TOKEN)


def aes_decrypt(encrypted_text, key):
    key = hashlib.sha256(key.encode()).digest()
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted_text = cipher.decrypt(base64.b64decode(encrypted_text)).decode()
    return decrypted_text[: -ord(decrypted_text[-1])]


async def get_subscriptions(field_name):
    doc = collection.find_one({field_name: {"$exists": True}})
    print(doc)
    return doc.get(field_name) if doc else "[]"


async def toto_reminder():
    url = "https://www.singaporepools.com.sg/DataFileArchive/Lottery/Output/toto_next_draw_estimate_en.html"
    response = requests.get(url)

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract jackpot amount
    jackpot_span = soup.find("span", style=lambda x: x and "color:#EC243D" in x)
    jackpot_amount = jackpot_span.text.strip() if jackpot_span else "N/A"

    # Extract next draw date
    draw_date_div = soup.find("div", class_="toto-draw-date")
    draw_date = draw_date_div.text.strip() if draw_date_div else "N/A"

    # Build message
    message_parts = ["<b>ToTo Reminder:</b>"]

    if jackpot_amount:
        # if int(jackpot_amount) < 4000000:
        #     return
        message_parts.append(f"💰 Jackpot: {jackpot_amount}")
    else:
        return

    if draw_date:
        message_parts.append(f"🗓️ Date: {draw_date}")
    else:
        message_parts.append("🗓️ Date: Not available")

    # Send final message
    final_message = "\n".join(message_parts)
    list = ast.literal_eval(await get_subscriptions("toto_reminder"))
    print(list)
    for chat_uid in list:
        print(f"Sending message to {chat_uid}")
        await bot.send_message(
            chat_id=int(chat_uid), text=final_message, parse_mode="HTML"
        )


@app.get("/")
def home():
    return {"status": "Bot is running!"}


@app.get("/toto_reminder")
async def manual_trigger(request: Request):
    headers = dict(request.headers)
    # print(headers)
    try:
        if aes_decrypt(headers["auth_key"], AUTH_KEY) == KEY_WORD:
            await toto_reminder()
        else:
            print("FAILED")
    except:
        print("FAILED EXCEPT")
    return {"message": "Reminder sent!"}
