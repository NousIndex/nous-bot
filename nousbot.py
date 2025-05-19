from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    CallbackContext,
    filters,
    MessageHandler,
)
from pymongo import MongoClient
import ast
import os
from pytz import timezone
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Now you can access them
BOT_TOKEN = os.getenv("TELE_TOKEN")
MONGODB_URI = os.getenv("MONGODB")


client = MongoClient(MONGODB_URI)
db = client["NousBot"]
collection = db["Subscriptions"]
collection2 = db["UserConfig"]
collection3 = db["ToToWinnings"]

# Track which users are allowed to send input
awaiting_input = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("ToTo", callback_data="toto")],
        # [InlineKeyboardButton("Dividend", callback_data="dividend")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose an option:", reply_markup=reply_markup)

    # Delete the command message
    await context.bot.delete_message(
        chat_id=update.effective_chat.id, message_id=update.message.message_id
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "You can run /reminder to set up reminders.\nYou can run /upload to upload toto numbers."
    )

    # Delete the command message
    await context.bot.delete_message(
        chat_id=update.effective_chat.id, message_id=update.message.message_id
    )


async def reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("ToTo", callback_data="toto")],
        # [InlineKeyboardButton("Dividend", callback_data="dividend")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose an option:", reply_markup=reply_markup)

    # Delete the command message
    await context.bot.delete_message(
        chat_id=update.effective_chat.id, message_id=update.message.message_id
    )


async def update_subscriptions(field_name, new_value):
    collection.update_one(
        {field_name: {"$exists": True}}, {"$set": {field_name: new_value}}
    )


async def get_subscriptions(field_name):
    doc = collection.find_one({field_name: {"$exists": True}})
    return doc.get(field_name) if doc else "[]"


def get_next_date_str():
    sg_timezone = timezone("Asia/Singapore")
    start_date = datetime.now(sg_timezone)

    weekday = start_date.weekday()  # Monday = 0, Sunday = 6
    tuesday = 1
    friday = 4

    if weekday < tuesday:
        delta_days = tuesday - weekday
    elif weekday < friday:
        delta_days = friday - weekday
    else:
        # After Friday, go to next Tuesday
        delta_days = 7 - weekday + tuesday

    next_date = start_date + timedelta(days=delta_days)
    return next_date.strftime("%Y-%m-%d")


async def save_toto_bets(chat_id: str, bets: str, message_source: str):
    collection3.insert_one(
        {
            "Date": get_next_date_str(),
            "ChatId": chat_id,
            "MessageSource": message_source,
            "Bets": bets,
        }
    )


async def delete_message(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.delete_message(
            chat_id=context.job.chat_id, message_id=context.job.data
        )
    except Exception as e:
        print(f"Failed to delete message: {e}")


async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    awaiting_input[user_id] = True
    await update.message.reply_text(
        "Please send your numbers in one message, each row separated by newline (\\n), and each number separated by commas."
    )

    # Delete the command message
    await context.bot.delete_message(
        chat_id=update.effective_chat.id, message_id=update.message.message_id
    )


async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not awaiting_input.get(user_id, False):
        # await update.message.reply_text("Please use /upload before sending numbers.")
        return

    text = update.message.text.strip()
    try:
        lines = text.split("\n")
        result = []
        for line in lines:
            row = [int(x.strip()) for x in line.split(",") if x.strip()]
            result.append(row)

        awaiting_input[user_id] = False  # Accept only one message
        await update.message.reply_text(
            f"Here is your list of lists:\n{result}\nUploading to database"
        )
        await save_toto_bets(chat_id, result, "toto_input")
    except ValueError:
        awaiting_input[user_id] = False  # Still reset to prevent multiple attempts
        await update.message.reply_text(
            "Invalid input. Make sure each row has only numbers separated by commas."
        )
    finally:
        # Delete the command message
        await context.bot.delete_message(
            chat_id=update.effective_chat.id, message_id=update.message.message_id
        )


async def button_handler(update: Update, context: CallbackContext):
    keyboard_main = [
        [InlineKeyboardButton("ToTo", callback_data="toto")],
        # [InlineKeyboardButton("Dividend", callback_data="dividend")],
    ]
    query = update.callback_query
    await query.answer()
    data = query.data
    keyboard_toto_sub = [
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_toto_main"),
            InlineKeyboardButton("✅ Subscribe", callback_data="subscribe_toto_yes"),
        ],
    ]
    keyboard_toto_unsub = [
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_toto_main"),
            InlineKeyboardButton("❌ Unsubscribe", callback_data="subscribe_toto_no"),
        ],
    ]

    keyboard_div_sub = [
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_dividend_main"),
            InlineKeyboardButton(
                "✅ Subscribe", callback_data="subscribe_dividend_yes"
            ),
        ],
    ]
    keyboard_div_unsub = [
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_dividend_main"),
            InlineKeyboardButton(
                "❌ Unsubscribe", callback_data="subscribe_dividend_no"
            ),
        ],
    ]

    if query.data == "toto":
        list = ast.literal_eval(await get_subscriptions("toto_reminder"))
        if query.message.chat_id in list:
            reply_markup = InlineKeyboardMarkup(keyboard_toto_unsub)
        else:
            reply_markup = InlineKeyboardMarkup(keyboard_toto_sub)

        await query.edit_message_text(
            text="ToTo Reminder Service",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    elif query.data == "dividend":
        list = ast.literal_eval(await get_subscriptions("dividend_reminder"))
        if query.message.chat_id in list:
            reply_markup = InlineKeyboardMarkup(keyboard_div_unsub)
        else:
            reply_markup = InlineKeyboardMarkup(keyboard_div_sub)

        await query.edit_message_text(
            text="Dividend Reminder Service",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    elif data.startswith("subscribe_toto"):
        choice = data.split("_")[2]
        chat_id = query.message.chat_id

        if choice == "yes":
            list = ast.literal_eval(await get_subscriptions("toto_reminder"))
            list.append(chat_id)
            await update_subscriptions("toto_reminder", str(list))
            await query.edit_message_text(
                "✅ You have subscribed to the ToTo reminder service."
            )
        else:
            list = ast.literal_eval(await get_subscriptions("toto_reminder"))
            list.remove(chat_id)
            await update_subscriptions("toto_reminder", str(list))
            await query.edit_message_text(
                "❌ You have unsubscribed to the ToTo reminder service."
            )

    elif data.startswith("subscribe_dividend"):
        choice = data.split("_")[2]
        chat_id = query.message.chat_id

        if choice == "yes":
            list = ast.literal_eval(await get_subscriptions("dividend_reminder"))
            list.append(chat_id)
            await update_subscriptions("dividend_reminder", str(list))
            await query.edit_message_text(
                "✅ You have subscribed to the dividend reminder service."
            )
        else:
            list = ast.literal_eval(await get_subscriptions("dividend_reminder"))
            list.remove(chat_id)
            await update_subscriptions("dividend_reminder", str(list))
            await query.edit_message_text(
                "❌ You have unsubscribed to the dividend reminder service."
            )

    elif data.startswith("back_toto"):
        choice = data.split("_")[2]
        if choice == "main":
            await query.edit_message_text(
                text="Choose an option:",
                reply_markup=InlineKeyboardMarkup(keyboard_main),
                parse_mode="Markdown",
            )

    elif data.startswith("back_dividend"):
        choice = data.split("_")[2]
        if choice == "main":
            await query.edit_message_text(
                text="Choose an option:",
                reply_markup=InlineKeyboardMarkup(keyboard_main),
                parse_mode="Markdown",
            )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reminder", reminder))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
