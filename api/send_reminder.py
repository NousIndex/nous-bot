import os
import telegram
from fastapi import FastAPI, Request
from pytz import timezone
from Crypto.Cipher import AES
import hashlib
import base64
from pymongo import MongoClient
from datetime import datetime, timedelta
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import ast
import json

app = FastAPI()

TOKEN = os.getenv("TELE_TOKEN")
AUTH_KEY = os.getenv("AUTH_KEY_DECODER")
KEY_WORD = os.getenv("KEY_WORD")
MONGODB_URI = os.getenv("MONGODB")

client = MongoClient(MONGODB_URI)
db = client["NousBot"]
collection = db["Subscriptions"]
collection2 = db["UserConfig"]

sg_timezone = timezone("Asia/Singapore")
bot = telegram.Bot(token=TOKEN)
now_sgt = datetime.now(sg_timezone)
current_date_str = now_sgt.strftime("%Y-%m-%d")


def aes_decrypt(encrypted_text, key):
    key = hashlib.sha256(key.encode()).digest()
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted_text = cipher.decrypt(base64.b64decode(encrypted_text)).decode()
    return decrypted_text[: -ord(decrypted_text[-1])]


async def get_subscriptions(field_name):
    doc = collection.find_one({field_name: {"$exists": True}})
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
        if int(jackpot_amount.replace(",", "")) < 4000000:
            return
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
    for chat_uid in list:
        await bot.send_message(
            chat_id=int(chat_uid), text=final_message, parse_mode="HTML"
        )


async def toto_check_winnings():
    result = collection.find({"Date": current_date_str})
    for doc in result:
        total_winnings = 0
        winning_sets = []
        # Step 1: Fetch the draw list HTML
        draw_list_url = "https://www.singaporepools.com.sg/DataFileArchive/Lottery/Output/toto_result_draw_list_en.html"
        response = requests.get(draw_list_url)
        soup = BeautifulSoup(response.text, "html.parser")

        # Step 2: Extract the latest draw number
        first_option = soup.select_one("select.selectDrawList option")
        latest_draw_number = first_option["value"]

        # Step 3: Prepare payload
        calculate_url = "https://www.singaporepools.com.sg/_layouts/15/TotoApplication/TotoCommonPage.aspx/CalculatePrizeForTOTO"

        lst = json.loads(doc["Bets"])
        for item in lst:
            numbers = ",".join(map(str, item))

            payload = {
                "numbers": numbers,
                "drawNumber": latest_draw_number,
                "isHalfBet": "false",
                "totalNumberOfParts": "1",
                "partsPurchased": "1",
            }

            headers = {"Content-Type": "application/json"}

            # Step 4: Send POST request
            post_response = requests.post(calculate_url, json=payload, headers=headers)

            # Step 5: Extract and parse nested JSON
            if post_response.status_code == 200:
                outer_data = post_response.json()
                inner_data = json.loads(
                    outer_data["d"]
                )  # Parse the inner string as JSON

                # Step 6: Sum the "Total" values
                total_sum = sum(
                    int(prize["Total"]) for prize in inner_data.get("Prizes", [])
                )
                if total_sum > 0:
                    total_winnings += total_sum
                    winning_sets.append("[" + numbers + "]")
            else:
                print("Request failed with status:", post_response.status_code)

        new_date = now_sgt + timedelta(days=-1)
        new_date_str = new_date.strftime("%Y-%m-%d")
        message_parts = ["<b>ToTo Winnings for {}:</b>".format(new_date_str)]
        message_parts.append(f"💰 Winnings: {total_winnings}")
        if winning_sets:
            message_parts.append(f"🎉 Winning Sets: {'\n'.join(winning_sets)}")
        final_message = "\n".join(message_parts)

        await bot.send_message(
            chat_id=int(doc["ChatId"]), text=final_message, parse_mode="HTML"
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
