from telegram.ext import Application, MessageHandler, CommandHandler, ConversationHandler, filters, PicklePersistence
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from dotenv import load_dotenv
import os
from tgtg import TgtgClient, DEFAULT_ACCESS_TOKEN_LIFETIME
from appclient import AppClient
from pickle import load
from datetime import timedelta


load_dotenv()


async def start(update, context):
    message = "\n".join([
        "Hello!",
        "I will try to help you not to miss another TGTG offer.",
        "These commands will help you get started:",
        "/start - shows this message",
        "/register - connect your TGTG account",
        "/forgetme - disconnect your TGTG account from the bot",
        "These commands will help you get food:",
        "/favs - Display currently available offers from your favorites.",
    ])
    await update.message.reply_text(message)


async def show_avialable_favorites(update, context):
    client = context.user_data.get("client")
    favorites_available = 0
    for message in client.get_item_texts():
        await update.message.reply_text(
            text = message,
            parse_mode = "HTML",
            disable_web_page_preview = True,
        )
        favorites_available += 1
    if favorites_available == 0:
        await update.message.reply_text(text="I'm sorry but your favorites don't have anything to offer right now :(")

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
    await update.message.reply_markdown("Please open your emails *on your computer* and click on the link in the email to confirm that you are the rightful owner of the TGTG account. (Opening the email on your phone will not work if you already have the app installed.)")
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
        create_refreshlogin_job(context.job_queue, update.message.chat_id)
        create_sendnewitems_job(context.job_queue, update.message.chat_id)
        create_spawnscheduledreminders_job(context.job_queue, update.message.chat_id)
        await update.message.reply_text("Registration successful!")
        await update.message.reply_text("From now on I will check regularly for updates on your favorite shops and notify you whenever some goods are available! :) ")
        return ConversationHandler.END

def create_refreshlogin_job(job_queue, chat_id):
    job_queue.run_repeating(
        callback = refresh_login,
        interval = DEFAULT_ACCESS_TOKEN_LIFETIME * 0.75,
        chat_id = chat_id,
        user_id = chat_id,
        name = f"{chat_id}_refreshlogin",
    )

async def refresh_login(context):
    try:
        context.user_data.get("client").login()
    except Exception as e:
        await context.bot.send_message(
            chat_id = context.job.chat_id, 
            text = f"Error with login: {e}",
        )

def create_sendnewitems_job(job_queue, chat_id):
    job_queue.run_repeating(
        callback = send_new_items,
        first = 1, # run once directly
        interval = timedelta(minutes=15),
        chat_id = chat_id,
        user_id = chat_id,
        name = f"{chat_id}_sendnewitems",
    )

async def send_new_items(context):
    try:
        messages = context.user_data.get("client").get_new_item_texts()
    except Exception as e:
        await context.bot.send_message(
            chat_id = context.job.chat_id, 
            text = f"Error with login: {e}",
        )
    else:
        for text in messages:
            await context.bot.send_message(
                chat_id = context.job.chat_id, 
                text = text,
                parse_mode = "HTML",
                disable_web_page_preview = True,
            )

def create_spawnscheduledreminders_job(job_queue, chat_id):
    job_queue.run_repeating(
        callback = spawn_scheduled_reminders,
        first = 1, # run once directly
        interval = timedelta(hours=3),
        chat_id = chat_id,
        user_id = chat_id,
        name = f"{chat_id}_spawnscheduledreminders",
    )

async def spawn_scheduled_reminders(context):
    for time in context.user_data.get("client").get_scheduled_items_times():
        # recollect all existing jobs to avoid collisions with newly scheduled
        existing_scheduled_remidners = [
            j.next_t for j in context.job_queue.jobs() 
            if (j.chat_id == context.job.chat_id) and (j.callback == send_new_items)
        ]
        if time in existing_scheduled_remidners:
            continue # skip if a reminder for that time is already scheduled
        for buffer in [0, 30, 60]: # retry after expected timepoint (in seconds)
            when = time + timedelta(seconds=buffer)
            context.job_queue.run_once(
                callback = send_new_items,
                when = when,
                chat_id = context.job.chat_id,
                user_id = context.job.chat_id,
                name = f"{context.job.chat_id}_scheduledsendnewitems_{when.isoformat()}",
            )
    
async def cancel(update, context):
    await update.message.reply_text(
        "Okay, action was canceled.", 
        reply_markup = ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def unregister(update, context):
    context.user_data.clear()
    for job in context.job_queue.jobs():
        if job.chat_id == update.message.chat_id:
            job.schedule_removal()
    await update.message.reply_text("All user data deleted from my memory.")


def restart_jobs(app):
    users = load_user_data()
    for chat_id in users.keys():
        if users.get(chat_id).get("client") is None:
            continue # ignore users without saved client
        create_refreshlogin_job(app.job_queue, chat_id)
        create_sendnewitems_job(app.job_queue, chat_id)
        create_spawnscheduledreminders_job(app.job_queue, chat_id)

def load_user_data():
    try:
        with open("storage.pkl", "rb") as file:
            storage = load(file)
        return storage.get("user_data")
    except FileNotFoundError:
        return dict()


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
    app.add_handler(CommandHandler("forgetme", unregister))
    restart_jobs(app) # since jobs are not persisted, they have to be seperatly restarted
    print("Start polling ...")
    app.run_polling()
