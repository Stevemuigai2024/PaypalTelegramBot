import logging
import asyncio
import os
from flask import Flask, request as flask_request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from threading import Thread
from telegram.request import HTTPXRequest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)

# Telegram bot setup
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Bot token is not set. Please check your .env file or environment variables.")

request = HTTPXRequest(
    connection_pool_size=64,
    connect_timeout=30,
    read_timeout=30,
    pool_timeout=30
)

bot = Bot(token=BOT_TOKEN, request=request)
application = Application.builder().token(BOT_TOKEN).request(request).build()

# Load movies database
movies = [
    {
        "id": "1",
        "title": "Inception",
        "description": "A thief with the ability to enter people's dreams and steal secrets from their subconscious.",
        "price": 10.99,
        "preview_video": "https://example.com/preview/inception",
        "download_link": "https://example.com/downloads/inception"
    },
    {
        "id": "2",
        "title": "The Dark Knight",
        "description": "Batman raises the stakes in his war on crime with the help of Lieutenant Jim Gordon and District Attorney Harvey Dent.",
        "price": 8.99,
        "preview_video": "https://example.com/previews/dark-knight.mp4",
        "download_link": "https://example.com/downloads/dark-knight"
    }
]

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info("Start command received")
        keyboard = [
            [InlineKeyboardButton(movie["title"], callback_data=movie["id"])]
            for movie in movies
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Welcome to MovieBot! 🎬\nBrowse and buy movies easily.', reply_markup=reply_markup)
        logger.info("Sent start message")
    except Exception as e:
        logger.error(f"Error in start handler: {e}", exc_info=True)

# Movie details handler
async def movie_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info("Movie details received")
        query = update.callback_query
        await query.answer()
        movie_id = query.data
        movie = next((m for m in movies if m["id"] == movie_id), None)
        if movie:
            text = f"*{movie['title']}*\n\n{movie['description']}\n\nPrice: ${movie['price']}"
            await query.edit_message_text(text=text, parse_mode='Markdown')
            logger.info(f"Sent details for movie: {movie_id}")
        else:
            await query.edit_message_text(text="Movie not found.")
            logger.info(f"Movie not found: {movie_id}")
    except Exception as e:
        logger.error(f"Error in movie_details handler: {e}", exc_info=True)

# Flask webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("Webhook received")
    try:
        update_json = flask_request.get_json(force=True)
        logger.info(f"Request JSON: {update_json}")
        update = Update.de_json(update_json, bot)
        
        # Run the update processing in the existing event loop
        async def process_update():
            await application.process_update(update)
            logger.info("Update processed")

        asyncio.run(process_update())
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
    return 'ok', 200

# Set up handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(movie_details))

# Function to run the bot
async def start_bot():
    try:
        logger.info("Starting bot initialization")
        await bot.initialize()
        logger.info("Bot initialized")
        await application.initialize()
        logger.info("Application initialized")
        await application.start()
        logger.info("Application started")
        logger.info("Bot started.")
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)

# Run Flask app
if __name__ == '__main__':
    try:
        port = int(os.getenv("PORT", 10000))
        logger.info(f"Starting Flask app on port {port}")

        loop = asyncio.get_event_loop()

        # Run bot in a separate thread
        Thread(target=lambda: loop.run_until_complete(start_bot()), daemon=True).start()

        # Start Flask server
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
