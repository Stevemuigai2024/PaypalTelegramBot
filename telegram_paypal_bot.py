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

# Load environment variables
load_dotenv()

app = Flask(__name__)

port = int(os.getenv("PORT", 10000))

@app.route('/')
def home():
    return 'Hello World!'

@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("Webhook received")
    logger.info(f"Request JSON: {request.get_json()}")
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        asyncio.create_task(application.process_update(update))
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

# Create bot and application
bot = Bot(token=BOT_TOKEN)
application = Application.builder().token(BOT_TOKEN).build()

# Configure PayPal
paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" for production
    "client_id": os.getenv("PAYPAL_CLIENT_ID"),  # Load from environment
    "client_secret": os.getenv("PAYPAL_CLIENT_SECRET")  # Load from environment
})

# Load movies database
with open('movies.json', 'r') as file:
    movies = json.load(file)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "Welcome to MovieBot! 🎬\nBrowse and buy movies easily."
    keyboard = [[InlineKeyboardButton(movie["title"], callback_data=f"movie_{movie['id']}") for movie in movies]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# Handle movie selection
async def movie_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

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
    await query.answer()

    movie_id = query.data.split("_")[1]
    movie = next((m for m in movies if m["id"] == movie_id), None)

    if movie:
        # Create PayPal payment
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal
