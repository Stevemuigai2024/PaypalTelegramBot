import logging
import asyncio
import os
from flask import Flask, request as flask_request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram Bot Token from environment variable
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_TOKEN:
    logger.error("Telegram bot token not found. Please set the TELEGRAM_BOT_TOKEN environment variable.")
    exit(1)

# Flask app
app = Flask(__name__)

# HTTPX Async Client
request = HTTPXRequest()

# Initialize Bot and Application
bot = Bot(token=TELEGRAM_TOKEN, request=request)
application = Application.builder().token(TELEGRAM_TOKEN).request(request).build()

# Error Handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg=f'Update {update} caused error {context.error}', exc_info=True)

# Add error handler
application.add_error_handler(error_handler)

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Buy Movie", callback_data='buy_movie')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text('Welcome! Click below to buy a movie.', reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text('Welcome! Click below to buy a movie.', reply_markup=reply_markup)

# Buy Movie callback handler
async def buy_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Processing your purchase...")
    # Simulate processing
    await asyncio.sleep(2)
    await query.edit_message_text(text="Purchase complete! Enjoy your movie.")

# Register Handlers
application.add_handler(CommandHandler('start', start))
application.add_handler(CallbackQueryHandler(buy_movie, pattern='^buy_movie$'))

# Initialize bot and application properly
async def initialize():
    await bot.initialize()
    await application.initialize()
    await application.start()
    logger.info("Bot and application have started successfully.")

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(flask_request.get_json(force=True), bot)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.run(application.process_update(update))
    return 'OK'

if __name__ == '__main__':
    # Ensure the requirements are installed, e.g., `pip install -r requirements.txt`
    loop = asyncio.get_event_loop()
    loop.run_until_complete(initialize())
    
    # Define the port from an environment variable provided by Render
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port)  # Bind to 0.0.0.0 to allow external connections
