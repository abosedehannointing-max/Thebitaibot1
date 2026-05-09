import os
import asyncio
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from flask import Flask
import threading

# ============= CONFIG =============
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
PORT = int(os.environ.get("PORT", 10000))
USER_DATA_FILE = "user_data.json"

# User states
STATE_ENTRY = "entry"
STATE_WAITING_BINANCE = "waiting_binance"
STATE_LICENSE = "license"
STATE_FUTURES = "futures"
STATE_API = "api"
STATE_TRANSFER = "transfer"
STATE_RISK = "risk"
STATE_COMPLETED = "completed"

# ============= DATA MANAGEMENT =============
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f)

user_data = load_user_data()

def get_user_state(user_id):
    return user_data.get(str(user_id), {}).get("state", STATE_ENTRY)

def update_user_state(user_id, state, step=0):
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {}
    user_data[str(user_id)]["state"] = state
    user_data[str(user_id)]["step"] = step
    user_data[str(user_id)]["last_action"] = datetime.now().isoformat()
    user_data[str(user_id)]["reminder_sent"] = False
    save_user_data(user_data)

def mark_user_completed(user_id):
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {}
    user_data[str(user_id)]["state"] = STATE_COMPLETED
    user_data[str(user_id)]["completed_at"] = datetime.now().isoformat()
    save_user_data(user_data)

def get_incomplete_users():
    incomplete = []
    now = datetime.now()
    for uid, data in user_data.items():
        if data.get("state") != STATE_COMPLETED:
            last_action = datetime.fromisoformat(data.get("last_action", datetime.now().isoformat()))
            if now - last_action > timedelta(hours=6):
                if not data.get("reminder_sent"):
                    incomplete.append((uid, data))
    return incomplete

