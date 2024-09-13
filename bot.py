import os
import logging
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, InlineQueryHandler, ContextTypes
import requests
from flask import Flask, request

# Use environment variable for API key
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("No API token found. Please set the TELEGRAM_BOT_TOKEN environment variable.")

# Set up logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ICANHAZDADJOKE_API = "https://icanhazdadjoke.com/"
HEADERS = {
    'Accept': 'application/json',
    'User-Agent': 'Telegram Dad Joke Bot (https://t.me/dadjokezbot)'
}

app = Flask(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Start command received from user {update.effective_user.id}")
    await update.message.reply_text("I'm a dad joke bot! Use me inline in any chat by typing @dadjokezbot followed by a space.")

async def get_joke():
    try:
        logger.info("Attempting to fetch joke from API")
        response = requests.get(ICANHAZDADJOKE_API, headers=HEADERS)
        response.raise_for_status()
        joke_data = response.json()
        logger.info(f"Joke fetched successfully: {joke_data['id']}")
        return joke_data['joke'], joke_data['id']
    except requests.RequestException as e:
        logger.error(f"Failed to fetch joke: {e}")
        return None, None

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query
    logger.info(f"Inline query received: '{query}' from user {update.effective_user.id}")
    
    try:
        joke, joke_id = await get_joke()
        logger.info(f"Joke fetched: {joke}")
        
        if joke:
            results = [
                InlineQueryResultArticle(
                    id=joke_id,
                    title="Get a dad joke",
                    input_message_content=InputTextMessageContent(joke),
                    description=joke[:100] + "..." if len(joke) > 100 else joke
                )
            ]
            logger.info(f"Answering inline query with results: {results}")
            await update.inline_query.answer(results, cache_time=0)
            logger.info(f"Inline query answered successfully for user {update.effective_user.id}")
        else:
            logger.error("Failed to fetch joke for inline query")
            results = [
                InlineQueryResultArticle(
                    id='error',
                    title="Error fetching joke",
                    input_message_content=InputTextMessageContent("Sorry, I couldn't fetch a joke right now. Please try again later.")
                )
            ]
            await update.inline_query.answer(results, cache_time=0)
    except Exception as e:
        logger.error(f"Error in inline query: {str(e)}")

application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(InlineQueryHandler(inline_query))

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), application.bot)
    application.process_update(update)
    return 'OK'

@app.route('/')
def index():
    return 'Hello, Dad Joke Bot is running!'

if __name__ == '__main__':
    app.run(port=int(os.environ.get('PORT', 5000)))
