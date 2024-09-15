import logging
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, ContextTypes, InlineQueryHandler
import requests
import time
import json
from flask import Flask
from threading import Thread

# Bot token included directly in the code as requested
BOT_TOKEN = "6332254372:AAGoCkC6FybzWliPp8mrH-H9um8w9E6rHDU"

# Set up logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ICANHAZDADJOKE_API = "https://icanhazdadjoke.com/"
ADVICESLIP_API = "https://api.adviceslip.com/advice"
USELESS_FACTS_API = "https://uselessfacts.jsph.pl/api/v2/facts/random"
HEADERS = {
    'Accept': 'application/json',
    'User-Agent': 'Telegram Dad Joke, Advice, and Useless Facts Bot (https://t.me/dadjokezbot)'
}

app = Flask('')

@app.route('/')
def home():
    return "Hello. I am alive!"

@app.route('/health')
def health():
    return "Bot is healthy!", 200

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Start command received from user {update.effective_user.id}")
    await update.message.reply_text(
        "Welcome to the Dad Joke, Advice, and Useless Facts Bot! Here are the available commands:\n"
        "/joke - Get a dad joke\n"
        "/advice - Get some advice\n"
        "/fact - Get a random useless fact\n"
        "You can also use me inline in any chat by typing @dadjokezbot followed by a space."
    )

async def get_joke():
    try:
        params = {'timestamp': int(time.time() * 1000)}
        logger.debug(f"Attempting to fetch joke from API with params: {params}")
        response = requests.get(ICANHAZDADJOKE_API, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        joke_data = response.json()
        logger.debug(f"Joke fetched successfully: {joke_data['id']}")
        return joke_data['joke'], joke_data['id']
    except requests.RequestException as e:
        logger.error(f"Failed to fetch joke: {e}")
        return None, None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse joke API response: {e}")
        return None, None

async def get_advice():
    try:
        params = {'timestamp': int(time.time() * 1000)}
        logger.debug(f"Attempting to fetch advice from API with params: {params}")
        response = requests.get(ADVICESLIP_API, params=params, timeout=10)
        response.raise_for_status()
        advice_data = response.json()
        logger.debug(f"Advice fetched successfully: {advice_data['slip']['id']}")
        return advice_data['slip']['advice'], advice_data['slip']['id']
    except requests.RequestException as e:
        logger.error(f"Failed to fetch advice: {e}")
        return None, None
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse advice API response: {e}")
        return None, None

async def get_fact():
    try:
        params = {'language': 'en'}
        logger.debug(f"Attempting to fetch useless fact from API with params: {params}")
        response = requests.get(USELESS_FACTS_API, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        fact_data = response.json()
        logger.debug(f"Useless fact fetched successfully: {fact_data['id']}")
        return fact_data['text'], fact_data['id']
    except requests.RequestException as e:
        logger.error(f"Failed to fetch useless fact: {e}")
        return None, None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse useless fact API response: {e}")
        return None, None

async def send_joke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    joke, _ = await get_joke()
    if joke:
        await update.message.reply_text(f"Here's your dad joke:\n\n{joke}")
    else:
        await update.message.reply_text("Sorry, I couldn't fetch a joke right now. Please try again later.")

async def send_advice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    advice, _ = await get_advice()
    if advice:
        await update.message.reply_text(f"Here's your advice:\n\n{advice}")
    else:
        await update.message.reply_text("Sorry, I couldn't fetch any advice right now. Please try again later.")

async def send_fact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    fact, _ = await get_fact()
    if fact:
        await update.message.reply_text(f"Here's your useless fact:\n\n{fact}")
    else:
        await update.message.reply_text("Sorry, I couldn't fetch a useless fact right now. Please try again later.")

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query.lower()
    logger.info(f"Inline query received: '{query}' from user {update.effective_user.id}")

    results = []

    # Fetch joke, advice, and fact
    joke, joke_id = await get_joke()
    advice, advice_id = await get_advice()
    fact, fact_id = await get_fact()

    if joke:
        results.append(InlineQueryResultArticle(
            id=f'joke_{joke_id}',
            title="Get a dad joke",
            description="Fetch a random dad joke",
            input_message_content=InputTextMessageContent(f"Here's your dad joke:\n\n{joke}")
        ))

    if advice:
        results.append(InlineQueryResultArticle(
            id=f'advice_{advice_id}',
            title="Get some advice",
            description="Fetch a random piece of advice",
            input_message_content=InputTextMessageContent(f"Here's your advice:\n\n{advice}")
        ))

    if fact:
        results.append(InlineQueryResultArticle(
            id=f'fact_{fact_id}',
            title="Get a useless fact",
            description="Fetch a random useless fact",
            input_message_content=InputTextMessageContent(f"Here's your useless fact:\n\n{fact}")
        ))

    results.append(InlineQueryResultArticle(
        id='help',
        title="Help",
        description="Show available commands",
        input_message_content=InputTextMessageContent(
            "Available commands:\n"
            "/joke - Get a dad joke\n"
            "/advice - Get some advice\n"
            "/fact - Get a random useless fact\n"
            "Just type @dadjokezbot in any chat to see these options!"
        )
    ))

    logger.debug(f"Answering inline query with results: {results}")
    await update.inline_query.answer(results, cache_time=0)
    logger.info(f"Inline query answered successfully for user {update.effective_user.id}")

def main() -> None:
    logger.info("Starting the bot")
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("joke", send_joke))
    application.add_handler(CommandHandler("advice", send_advice))
    application.add_handler(CommandHandler("fact", send_fact))
    application.add_handler(InlineQueryHandler(inline_query))

    logger.info("Handlers added, starting polling")
    keep_alive()
    application.run_polling()

if __name__ == '__main__':
    main()
