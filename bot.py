from atexit import unregister
from telegram.ext import Application, MessageHandler, CommandHandler, ConversationHandler, filters, PicklePersistence
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from dotenv import load_dotenv
import os
from tgtg import TgtgClient


load_dotenv()


async def start(update, context):
    message = "\n".join([
        "Hello!",
        "I will try to help you not to miss another TGTG offer.",
        "These commands will help you get started:",
        "/start - shows this message",
        "/register - connect your TGTG account",
        "/unregister - disconnect your TGTG account",
        "These commands will help you get food:",
        "/favs - Display currently avialable offers from your favourites.",
    ])
    await update.message.reply_text(message)


async def show_avialable_favourites(update, context):
    client = context.user_data.get("client")
    items = client.get_items()
    for item in items:
        items_available = item["items_available"]
        if items_available > 0:
            store_name = item["store"]["store_name"]
            store_adress = item["store"]["store_location"]["address"]["address_line"]
            item_name = item["item"]["name"]
            item_category = item["item"]["item_category"]
            item_price = item["item"]["price_including_taxes"]["minor_units"] / (10**item["item"]["price_including_taxes"]["decimals"])
            await update.message.reply_text(f"{store_name} has {items_available} {item_name or item_category} avaiable for {item_price}€ each.")
            pickup_start = item["pickup_interval"]["start"]
            pickup_end = item["pickup_interval"]["end"]
            await update.message.reply_text(f"You can pick it up at {store_adress} from {pickup_start} to {pickup_end}")
        

async def start_registration(update, context):
    email = context.user_data.get("registration_email")
    if email is None:
        await update.message.reply_text("Wich email adress did you use to register at TGTG?")
        return 0
    else:
        await update.message.reply_text(f"You are already registered with {email}. Please /unregister first.")
        return ConversationHandler.END

async def get_email(update, context):
    response = update.message.text
    try:
        await update.message.reply_text("If everything worked out you should have an email in your inbox from TGTG. Please click on the link in it to confirm your login.")
        credentials = TgtgClient(email=response).get_credentials()
    except Exception as e:
        await update.message.reply_text(e)
        await update.message.reply_text("Action canceled.")
        return ConversationHandler.END
    else:
        context.user_data["registration_email"] = response
        client = TgtgClient(**credentials, access_token_lifetime = 3600)
        context.user_data["client"] = client
        await update.message.reply_text("Registration successfull!")
        return ConversationHandler.END

async def cancel(update, context):
    await update.message.reply_text(
        "Okay, action was canceled.", 
        reply_markup = ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


registration = ConversationHandler(
    entry_points = [CommandHandler("register", start_registration)],
    states = {
        0: [MessageHandler(filters.TEXT, get_email)],
    },
    fallbacks = [CommandHandler("cancel", cancel)],
)


if __name__ == "__main__":

    builder = Application.builder()
    builder.token(os.getenv("telegram_access_token"))
    builder.persistence(persistence = PicklePersistence(filepath = "storage.pkl"))
    app = builder.build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("favs", show_avialable_favourites))
    app.add_handler(registration)
    print("Start polling ...")
    app.run_polling()
