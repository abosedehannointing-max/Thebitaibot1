import logging
import os
import asyncio
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Get bot token from environment variable
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables")

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Video URLs - Catbox direct links (ALL WORKING)
WELCOME_VIDEO = "https://files.catbox.moe/b2unen.mp4"
VIDEO_1 = "https://files.catbox.moe/u392du.mp4"
VIDEO_2 = "https://files.catbox.moe/wn3azc.mp4"
VIDEO_3 = "https://files.catbox.moe/tb0jm3.mp4"
VIDEO_4 = "https://files.catbox.moe/tb0jm3.mp4"  # Same as step 3
VIDEO_5 = "https://files.catbox.moe/0z82y0.mp4"
VIDEO_6 = "https://files.catbox.moe/eowij6.mp4"

# Message texts
WELCOME_TEXT = """🚀 *Welcome to BitAI by Affinity AI*

Most crypto traders don't lose because they lack knowledge.
They lose because manual trading is emotional, bot settings are messy, and execution comes too late.

It's time to upgrade to BitAI - built to analyze real-time market data and execute your trades automatically, 24/7."""

STEP1_TEXT = """📌 *Step 1/6: Prepare Your Binance Account*

To start using BitAI, you need a Binance account with KYC verification completed.

✅ *Already have a verified Binance account?*
You may skip this step and continue to BitAI License Activation."""

STEP2_TEXT = """📌 *Step 2/6: BitAI License Activation*

To unlock BitAI's full auto AI trading, activate your BitAI License inside your BitAI app.

Once activated, you can proceed to activate & enable your Binance Futures."""

STEP3_TEXT = """📌 *Step 3/6: Activate & Enable Binance Futures*

Before BitAI can execute, you need to activate Binance Futures inside your Binance account.

Once Futures is enabled, you can continue to the next step and create your Binance API connection."""

STEP4_TEXT = """📌 *Step 4/6: Set Up Your API Keys*

Next, create your Binance API Keys and connect them to your BitAI account.

This allows BitAI to analyze real-time market data and execute based on your selected risk profile.

⚠️ *Make sure your API Keys are kept private and only connected inside the official BitAI platform.*"""

STEP5_TEXT = """📌 *Step 5/6: Transfer USDT to Binance Futures*

Before BitAI can execute, make sure your USDT is transferred into your own Binance Futures Wallet.

This will be the capital used for BitAI's AI-driven execution based on your selected risk profile.

Once completed, continue to Select Risk Profile."""

