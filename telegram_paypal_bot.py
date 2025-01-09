from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
import paypalrestsdk
import json
import logging
import asyncio

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure PayPal
paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" for production
    "client_id": "AUJyNrn8-dgBmGkibJj2Wv0fO4iiKh5uE5rRn5szxdkNHdGrnUZm9RUilZ5LusIYXoFoHABzN1-5xV89",  # Replace with your PayPal Client ID
    "client_secret": "EKb8-RBtQvzF0YHoZ1rslR7-BSIQM2hD2qbWhJQNk-F22GF3Vit-OKtiaWirKOTgHfcHdCxK_DO62hEJ"  # Replace with your PayPal Client Secret
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
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": "https://yourserver.com/payment/return",
                "cancel_url": "https://yourserver.com/payment/cancel"
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

# Main function
def main():
    # Create application
    application = Application.builder().token("YOUR_TELEGRAM_BOT_TOKEN").build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(movie_details, pattern="^movie_"))
    application.add_handler(CallbackQueryHandler(handle_purchase, pattern="^buy_"))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
