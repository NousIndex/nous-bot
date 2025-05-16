from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    CallbackContext,
)
from pymongo import MongoClient
import ast
import os

BOT_TOKEN = os.getenv("TELE_TOKEN")
MONGODB_URI = os.getenv("MONGODB")

client = MongoClient(MONGODB_URI)
db = client["NousBot"]
collection = db["Subscriptions"]
collection2 = db["UserConfig"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("ToTo", callback_data="toto")],
        [InlineKeyboardButton("Dividend", callback_data="dividend")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose an option:", reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("You can run /reminder to set up reminders.")


async def reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("ToTo", callback_data="toto")],
        [InlineKeyboardButton("Dividend", callback_data="dividend")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose an option:", reply_markup=reply_markup)


async def update_subscriptions(field_name, new_value):
    collection.update_one(
        {field_name: {"$exists": True}}, {"$set": {field_name: new_value}}
    )


async def get_subscriptions(field_name):
    doc = collection.find_one({field_name: {"$exists": True}})
    return doc.get(field_name) if doc else "[]"


async def save_message(chat_id: str, message_id: str, message_source: str, date: str):
    collection.insert_one(
        {
            "Date": date,
            "ChatId": str(chat_id),
            "MessageId": str(message_id),
            "MessageSource": message_source,
        }
    )


async def delete_message(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.delete_message(
            chat_id=context.job.chat_id, message_id=context.job.data
        )
    except Exception as e:
        print(f"Failed to delete message: {e}")


async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data
    print(query)
    keyboard1 = [
        [InlineKeyboardButton("✅ Subscribe", callback_data="subscribe_toto_yes")],
    ]
    keyboard2 = [
        [InlineKeyboardButton("❌ Unsubscribe", callback_data="subscribe_toto_no")],
    ]

    keyboard3 = [
        [InlineKeyboardButton("✅ Subscribe", callback_data="subscribe_dividend_yes")],
    ]
    keyboard4 = [
        [InlineKeyboardButton("❌ Unsubscribe", callback_data="subscribe_dividend_no")],
    ]

    if query.data == "toto":
        list = ast.literal_eval(await get_subscriptions("toto_reminder"))
        if query.message.chat_id in list:
            reply_markup = InlineKeyboardMarkup(keyboard2)
        else:
            reply_markup = InlineKeyboardMarkup(keyboard1)

        await query.edit_message_text(
            text="ToTo Reminder Service",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    elif query.data == "dividend":
        list = ast.literal_eval(await get_subscriptions("dividend_reminder"))
        if query.message.chat_id in list:
            reply_markup = InlineKeyboardMarkup(keyboard4)
        else:
            reply_markup = InlineKeyboardMarkup(keyboard3)

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


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reminder", reminder))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
