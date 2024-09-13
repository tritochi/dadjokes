import asyncio
import logging
import os
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, InlineQueryHandler, ContextTypes
import requests

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Define configuration constants
URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 8000))
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

ICANHAZDADJOKE_API = "https://icanhazdadjoke.com/"
HEADERS = {
    'Accept': 'application/json',
    'User-Agent': 'Telegram Dad Joke Bot (https://t.me/dadjokezbot)'
}

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

async def main() -> None:
    application = Application.builder().token(TOKEN).updater(None).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(InlineQueryHandler(inline_query))

    await application.bot.set_webhook(url=f"{URL}/telegram", allowed_updates=Update.ALL_TYPES)

    async def telegram(request: Request) -> Response:
        await application.update_queue.put(
            Update.de_json(data=await request.json(), bot=application.bot)
        )
        return Response()

    async def health(_: Request) -> PlainTextResponse:
        return PlainTextResponse(content="The bot is still running fine!")

    starlette_app = Starlette(
        routes=[
            Route("/telegram", telegram, methods=["POST"]),
            Route("/healthcheck", health, methods=["GET"]),
        ]
    )

    webserver = uvicorn.Server(
        config=uvicorn.Config(
            app=starlette_app,
            port=PORT,
            use_colors=False,
            host="0.0.0.0",
        )
    )

    async with application:
        await application.start()
        await webserver.serve()
        await application.stop()

if __name__ == "__main__":
    asyncio.run(main())
