import logging
import asyncio
import os
from flask import Flask, request as flask_request, jsonify
import paypalrestsdk
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

# Configure HTTPXRequest with increased connection pooling
request = HTTPXRequest(
    connection_pool_size=128,
    connect_timeout=30,
    read_timeout=30,
    pool_timeout=60
)

bot = Bot(token=BOT_TOKEN, request=request)
application = Application.builder().token(BOT_TOKEN).request(request).build()

# PayPal configuration
paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" for production
    "client_id": os.getenv("PAYPAL_CLIENT_ID"),
    "client_secret": os.getenv("PAYPAL_CLIENT_SECRET")
})

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

# Safe query answer with retries
async def safe_query_answer(query):
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Query answer failed: {e}, retrying...")
        await asyncio.sleep(1)
        await query.answer()

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Inception", callback_data="1")],
        [InlineKeyboardButton("The Dark Knight", callback_data="2")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text('Welcome to MovieBot! 🎬\nBrowse and buy movies easily.', reply_markup=reply_markup)

# Movie details handler
async def movie_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_query_answer(query)
    movie_id = query.data
    movie = next((m for m in movies if m["id"] == movie_id), None)
    if movie:
        text = f"*{movie['title']}*\n\n{movie['description']}\n\nPrice: ${movie['price']}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Pay with PayPal", callback_data=f"buy_{movie['id']}")],
            [InlineKeyboardButton("🔄 Start Over", callback_data="start_over")]
        ])
        await query.edit_message_text(text=text, parse_mode='Markdown', reply_markup=keyboard)

# Buy movie handler
async def buy_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_query_answer(query)
    movie_id = query.data.split('_')[1]
    movie = next((m for m in movies if m["id"] == movie_id), None)
    if movie:
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "transactions": [{
                "item_list": {"items": [{
                    "name": movie['title'],
                    "sku": movie['id'],
                    "price": str(movie['price']),
                    "currency": "USD",
                    "quantity": 1
                }]},
                "amount": {"total": str(movie['price']), "currency": "USD"},
                "description": f"Purchase of {movie['title']}"
            }],
            "redirect_urls": {
                "return_url": f"https://example.com/payment/execute?movie_id={movie['id']}",
                "cancel_url": "https://example.com/payment/cancel"
            }
        })
        if payment.create():
            approval_url = next(link.href for link in payment.links if link.rel == "approval_url")
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("💳 Pay with PayPal", url=approval_url)]])
            await query.edit_message_text(text="Click the button below to complete your purchase:", reply_markup=keyboard)

# Flask webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    update_json = flask_request.get_json(force=True)
    update = Update.de_json(update_json, bot)
    asyncio.run(application.process_update(update))
    return 'ok', 200

# Set up handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(movie_details, pattern='^\\d+$'))
application.add_handler(CallbackQueryHandler(buy_movie, pattern='^buy_\\d+$'))
application.add_handler(CallbackQueryHandler(start, pattern='start_over'))

# Function to run the bot
async def start_bot():
    await application.initialize()
    await application.start()

# Run Flask app
if __name__ == '__main__':
    port = int(os.getenv("PORT", 10000))
    Thread(target=lambda: asyncio.run(start_bot()), daemon=True).start()
    app.run(host='0.0.0.0', port=port)
