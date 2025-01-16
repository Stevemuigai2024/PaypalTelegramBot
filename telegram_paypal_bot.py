import logging
import asyncio
import os
from flask import Flask, request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

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

# Initialize Bot and Application
bot = Bot(token=TELEGRAM_TOKEN)
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Error Handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg=f'Update {update} caused error {context.error}', exc_info=True)

# Add error handler
application.add_error_handler(error_handler)

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Buy Movie", callback_data='buy_movie')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Welcome! Click below to buy a movie.', reply_markup=reply_markup)

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

# Flask Webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(application.process_update(update))
    return 'OK'

async def run_bot():
    await bot.initialize()
    await application.initialize()
    await application.start()
    logger.info("Bot and application have started successfully.")

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())
    app.run(port=5000)
