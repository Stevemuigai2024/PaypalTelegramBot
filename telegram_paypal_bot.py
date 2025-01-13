import logging
import asyncio
import os
from flask import Flask, request as flask_request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)

# Telegram bot setup
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(TOKEN)
application = Application.builder().token(TOKEN).build()

# Movie catalog
movies = {
    "movie_1": {"title": "Inception", "price": 9.99, "description": "A thief who steals corporate secrets through the use of dream-sharing technology."},
    "movie_2": {"title": "The Dark Knight", "price": 8.99, "description": "Batman must accept one of the greatest psychological and physical tests."}
}

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(movie["title"], callback_data=movie_id)]
        for movie_id, movie in movies.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Welcome to MovieBot! 🎬\nBrowse and buy movies easily.', reply_markup=reply_markup)

# Movie details handler
async def movie_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_id = query.data
    movie = movies.get(movie_id, {})
    if movie:
        text = f"*{movie['title']}*\n\n{movie['description']}\n\nPrice: ${movie['price']}"
        await query.edit_message_text(text=text, parse_mode='Markdown')
    else:
        await query.edit_message_text(text="Movie not found.")

# Flask webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("Webhook received")
    logger.info(f"Request JSON: {flask_request.get_json()}")
    try:
        update = Update.de_json(flask_request.get_json(force=True), bot)
        asyncio.run(application.process_update(update))
    except Exception as e:
        logger.error(f"Error processing update: {e}")
    return 'ok', 200

# Set up handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(movie_details))

# Run Flask app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port)

# Start the bot asynchronously
async def main():
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.idle()

asyncio.run(main())