# ============= KEYBOARDS =============
def get_entry_keyboard():
    keyboard = [
        [InlineKeyboardButton("📝 Register my FREE BitAI account", url="https://app.bitai.com.sg/h5/#/pages/sign/sign?invite=888")],
        [InlineKeyboardButton("📱 Download BitAI (iOS & Android)", url="https://fir.bitai.app/app.html")],
        [InlineKeyboardButton("▶️ BitAI Setup Video", callback_data="setup_video")],
        [InlineKeyboardButton("📞 Contact support", url="http://wa.me/6589691668")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_binance_keyboard():
    keyboard = [
        [InlineKeyboardButton("🆓 Create a FREE Binance account", url="https://accounts.binance.com/en/register?ref=1154159582")],
        [InlineKeyboardButton("📱 Download Binance", url="https://www.binance.com/en/download")],
        [InlineKeyboardButton("⏩ Skip to License Activation", callback_data="skip_to_license")],
        [InlineKeyboardButton("📞 Contact support", url="http://wa.me/6589691668")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_license_keyboard():
    keyboard = [
        [InlineKeyboardButton("⏩ Skip to Activate Binance Futures", callback_data="skip_to_futures")],
        [InlineKeyboardButton("📝 Register BitAI", url="https://app.bitai.com.sg/h5/#/pages/sign/sign?invite=888")],
        [InlineKeyboardButton("📱 Download BitAI", url="https://fir.bitai.app/app.html")],
        [InlineKeyboardButton("📞 Contact support", url="http://wa.me/6589691668")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_futures_keyboard():
    keyboard = [
        [InlineKeyboardButton("⏩ Skip to setting API Keys", callback_data="skip_to_api")],
        [InlineKeyboardButton("◀️ Back to License Activation", callback_data="back_to_license")],
        [InlineKeyboardButton("📞 Contact support", url="http://wa.me/6589691668")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_api_keyboard():
    keyboard = [
        [InlineKeyboardButton("⏩ Skip to Transferring USDT", callback_data="skip_to_transfer")],
        [InlineKeyboardButton("◀️ Back to Activate Futures", callback_data="back_to_futures")],
        [InlineKeyboardButton("📞 Contact support", url="http://wa.me/6589691668")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_transfer_keyboard():
    keyboard = [
        [InlineKeyboardButton("⏩ Skip to Select Risk Profile", callback_data="skip_to_risk")],
        [InlineKeyboardButton("◀️ Back to Setting API Keys", callback_data="back_to_api")],
        [InlineKeyboardButton("📞 Contact support", url="http://wa.me/6589691668")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_risk_keyboard():
    keyboard = [
        [InlineKeyboardButton("◀️ Back to Transferring USDT", callback_data="back_to_transfer")],
        [InlineKeyboardButton("❓ FAQ", url="https://bitai.app/faq")],
        [InlineKeyboardButton("✉️ Email support", url="mailto:info@bitai.app")],
        [InlineKeyboardButton("📞 Contact support", url="http://wa.me/6589691668")],
        [InlineKeyboardButton("✅ Complete Setup", callback_data="complete_setup")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_completed_keyboard():
    keyboard = [
        [InlineKeyboardButton("🏠 Restart Setup", callback_data="restart")],
        [InlineKeyboardButton("📞 Contact support", url="http://wa.me/6589691668")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============= MESSAGE HANDLERS =============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_state = get_user_state(user_id)
    
    if current_state == STATE_COMPLETED:
        await update.message.reply_text(
            "✅ You've already completed the BitAI setup!\n\n"
            "BitAI is now analyzing market data and executing trades for you.\n\n"
            "What would you like to do?",
            reply_markup=get_completed_keyboard()
        )
    else:
        await entry_message(update, context, is_new=True)

async def entry_message(update: Update, context: ContextTypes.DEFAULT_TYPE, is_new=True, user_id=None):
    if user_id:
        chat_id = user_id
    else:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
    
    update_user_state(user_id, STATE_ENTRY)
    
    message_text = (
        "🚀 *Welcome to BitAI by Affinity AI* 🚀\n\n"
        "Most crypto traders don't lose because they lack knowledge.\n"
        "They lose because manual trading is emotional, bot settings are messy, and execution comes too late.\n\n"
        "It's time to upgrade to BitAI - built to analyze real-time market data and execute your trades automatically, 24/7."
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=message_text,
        parse_mode="Markdown",
        reply_markup=get_entry_keyboard()
    )

async def message_1_binance(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None):
    if user_id:
        chat_id = user_id
    else:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
    
    update_user_state(user_id, STATE_WAITING_BINANCE)
    
    message_text = (
        "*Step 1/6: Prepare Your Binance Account*\n\n"
        "To start using BitAI, you need a Binance account with KYC verification completed.\n\n"
        "_Already have a verified Binance account?_\n"
        "You may skip this video and continue to BitAI License Activation."
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=message_text,
        parse_mode="Markdown",
        reply_markup=get_binance_keyboard()
    )

async def message_2_license(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None):
    if user_id:
        chat_id = user_id
    else:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
    
    update_user_state(user_id, STATE_LICENSE)
    
    message_text = (
        "*Step 2/6: BitAI License Activation*\n\n"
        "To unlock BitAI's full auto AI trading, activate your BitAI License inside your BitAI app.\n\n"
        "Once activated, you can proceed to activate & enable your Binance Futures."
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=message_text,
        parse_mode="Markdown",
        reply_markup=get_license_keyboard()
    )

async def message_3_futures(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None):
    if user_id:
        chat_id = user_id
    else:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
    
    update_user_state(user_id, STATE_FUTURES)
    
    message_text = (
        "*Step 3/6: Activate & Enable Binance Futures*\n\n"
        "Before BitAI can execute, you need to activate Binance Futures inside your Binance account.\n\n"
        "Once Futures is enabled, you can continue to the next step and create your Binance API connection."
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=message_text,
        parse_mode="Markdown",
        reply_markup=get_futures_keyboard()
    )

async def message_4_api(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None):
    if user_id:
        chat_id = user_id
    else:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
    
    update_user_state(user_id, STATE_API)
    
    message_text = (
        "*Step 4/6: Set Up Your API Keys*\n\n"
        "Next, create your Binance API Keys and connect them to your BitAI account.\n\n"
        "This allows BitAI to analyze real-time market data and execute based on your selected risk profile.\n\n"
        "⚠️ *Make sure your API Keys are kept private and only connected inside the official BitAI platform.*"
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=message_text,
        parse_mode="Markdown",
        reply_markup=get_api_keyboard()
    )

async def message_5_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None):
    if user_id:
        chat_id = user_id
    else:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
    
    update_user_state(user_id, STATE_TRANSFER)
    
    message_text = (
        "*Step 5/6: Transfer USDT to Binance Futures*\n\n"
        "Before BitAI can execute, make sure your USDT is transferred into your own Binance Futures Wallet.\n\n"
        "This will be the capital used for BitAI's AI-driven execution based on your selected risk profile.\n\n"
        "Once completed, continue to Select Risk Profile."
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=message_text,
        parse_mode="Markdown",
        reply_markup=get_transfer_keyboard()
    )

async def message_6_risk(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None):
    if user_id:
        chat_id = user_id
    else:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
    
    update_user_state(user_id, STATE_RISK)
    
    message_text = (
        "*Step 6/6: Select Your Risk Profile*\n\n"
        "Choose your preferred BitAI Risk Profile based on your capital, goals, and risk appetite.\n\n"
        "BitAI will execute according to the risk level you select.\n\n"
        "✅ *Once done, BitAI will start to analyze real time market data and execute your trades automatically!*"
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=message_text,
        parse_mode="Markdown",
        reply_markup=get_risk_keyboard()
    )

async def complete_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    mark_user_completed(user_id)
    
    await query.edit_message_text(
        "🎉 *Congratulations! BitAI Setup Complete!* 🎉\n\n"
        "BitAI is now:\n"
        "✅ Analyzing real-time market data\n"
        "✅ Executing trades based on your risk profile\n"
        "✅ Working 24/7 automatically\n\n"
        "Your AI trading journey has begun!\n\n"
        "Need help? Contact support anytime.",
        parse_mode="Markdown",
        reply_markup=get_completed_keyboard()
    )

# ============= CALLBACK HANDLERS =============
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "setup_video":
        await query.edit_message_text(
            "📹 *BitAI Setup Video*\n\n"
            "Watch this video to complete your setup:\n"
            "[Video Link Placeholder]\n\n"
            "After watching, press any button to continue.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Next: Binance Setup", callback_data="next_to_binance")],
                [InlineKeyboardButton("📞 Contact support", url="http://wa.me/6589691668")]
            ])
        )
    
    elif data == "next_to_binance":
        await message_1_binance(update, context, user_id)
        await query.delete_message()
    
    elif data == "skip_to_license":
        await message_2_license(update, context, user_id)
        await query.delete_message()
    
    elif data == "skip_to_futures":
        await message_3_futures(update, context, user_id)
        await query.delete_message()
    
    elif data == "skip_to_api":
        await message_4_api(update, context, user_id)
        await query.delete_message()
    
    elif data == "skip_to_transfer":
        await message_5_transfer(update, context, user_id)
        await query.delete_message()
    
    elif data == "skip_to_risk":
        await message_6_risk(update, context, user_id)
        await query.delete_message()
    
    elif data == "back_to_license":
        await message_2_license(update, context, user_id)
        await query.delete_message()
    
    elif data == "back_to_futures":
        await message_3_futures(update, context, user_id)
        await query.delete_message()
    
    elif data == "back_to_api":
        await message_4_api(update, context, user_id)
        await query.delete_message()
    
    elif data == "back_to_transfer":
        await message_5_transfer(update, context, user_id)
        await query.delete_message()
    
    elif data == "complete_setup":
        await complete_setup(update, context)
    
    elif data == "restart":
        await entry_message(update, context, is_new=True, user_id=user_id)
        await query.delete_message()

# ============= REMINDER SYSTEM =============
async def send_reminder(context: ContextTypes.DEFAULT_TYPE, user_id, current_state):
    reminder_messages = {
        STATE_ENTRY: "⏰ Reminder: You haven't started your BitAI setup yet! Check your Binance account and continue with step 1.",
        STATE_WAITING_BINANCE: "⏰ Reminder: Step 1/6 - You need to prepare your Binance account to continue with BitAI setup.",
        STATE_LICENSE: "⏰ Reminder: Step 2/6 - Don't forget to activate your BitAI License!",
        STATE_FUTURES: "⏰ Reminder: Step 3/6 - Activate Binance Futures to proceed with BitAI setup.",
        STATE_API: "⏰ Reminder: Step 4/6 - Set up your API Keys to connect Binance with BitAI.",
        STATE_TRANSFER: "⏰ Reminder: Step 5/6 - Transfer USDT to your Binance Futures Wallet.",
        STATE_RISK: "⏰ Reminder: Step 6/6 - Select your risk profile to complete setup!",
    }
    
    message = reminder_messages.get(current_state, "⏰ Reminder: Complete your BitAI setup to start automated trading!")
    
    await context.bot.send_message(
        chat_id=int(user_id),
        text=f"{message}\n\nType /start to continue where you left off.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Continue Setup", callback_data="restart")],
            [InlineKeyboardButton("📞 Contact support", url="http://wa.me/6589691668")]
        ])
    )
    
    # Mark reminder as sent
    if str(user_id) in user_data:
        user_data[str(user_id)]["reminder_sent"] = True
        user_data[str(user_id)]["last_reminder"] = datetime.now().isoformat()
        save_user_data(user_data)

async def reminder_loop(context: ContextTypes.DEFAULT_TYPE):
    """Check every hour for users who need reminders"""
    incomplete_users = get_incomplete_users()
    
    for user_id_str, user_info in incomplete_users:
        current_state = user_info.get("state", STATE_ENTRY)
        await send_reminder(context, user_id_str, current_state)
        
        # Reset reminder tracking for next check
        user_data[user_id_str]["reminder_sent"] = True
        save_user_data(user_data)

# ============= MAIN BOT SETUP =============
async def post_init(application: Application):
    """Start reminder loop after bot initializes"""
    application.job_queue.run_repeating(reminder_loop, interval=3600, first=10)  # Check every hour

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # Run bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)

# ============= FLASK FOR RENDER =============
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Bot is running!"

def run_flask():
    flask_app.run(host='0.0.0.0', port=PORT)

def run_bot():
    main()

if __name__ == "__main__":
    # Run Flask in a separate thread for Render's health checks
    thread = threading.Thread(target=run_flask)
    thread.start()
    run_bot()
