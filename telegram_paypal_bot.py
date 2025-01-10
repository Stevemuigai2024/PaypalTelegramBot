from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from flask import Flask, request
from dotenv import load_dotenv
import os
import paypalrestsdk
import json
import logging
import asyncio
from telegram.request import Request
from telegram.error import BadRequest

# Load environment variables
load_dotenv()

app = Flask(__name__)

port = int(os.getenv("PORT", 10000))

@app.route('/')
async def home():
    return 'Hello World!'

@app.route('/webhook', methods=['POST'])
async def webhook():
    logger.info("Webhook received")
    logger.info(f"Request JSON: {request.get_json()}")
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
    return 'ok', 200

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Load bot token from environment
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Bot token is not set. Please check your .env file or environment variables.")

# Increase connection pool size and timeout
request = Request(
    connection_pool_size=16,  # Increase the pool size as needed
    connect_timeout=10,
    read_timeout=10,
    pool_timeout=10
)

# Create bot and application
bot = Bot(token=BOT_TOKEN, request=request)
application = Application.builder().token(BOT_TOKEN).request(request).build()

# Configure PayPal
paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" for production
    "client_id": os.getenv("PAYPAL_CLIENT_ID"),  # Load from environment
    "client_secret": os.getenv("PAYPAL_CLIENT_SECRET")  # Load from environment
})

# Load movies database
with open('movies.json', 'r') as file:
    movies = json.load(file)

# Error handler function
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# Add error handler
application.add_error_handler(error_handler)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "Welcome to MovieBot! 🎬\nBrowse and buy movies easily."
    keyboard = [[InlineKeyboardButton(movie["title"], callback_data=f"movie_{movie['id']}") for movie in movies]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# Handle movie selection
async def movie_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest as e:
        logger.error(f"Failed to answer callback query: {e}")

    movie_id = query.data.split("_")[1]
    movie = next((m for m in movies if m["id"] == movie_id), None)

    if movie:
        text = f"*{movie['title']}*\n{movie['description']}\nPrice: ${movie['price']}"
        keyboard = [[InlineKeyboardButton("Buy Now", callback_data=f"buy_{movie['id']}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_photo(photo=movie["cover"], caption=text, parse_mode="Markdown", reply_markup=reply_markup)

# Handle purchase
async def handle_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest as e:
        logger.error(f"Failed to answer callback query: {e}")

    movie_id = query.data.split("_")[1]
    movie = next((m for m in movies if m["id"] == movie_id), None)

    if movie:
        # Create PayPal payment
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": "https://paypaltelegrambot.onrender.com/payment/return",
                "cancel_url": "https://paypaltelegrambot.onrender.com/payment/cancel"
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": movie["title"],
                        "sku": movie["id"],
                        "price": str(movie["price"]),
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": str(movie["price"]),
                    "currency": "USD"
                },
                "description": movie["description"]
            }]
        })

        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    approval_url = link.href
                    keyboard = [[InlineKeyboardButton("Pay with PayPal", url=approval_url)]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text("Click below to complete your purchase:", reply_markup=reply_markup)
                    return
        else:
            logger.error(payment.error)
            await query.message.reply_text("Payment creation failed. Please try again later.")

# After successful payment, send download link
async def send_download_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Verify payment using PayPal SDK or webhook listener
    # Placeholder logic for actual verification
    movie_id = "1"  # Replace with dynamic extraction from payment metadata
    movie = next((m for m in movies if m["id"] == movie_id), None)

    if movie:
        await update.message.reply_text(f"Thank you for your purchase! 🎉\nHere is your download link: {movie['download_link']}")

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(movie_details, pattern="^movie_"))
application.add_handler(CallbackQueryHandler(handle_purchase, pattern="^buy_"))

async def main():
    webhook_url = f"https://paypaltelegrambot.onrender.com/webhook"
    await bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

    await application.initialize()
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    asyncio.run(main())
