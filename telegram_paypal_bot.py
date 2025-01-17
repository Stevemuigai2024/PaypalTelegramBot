import logging
import asyncio
import os
import gc
import json
from flask import Flask, request as flask_request, jsonify
import paypalrestsdk
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest
import httpx

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram Bot Token and PayPal settings from environment variable
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_TOKEN:
    logger.error("Telegram bot token not found. Please set the TELEGRAM_BOT_TOKEN environment variable.")
    exit(1)

PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET')

# Flask app
app = Flask(__name__)

# HTTPX Async Client with increased pool limits and timeout
client = httpx.AsyncClient(
    limits=httpx.Limits(max_keepalive_connections=200, max_connections=1000),
    timeout=httpx.Timeout(60.0),
    headers={"Connection": "keep-alive"}
)

# Initialize Bot and Application using HTTPXRequest with the custom client
request = HTTPXRequest()
bot = Bot(token=TELEGRAM_TOKEN, request=request)
application = Application.builder().token(TELEGRAM_TOKEN).request(request).build()

# PayPal configuration
paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" for production
    "client_id": PAYPAL_CLIENT_ID,
    "client_secret": PAYPAL_CLIENT_SECRET
})

# Load shows data from JSON file
with open('shows.json', 'r') as f:
    wwe_shows = json.load(f)

# Error Handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg=f'Update {update} caused error {context.error}', exc_info=True)

# Add error handler
application.add_error_handler(error_handler)

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("WWE RAW", callback_data='show_RAW')],
        [InlineKeyboardButton("WWE SMACKDOWN", callback_data='show_SMACKDOWN')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "Welcome to our WWE official telegram bot! 🏆 Watch shows for $0.20 only 🎉"
    if update.message:
        await update.message.reply_text(message, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(message, reply_markup=reply_markup)

# Show details handler
async def show_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    show_key = query.data.split('_')[1]
    show = wwe_shows[show_key]

    keyboard = [[InlineKeyboardButton("Buy", callback_data=f'buy_{show_key}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = f"{show['description']}\n\n![Cover Photo]({show['cover_photo']})"
    await query.answer()
    await query.edit_message_text(text=message, parse_mode='Markdown', reply_markup=reply_markup)

# Buy show handler
async def buy_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    show_key = query.data.split('_')[1]
    show = wwe_shows[show_key]

    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {"payment_method": "paypal"},
        "transactions": [{
            "item_list": {
                "items": [{"name": f"WWE {show_key}", "sku": f"WWE_{show_key}", "price": str(show['price']), "currency": "USD", "quantity": 1}]
            },
            "amount": {"total": str(show['price']), "currency": "USD"},
            "description": f"Purchase of WWE {show_key}"
        }],
        "redirect_urls": {
            "return_url": f"https://example.com/payment/execute?show={show_key}",
            "cancel_url": "https://example.com/payment/cancel"
        }
    })

    if payment.create():
        approval_url = next(link.href for link in payment.links if link.rel == "approval_url")
        keyboard = [[InlineKeyboardButton("Pay with PayPal", url=approval_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Click the button below to complete your purchase:", reply_markup=reply_markup)
    else:
        await query.edit_message_text(text="An error occurred while creating the payment. Please try again.")

# Payment execution endpoint
@app.route('/payment/execute', methods=['GET'])
def execute_payment():
    payment_id = flask_request.args.get('paymentId')
    payer_id = flask_request.args.get('PayerID')
    show_key = flask_request.args.get('show')

    payment = paypalrestsdk.Payment.find(payment_id)
    if payment.execute({"payer_id": payer_id}):
        show = wwe_shows[show_key]
        return jsonify({'message': 'Payment successful!', 'download_link': show['download_link']})
    return jsonify({'message': 'Payment execution failed.'}), 400

# Register Handlers
application.add_handler(CommandHandler('start', start))
application.add_handler(CallbackQueryHandler(show_details, pattern='^show_'))
application.add_handler(CallbackQueryHandler(buy_show, pattern='^buy_'))

# Initialize bot and application properly
async def initialize():
    await bot.initialize()
    await application.initialize()
    await application.start()
    logger.info('Bot and application have started successfully.')

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(flask_request.get_json(force=True), bot)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.process_update(update))
    loop.close()

    clear_memory()
    return 'OK'

def clear_memory():
    gc.collect()
    logger.info("Memory cleared to prevent overload.")

if __name__ == '__main__':
    asyncio.run(initialize())
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port)
