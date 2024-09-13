import os
import logging
import asyncio
import uvicorn
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, InlineQueryHandler, ContextTypes
import requests

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No TOKEN provided")

WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")
if not WEBHOOK_URL:
    raise ValueError("No WEBHOOK_URL provided")

PORT = int(os.getenv("PORT", "8080"))

ICANHAZDADJOKE_API = "https://icanhazdadjoke.com/"
HEADERS = {
    'Accept': 'application/json',
    'User-Agent': 'Telegram Dad Joke Bot (https://t.me/dadjokezbot)'
}

# Bot handlers
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
    
    joke, joke_id = await get_joke()
    
    if joke:
        results = [
            InlineQueryResultArticle(
                id=joke_id,
                title="Get a dad joke",
                input_message_content=InputTextMessageContent(joke),
                description=joke[:100] + "..." if len(joke) > 100 else joke
            )
        ]
        logger.info(f"Answering inline query with joke: {joke}")
        await update.inline_query.answer(results, cache_time=0)
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

# Starlette routes
async def telegram_webhook(request):
    await application.update_queue.put(Update.de_json(data=await request.json(), bot=application.bot))
    return PlainTextResponse("OK")

async def healthcheck(request):
    return PlainTextResponse("Bot is running!")

async def root(request):
    return PlainTextResponse("Hello, Dad Joke Bot is running!")

routes = [
    Route("/", root),
    Route("/telegram", telegram_webhook, methods=["POST"]),
    Route("/healthcheck", healthcheck)
]

app = Starlette(routes=routes)

# Set up the bot
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(InlineQueryHandler(inline_query))

async def main():
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/telegram")
    await application.start()
    config = uvicorn.Config(app=app, port=PORT, host="0.0.0.0")
    server = uvicorn.Server(config)
    await server.serve()
    await application.stop()

if __name__ == "__main__":
    asyncio.run(main())
