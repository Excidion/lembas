from telegram.ext import Application, MessageHandler, CommandHandler, ConversationHandler, filters, PicklePersistence
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from dotenv import load_dotenv
import os
from tgtg import TgtgClient, DEFAULT_ACCESS_TOKEN_LIFETIME
from appclient import AppClient
from pickle import load


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
        "/favs - Display currently available offers from your favorites.",
    ])
    await update.message.reply_text(message)


async def show_avialable_favorites(update, context):
    client = context.user_data.get("client")
    items = client.get_items()
    for item in items:
        items_available = item["items_available"]
        if items_available > 0:
            store_name = item["store"]["store_name"]
            store_address = item["store"]["store_location"]["address"]["address_line"]
            item_name = item["item"]["name"]
            item_category = item["item"]["item_category"]
            item_price = item["item"]["price_including_taxes"]["minor_units"] / (10**item["item"]["price_including_taxes"]["decimals"])
            await update.message.reply_text(f"{store_name} has {items_available} {item_name or item_category} avaiable for {item_price}€ each.")
            pickup_start = item["pickup_interval"]["start"]
            pickup_end = item["pickup_interval"]["end"]
            await update.message.reply_text(f"You can pick it up at {store_address} from {pickup_start} to {pickup_end}")
        

async def start_registration(update, context):
    client = context.user_data.get("client")
    if client is None:
        await update.message.reply_text("Which email address did you use to register at TGTG?")
        return 0
    else:
        await update.message.reply_text(f"You are already registered with {client.registration_email}. Please /unregister first.")
        return ConversationHandler.END

async def get_email(update, context):
    response = update.message.text
    await update.message.reply_text(f"You should now receive an email from TGTG to your inbox ({response}).")
    await update.message.reply_text("Please click on the link in the email to confirm you are the rightful owner of the account.")
    try:
        credentials = TgtgClient(email=response).get_credentials()
    except Exception as e:
        await update.message.reply_text(e)
        await update.message.reply_text("Action canceled.")
        return ConversationHandler.END
    else:
        client = AppClient(**credentials)
        client.registration_email = response
        context.user_data["client"] = client
        context.job_queue.run_repeating(
            callback = refresh_login,
            interval = DEFAULT_ACCESS_TOKEN_LIFETIME * 0.75,
            chat_id = update.message.chat_id,
            name = f"{update.message.chat_id}_refreshlogin",
        )
        await update.message.reply_text("Registration successful!")
        return ConversationHandler.END

async def refresh_login(context):
    try:
        context.job.context.user_data.get("client").refresh_token()
    except Exception as e:
        await context.bot.send_message(
            chat_id = context.job.chat_id, 
            text = f"Error with login: {e}",
        )

async def cancel(update, context):
    await update.message.reply_text(
        "Okay, action was canceled.", 
        reply_markup = ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


def restart_jobs(app):
    users = load_user_data()
    for chat_id in users.keys():
        app.job_queue.run_repeating(
            callback = refresh_login,
            interval = DEFAULT_ACCESS_TOKEN_LIFETIME * 0.75,
            chat_id = chat_id,
            name = f"{chat_id}_refreshlogin",
        )

def load_user_data():
    with open("storage.pkl", "rb") as file:
        storage = load(file)
    return storage.get("user_data")
    
async def show_jobs(update, context):
    for job in context.job_queue.jobs():
        if job.chat_id == update.message.chat_id:
            await update.message.reply_text(job.name)


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
    app.add_handler(CommandHandler("favs", show_avialable_favorites))
    app.add_handler(CommandHandler("jobs", show_jobs))
    app.add_handler(registration)
    restart_jobs(app) # since jobs are not persisted, they have to be seperatly restarted
    print("Start polling ...")
    app.run_polling()
