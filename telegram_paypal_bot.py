import logging
import asyncio
import os
from flask import Flask, request as flask_request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from threading import Thread
from telegram.request import HTTPXRequest

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Corrected format string
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)

# Telegram bot setup
TOKEN = "7964230854:AAHb1cv8J42SHksH9Vaq_DBaKNbhKGzLoMA"

request = HTTPXRequest(
    connection_pool_size=64,  # Set a balanced pool size
    connect_timeout=30,
    read_timeout=30,
    pool_timeout=30
)

bot = Bot(token=TOKEN, request=request)
application = Application.builder().token(TOKEN).request(request).build()

# Movie catalog
movies = {
    "movie_1": {"title": "Inception", "price": 9.99, "description": "A thief who steals corporate secrets through the use of dream-sharing technology."},
    "movie_2": {"title": "The Dark Knight", "price": 8.99, "description": "Batman must accept one of the greatest psychological and physical tests."}
}

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info("Start command received")
        keyboard = [
            [InlineKeyboardButton(movie["title"], callback_data=movie_id)]
            for movie_id, movie in movies.items()
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Welcome to MovieBot! 🎬\nBrowse and buy movies easily.', reply_markup=reply_markup)
        logger.info("Sent start message")
    except Exception as e:
        logger.error(f"Error in start handler: {e}")

# Movie details handler
async def movie_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info("Movie details received")
        query = update.callback_query
        await query.answer()
        movie_id = query.data
        movie = movies.get(movie_id, {})
        if movie:
            text = f"*{movie['title']}*\n\n{movie['description']}\n\nPrice: ${movie['price']}"
            await query.edit_message_text(text=text, parse_mode='Markdown')
            logger.info(f"Sent details for movie: {movie_id}")
        else:
            await query.edit_message_text(text="Movie not found.")
            logger.info(f"Movie not found: {movie_id}")
    except Exception as e:
        logger.error(f"Error in movie_details handler: {e}")

# Flask webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("Webhook received")
    try:
        update_json = flask_request.get_json(force=True)
        logger.info(f"Request JSON: {update_json}")
        update = Update.de_json(update_json, bot)
        asyncio.run_coroutine_threadsafe(application.process_update(update), loop)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
    return 'ok', 200

# Set up handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(movie_details))

# Function to run the bot
async def start_bot():
    try:
        await bot.initialize()
        await application.initialize()
        await application.start()
        logger.info("Bot started.")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

# Run Flask app
if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Starting Flask app on port {port}")

        loop = asyncio.get_event_loop()

        # Run bot in a separate thread
        Thread(target=lambda: loop.run_until_complete(start_bot()), daemon=True).start()

        # Start Flask server
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Error in main: {e}")