STEP6_TEXT = """📌 *Step 6/6: Select Your Risk Profile*

Choose your preferred BitAI Risk Profile based on your capital, goals, and risk appetite.

BitAI will execute according to the risk level you select.

Once done, BitAI will start to analyze real time market data and execute your trades automatically! 🎉"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - sends welcome video and message"""
    user_id = update.effective_user.id
    context.user_data['step'] = 0
    
    keyboard = [
        [InlineKeyboardButton("📝 Register FREE BitAI", url="https://app.bitai.com.sg/h5/#/pages/sign/sign?invite=888")],
        [InlineKeyboardButton("📱 Download BitAI", url="https://fir.bitai.app/app.html")],
        [InlineKeyboardButton("▶️ Start Setup", callback_data="next_step")],
        [InlineKeyboardButton("🆘 Contact Support", url="http://wa.me/6589691668")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await update.message.reply_video(
            video=WELCOME_VIDEO,
            caption=WELCOME_TEXT,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to send video: {e}")
        await update.message.reply_text(WELCOME_TEXT, reply_markup=reply_markup, parse_mode='Markdown')

async def show_step1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔗 Create Binance Account", url="https://accounts.binance.com/en/register?ref=1154159582")],
        [InlineKeyboardButton("📱 Download Binance App", url="https://www.binance.com/en/download")],
        [InlineKeyboardButton("✅ Done - I completed Step 1", callback_data="step1_done")],
        [InlineKeyboardButton("⏩ Skip to Step 2", callback_data="step1_skip")],
        [InlineKeyboardButton("🆘 Contact Support", url="http://wa.me/6589691668")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if update.callback_query:
            await update.callback_query.delete_message()
            await update.callback_query.message.chat.send_video(
                video=VIDEO_1,
                caption=STEP1_TEXT,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_video(
                video=VIDEO_1,
                caption=STEP1_TEXT,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Failed to send video: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text(STEP1_TEXT, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(STEP1_TEXT, reply_markup=reply_markup, parse_mode='Markdown')

async def step1_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ *Great! Step 1 completed!*\n\nMoving to Step 2...", parse_mode='Markdown')
    await asyncio.sleep(1)
    await show_step2(update, context)

async def step1_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏩ *Step 1 skipped*\n\nMoving to Step 2...", parse_mode='Markdown')
    await asyncio.sleep(1)
    await show_step2(update, context)

async def show_step2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Register BitAI", url="https://app.bitai.com.sg/h5/#/pages/sign/sign?invite=888")],
        [InlineKeyboardButton("📱 Download BitAI App", url="https://fir.bitai.app/app.html")],
        [InlineKeyboardButton("✅ Done - I completed Step 2", callback_data="step2_done")],
        [InlineKeyboardButton("⏩ Skip to Step 3", callback_data="step2_skip")],
        [InlineKeyboardButton("◀️ Back to Step 1", callback_data="step1_back")],
        [InlineKeyboardButton("🆘 Contact Support", url="http://wa.me/6589691668")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if update.callback_query:
            await update.callback_query.delete_message()
            await update.callback_query.message.chat.send_video(
                video=VIDEO_2,
                caption=STEP2_TEXT,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_video(
                video=VIDEO_2,
                caption=STEP2_TEXT,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Failed to send video: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text(STEP2_TEXT, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(STEP2_TEXT, reply_markup=reply_markup, parse_mode='Markdown')

async def step2_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ *Great! Step 2 completed!*\n\nMoving to Step 3...", parse_mode='Markdown')
    await asyncio.sleep(1)
    await show_step3(update, context)

async def step2_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏩ *Step 2 skipped*\n\nMoving to Step 3...", parse_mode='Markdown')
    await asyncio.sleep(1)
    await show_step3(update, context)

async def show_step3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Done - I enabled Futures", callback_data="step3_done")],
        [InlineKeyboardButton("⏩ Skip to Step 4", callback_data="step3_skip")],
        [InlineKeyboardButton("◀️ Back to Step 2", callback_data="step2_back")],
        [InlineKeyboardButton("🆘 Contact Support", url="http://wa.me/6589691668")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if update.callback_query:
            await update.callback_query.delete_message()
            await update.callback_query.message.chat.send_video(
                video=VIDEO_3,
                caption=STEP3_TEXT,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_video(
                video=VIDEO_3,
                caption=STEP3_TEXT,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Failed to send video: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text(STEP3_TEXT, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(STEP3_TEXT, reply_markup=reply_markup, parse_mode='Markdown')

async def step3_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ *Great! Step 3 completed!*\n\nMoving to Step 4...", parse_mode='Markdown')
    await asyncio.sleep(1)
    await show_step4(update, context)

async def step3_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏩ *Step 3 skipped*\n\nMoving to Step 4...", parse_mode='Markdown')
    await asyncio.sleep(1)
    await show_step4(update, context)

async def show_step4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Done - I set up API Keys", callback_data="step4_done")],
        [InlineKeyboardButton("⏩ Skip to Step 5", callback_data="step4_skip")],
        [InlineKeyboardButton("◀️ Back to Step 3", callback_data="step3_back")],
        [InlineKeyboardButton("🆘 Contact Support", url="http://wa.me/6589691668")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.callback_query:
            await update.callback_query.delete_message()
            await update.callback_query.message.chat.send_video(
                video=VIDEO_4,
                caption=STEP4_TEXT,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_video(
                video=VIDEO_4,
                caption=STEP4_TEXT,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Failed to send video: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text(STEP4_TEXT, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(STEP4_TEXT, reply_markup=reply_markup, parse_mode='Markdown')

async def step4_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ *Great! Step 4 completed!*\n\nMoving to Step 5...", parse_mode='Markdown')
    await asyncio.sleep(1)
    await show_step5(update, context)

async def step4_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏩ *Step 4 skipped*\n\nMoving to Step 5...", parse_mode='Markdown')
    await asyncio.sleep(1)
    await show_step5(update, context)

async def show_step5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Done - I transferred USDT", callback_data="step5_done")],
        [InlineKeyboardButton("⏩ Skip to Step 6", callback_data="step5_skip")],
        [InlineKeyboardButton("◀️ Back to Step 4", callback_data="step4_back")],
        [InlineKeyboardButton("🆘 Contact Support", url="http://wa.me/6589691668")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.callback_query:
            await update.callback_query.delete_message()
            await update.callback_query.message.chat.send_video(
                video=VIDEO_5,
                caption=STEP5_TEXT,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_video(
                video=VIDEO_5,
                caption=STEP5_TEXT,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Failed to send video: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text(STEP5_TEXT, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(STEP5_TEXT, reply_markup=reply_markup, parse_mode='Markdown')

async def step5_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ *Great! Step 5 completed!*\n\nMoving to final Step 6...", parse_mode='Markdown')
    await asyncio.sleep(1)
    await show_step6(update, context)

async def step5_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏩ *Step 5 skipped*\n\nMoving to final Step 6...", parse_mode='Markdown')
    await asyncio.sleep(1)
    await show_step6(update, context)

async def show_step6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Done - Setup Complete!", callback_data="step6_done")],
        [InlineKeyboardButton("◀️ Back to Step 5", callback_data="step5_back")],
        [InlineKeyboardButton("❓ FAQ", url="https://bitai.app/faq")],
        [InlineKeyboardButton("📧 Email Support", url="mailto:info@bitai.app")],
        [InlineKeyboardButton("🆘 Contact Support", url="http://wa.me/6589691668")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.callback_query:
            await update.callback_query.delete_message()
            await update.callback_query.message.chat.send_video(
                video=VIDEO_6,
                caption=STEP6_TEXT,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_video(
                video=VIDEO_6,
                caption=STEP6_TEXT,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Failed to send video: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text(STEP6_TEXT, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(STEP6_TEXT, reply_markup=reply_markup, parse_mode='Markdown')

async def step6_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    completion_msg = """🎉 *CONGRATULATIONS! Setup Complete!* 🎉

You've successfully completed all steps!

✨ *BitAI is now ready to:*
• 📊 Analyze real-time market data
• 🤖 Execute trades automatically
• 💎 Run 24/7

*Select your Risk Profile in the BitAI App to start trading!*

Need help? Contact our support team anytime.

Thank you for choosing BitAI! 🚀"""

    keyboard = [
        [InlineKeyboardButton("🆘 Contact Support", url="http://wa.me/6589691668")],
        [InlineKeyboardButton("🏠 Restart Setup", callback_data="restart")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(completion_msg, reply_markup=reply_markup, parse_mode='Markdown')

async def restart_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(update, context)

# Back navigation handlers
async def back_to_step1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_step1(update, context)

async def back_to_step2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_step2(update, context)

async def back_to_step3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_step3(update, context)

async def back_to_step4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_step4(update, context)

async def back_to_step5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_step5(update, context)

def main():
    """Start the bot"""
    # Delete any existing webhook
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1&timeout=1")
        logger.info("Cleared existing webhook and updates")
    except Exception as e:
        logger.warning(f"Could not clear webhook: {e}")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(show_step1, pattern="^next_step$"))
    application.add_handler(CallbackQueryHandler(step1_done, pattern="^step1_done$"))
    application.add_handler(CallbackQueryHandler(step1_skip, pattern="^step1_skip$"))
    application.add_handler(CallbackQueryHandler(back_to_step1, pattern="^step1_back$"))
    application.add_handler(CallbackQueryHandler(step2_done, pattern="^step2_done$"))
    application.add_handler(CallbackQueryHandler(step2_skip, pattern="^step2_skip$"))
    application.add_handler(CallbackQueryHandler(back_to_step2, pattern="^step2_back$"))
    application.add_handler(CallbackQueryHandler(step3_done, pattern="^step3_done$"))
    application.add_handler(CallbackQueryHandler(step3_skip, pattern="^step3_skip$"))
    application.add_handler(CallbackQueryHandler(back_to_step3, pattern="^step3_back$"))
    application.add_handler(CallbackQueryHandler(step4_done, pattern="^step4_done$"))
    application.add_handler(CallbackQueryHandler(step4_skip, pattern="^step4_skip$"))
    application.add_handler(CallbackQueryHandler(back_to_step4, pattern="^step4_back$"))
    application.add_handler(CallbackQueryHandler(step5_done, pattern="^step5_done$"))
    application.add_handler(CallbackQueryHandler(step5_skip, pattern="^step5_skip$"))
    application.add_handler(CallbackQueryHandler(back_to_step5, pattern="^step5_back$"))
    application.add_handler(CallbackQueryHandler(step6_done, pattern="^step6_done$"))
    application.add_handler(CallbackQueryHandler(restart_setup, pattern="^restart$"))
    
    logger.info("Bot is starting with Catbox videos...")
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        poll_interval=1.0,
        timeout=30
    )

if __name__ == "__main__":
    main()
