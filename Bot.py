import os
import asyncio
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask
import threading

# ============= CONFIG =============
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
PORT = int(os.environ.get("PORT", 10000))
USER_DATA_FILE = "user_data.json"

# Channel to check (replace with your channel username)
REQUIRED_CHANNEL = os.environ.get("REQUIRED_CHANNEL", "@BitAI_Official")  # Change this!

# ============= DATA MANAGEMENT =============
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

user_data = load_user_data()

def get_user_step(user_id):
    uid = str(user_id)
    if uid not in user_data:
        user_data[uid] = {
            "step": 0,  # 0 = not started, 1-6 = current step, 7 = completed
            "step1_verified": False,
            "step2_verified": False,
            "step3_verified": False,
            "step4_verified": False,
            "step5_verified": False,
            "step6_verified": False,
            "channel_joined": False,
            "last_reminder": None,
            "reminder_count": 0,
            "joined_at": None
        }
        save_user_data(user_data)
    return user_data[uid]

def verify_step(user_id, step_num):
    uid = str(user_id)
    if uid in user_data:
        user_data[uid][f"step{step_num}_verified"] = True
        user_data[uid]["step"] = step_num + 1 if step_num < 6 else 7
        user_data[uid]["last_action"] = datetime.now().isoformat()
        user_data[uid]["reminder_count"] = 0
        save_user_data(user_data)
        return True
    return False

def is_step_verified(user_id, step_num):
    uid = str(user_id)
    return user_data.get(uid, {}).get(f"step{step_num}_verified", False)

def mark_channel_joined(user_id):
    uid = str(user_id)
    if uid in user_data:
        user_data[uid]["channel_joined"] = True
        user_data[uid]["joined_at"] = datetime.now().isoformat()
        save_user_data(user_data)
        return True
    return False

def is_channel_joined(user_id):
    uid = str(user_id)
    return user_data.get(uid, {}).get("channel_joined", False)

def get_incomplete_users():
    """Get users who haven't completed all steps and need reminders"""
    incomplete = []
    now = datetime.now()
    for uid, data in user_data.items():
        step = data.get("step", 0)
        if step < 7:  # Not completed
            last_action = data.get("last_action")
            if last_action:
                last_time = datetime.fromisoformat(last_action)
                hours_inactive = (now - last_time).total_seconds() / 3600
                if hours_inactive >= 6:
                    last_reminder = data.get("last_reminder")
                    if not last_reminder or (now - datetime.fromisoformat(last_reminder)).total_seconds() / 3600 >= 6:
                        incomplete.append((uid, data))
    return incomplete

# ============= STEP DEFINITIONS =============
STEPS = {
    1: {
        "title": "Join Our Official Channel",
        "emoji": "📢",
        "description": "Stay updated with latest news, signals, and updates!",
        "instruction": "Click the button below to join our official Telegram channel.\n\nAfter joining, click '✅ I Have Joined' to verify.",
        "action_buttons": [
            [InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")]
        ],
        "verification_type": "channel_join"
    },
    2: {
        "title": "Register BitAI Account",
        "emoji": "📝",
        "description": "Create your free BitAI trading account",
        "instruction": "Click below to register your BitAI account.\n\nComplete the registration form and verify your email.\n\nAfter registration, click '✅ I Have Registered'.",
        "action_buttons": [
            [InlineKeyboardButton("🚀 REGISTER NOW", url="https://app.bitai.com.sg/h5/#/pages/sign/sign?invite=888")]
        ],
        "verification_type": "button"
    },
    3: {
        "title": "Download BitAI App",
        "emoji": "📱",
        "description": "Get the BitAI app on your device",
        "instruction": "Download and install the BitAI app on your iOS or Android device.\n\nOpen the app and login with your registered account.\n\nAfter installing, click '✅ I Have Installed'.",
        "action_buttons": [
            [InlineKeyboardButton("📱 DOWNLOAD iOS", url="https://fir.bitai.app/app.html")],
            [InlineKeyboardButton("🤖 DOWNLOAD Android", url="https://fir.bitai.app/app.html")]
        ],
        "verification_type": "button"
    },
    4: {
        "title": "Create Binance Account",
        "emoji": "🏦",
        "description": "Set up your Binance trading account",
        "instruction": "Create a Binance account if you don't have one.\n\nComplete KYC verification (Level 2 required).\n\nEnable 2FA security.\n\nAfter completing, click '✅ I Have Created Binance'.",
        "action_buttons": [
            [InlineKeyboardButton("🆓 CREATE BINANCE", url="https://accounts.binance.com/en/register?ref=1154159582")],
            [InlineKeyboardButton("📱 DOWNLOAD BINANCE", url="https://www.binance.com/en/download")]
        ],
        "verification_type": "button"
    },
    5: {
        "title": "Connect API & Transfer Funds",
        "emoji": "🔗",
        "description": "Link Binance to BitAI",
        "instruction": "1. Create API keys in Binance (Enable Futures & Read only)\n"
                       "2. Connect API keys to BitAI app\n"
                       "3. Transfer USDT to Binance Futures Wallet (min 50 USDT)\n\n"
                       "After completing, click '✅ I Have Connected & Funded'.",
        "action_buttons": [],
        "verification_type": "button"
    },
    6: {
        "title": "Select Risk Profile & Activate",
        "emoji": "⚡",
        "description": "Start automated trading",
        "instruction": "1. Open BitAI app\n"
                       "2. Select your risk profile:\n"
                       "   🟢 Conservative (Low Risk)\n"
                       "   🟡 Moderate (Medium Risk)\n"
                       "   🔴 Aggressive (High Risk)\n"
                       "3. Click 'Start Trading'\n\n"
                       "After activation, click '✅ I Have Activated' to complete setup!",
        "action_buttons": [],
        "verification_type": "button"
    }
}

# ============= KEYBOARDS =============
def get_step_keyboard(step_num, user_id):
    """Create keyboard for the current step"""
    step = STEPS[step_num]
    keyboard = step["action_buttons"].copy()
    
    # Add verification button based on step type
    if step_num == 1:
        keyboard.append([InlineKeyboardButton("✅ I HAVE JOINED", callback_data=f"verify_channel_join")])
    else:
        keyboard.append([InlineKeyboardButton("✅ I HAVE COMPLETED THIS STEP", callback_data=f"verify_step_{step_num}")])
    
    keyboard.append([InlineKeyboardButton("❓ Need Help?", callback_data=f"help_step_{step_num}")])
    keyboard.append([InlineKeyboardButton("📞 Contact Support", url="http://wa.me/6589691668")])
    
    return InlineKeyboardMarkup(keyboard)

def get_welcome_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 START SETUP", callback_data="start_setup")],
        [InlineKeyboardButton("📞 Contact Support", url="http://wa.me/6589691668")]
    ])

def get_completed_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 VIEW STATUS", callback_data="view_status")],
        [InlineKeyboardButton("📞 Support", url="http://wa.me/6589691668")]
    ])

def get_admin_keyboard():
    """Admin panel with pending verifications"""
    pending = []
    for uid, data in user_data.items():
        step = data.get("step", 0)
        if step < 7 and step > 0:
            # Check which step needs verification
            for s in range(1, 7):
                if not data.get(f"step{s}_verified", False) and s == step:
                    pending.append((uid, s))
                    break
    
    if not pending:
        return InlineKeyboardMarkup([[InlineKeyboardButton("📋 No Pending", callback_data="no_action")]])
    
    buttons = []
    for uid, step_num in pending:
        # Try to get username (we don't store it, so just show ID)
        buttons.append([InlineKeyboardButton(
            f"👤 User {uid[-6:]} - Step {step_num}: {STEPS[step_num]['title'][:20]}", 
            callback_data=f"admin_verify_{uid}_{step_num}"
        )])
    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="admin_menu")])
    return InlineKeyboardMarkup(buttons)

def get_admin_verify_keyboard(user_id, step_num):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user_id}_{step_num}")],
        [InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{user_id}_{step_num}")],
        [InlineKeyboardButton("💬 Contact User", url=f"tg://user?id={user_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_menu")]
    ])

def get_progress_bar(user_id):
    """Visual progress bar"""
    data = get_user_step(user_id)
    completed = []
    for i in range(1, 7):
        if data.get(f"step{i}_verified", False):
            completed.append(i)
    
    bar = ""
    for i in range(1, 7):
        if i in completed:
            bar += "✅"
        elif i == data.get("step", 1):
            bar += "▶️"
        else:
            bar += "⬜"
        if i < 6:
            bar += "→"
    
    return bar, len(completed)

# ============= MESSAGE HANDLERS =============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    
    data = get_user_step(user_id)
    step = data.get("step", 0)
    
    # Check if all steps completed
    all_completed = all(data.get(f"step{i}_verified", False) for i in range(1, 7))
    
    if all_completed or step == 7:
        await update.message.reply_text(
            f"🎉 *CONGRATULATIONS {username}!* 🎉\n\n"
            f"✅ Your BitAI setup is COMPLETE!\n"
            f"🤖 BitAI is now actively trading for you 24/7\n\n"
            f"*Your Stats:*\n"
            f"• Account: Active 🟢\n"
            f"• Trading: Automated 🤖\n"
            f"• Status: Live 24/7\n\n"
            f"Need help? Contact support anytime.",
            parse_mode="Markdown",
            reply_markup=get_completed_keyboard()
        )
    elif step == 0:
        # New user
        await update.message.reply_text(
            f"🚀 *WELCOME TO BITAI {username}!* 🚀\n\n"
            f"*What is BitAI?*\n"
            f"BitAI is an automated crypto trading bot that:\n"
            f"• Analyzes real-time market data 📊\n"
            f"• Executes trades automatically 🤖\n"
            f"• Works 24/7 without emotions ⚡\n\n"
            f"*Setup Required:* Complete 6 simple steps\n"
            f"*Time needed:* ~10-15 minutes\n\n"
            f"Ready to start your AI trading journey?\n\n"
            f"⚠️ *Note:* Each step must be verified before moving forward.",
            parse_mode="Markdown",
            reply_markup=get_welcome_keyboard()
        )
    else:
        # User in progress - show current step
        current_step = step
        await show_step(update, context, current_step, user_id)

async def show_step(update: Update, context: ContextTypes.DEFAULT_TYPE, step_num, user_id=None, edit_mode=False):
    if not user_id:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
    else:
        chat_id = user_id
    
    step = STEPS[step_num]
    progress_bar, completed_count = get_progress_bar(user_id)
    
    message = (
        f"{step['emoji']} *STEP {step_num}/6: {step['title']}* {step['emoji']}\n\n"
        f"*Progress:* {progress_bar}\n"
        f"✅ *Completed:* {completed_count}/6 steps\n\n"
        f"*📌 Task:*\n{step['instruction']}\n\n"
        f"*⚠️ Important:*\n"
        f"• Complete this step fully\n"
        f"• Click the verification button when done\n"
        f"• Admin will approve before next step\n\n"
        f"*Need help?* Click 'Need Help' below."
    )
    
    if edit_mode and update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=get_step_keyboard(step_num, user_id)
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown",
            reply_markup=get_step_keyboard(step_num, user_id)
        )

async def verify_channel_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify if user joined the channel"""
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    
    await query.answer("Checking channel membership...")
    
    try:
        # Check if user is a member of the channel
        chat_member = await context.bot.get_chat_member(chat_id=f"@{REQUIRED_CHANNEL.replace('@', '')}", user_id=user_id)
        
        if chat_member.status in ['member', 'administrator', 'creator']:
            # User joined
            mark_channel_joined(user_id)
            verify_step(user_id, 1)
            
            await query.edit_message_text(
                f"✅ *VERIFIED!* ✅\n\n"
                f"Great job @{username}! You have successfully joined our channel.\n\n"
                f"Step 1 is complete! Moving you to Step 2...",
                parse_mode="Markdown"
            )
            
            # Show step 2 after delay
            await asyncio.sleep(1)
            await show_step(update, context, 2, user_id)
        else:
            # User didn't join
            await query.edit_message_text(
                f"❌ *NOT VERIFIED* ❌\n\n"
                f"@{username}, you haven't joined our official channel yet.\n\n"
                f"Please click the 'JOIN CHANNEL' button below and join first.\n\n"
                f"After joining, click '✅ I HAVE JOINED' again to verify.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")],
                    [InlineKeyboardButton("✅ I HAVE JOINED", callback_data="verify_channel_join")],
                    [InlineKeyboardButton("📞 Support", url="http://wa.me/6589691668")]
                ])
            )
    except Exception as e:
        print(f"Error checking membership: {e}")
        await query.edit_message_text(
            f"⚠️ *Could not verify* ⚠️\n\n"
            f"Please make sure you:\n"
            f"1. Click the JOIN CHANNEL button\n"
            f"2. Join the channel\n"
            f"3. Then click '✅ I HAVE JOINED' again\n\n"
            f"Still having issues? Contact support.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")],
                [InlineKeyboardButton("✅ TRY AGAIN", callback_data="verify_channel_join")],
                [InlineKeyboardButton("📞 Support", url="http://wa.me/6589691668")]
            ])
        )

async def submit_step(update: Update, context: ContextTypes.DEFAULT_TYPE, step_num):
    """User submits a step for verification"""
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    
    # Check if step already verified
    if is_step_verified(user_id, step_num):
        await query.answer("This step is already completed!", show_alert=True)
        return
    
    await query.answer("Submitting for verification...")
    
    # Store pending verification (in memory for admin)
    if not hasattr(context.bot_data, 'pending_verifications'):
        context.bot_data['pending_verifications'] = {}
    
    context.bot_data['pending_verifications'][str(user_id)] = {
        "step": step_num,
        "username": username,
        "submitted_at": datetime.now().isoformat()
    }
    
    await query.edit_message_text(
        f"⏳ *STEP {step_num} SUBMITTED FOR VERIFICATION* ⏳\n\n"
        f"@{username}, your submission has been sent to admin.\n\n"
        f"*What happens next?*\n"
        f"• Admin will review your submission\n"
        f"• You'll receive notification once approved/rejected\n"
        f"• After approval, you'll move to Step {step_num + 1}\n\n"
        f"⏰ Estimated wait time: Few minutes\n\n"
        f"Thank you for your patience! 🙏",
        parse_mode="Markdown"
    )
    
    # Notify admin
    if ADMIN_ID:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 *NEW SUBMISSION* 🔔\n\n"
                 f"👤 User: @{username}\n"
                 f"🆔 ID: `{user_id}`\n"
                 f"📌 Step: {step_num}/6 - {STEPS[step_num]['title']}\n"
                 f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                 f"Use /admin to review and approve.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 GO TO ADMIN", callback_data="admin_menu")]
            ])
        )

async def handle_admin_approval(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, step_num, is_approved):
    query = update.callback_query
    await query.answer()
    
    if is_approved:
        # Verify the step
        verify_step(user_id, step_num)
        
        # Get user data
        user = get_user_step(user_id)
        next_step = step_num + 1 if step_num < 6 else 7
        
        # Notify user
        if next_step <= 6:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=f"✅ *STEP {step_num} APPROVED!* ✅\n\n"
                     f"Great work! Your submission for '{STEPS[step_num]['title']}' has been verified and approved.\n\n"
                     f"Moving you to Step {next_step}... 🚀",
                parse_mode="Markdown"
            )
            # Create a mock callback for showing next step
            class MockUpdate:
                def __init__(self, user_id):
                    self.effective_user = type('obj', (object,), {'id': user_id})()
                    self.callback_query = type('obj', (object,), {
                        'answer': lambda *a, **k: None,
                        'edit_message_text': lambda *a, **k: None
                    })()
            
            await show_step(update, context, next_step, user_id)
        else:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=f"🎉 *CONGRATULATIONS!* 🎉\n\n"
                     f"✅ ALL 6 STEPS COMPLETED & APPROVED!\n\n"
                     f"*Your BitAI is now ACTIVE!*\n\n"
                     f"🤖 BitAI is now:\n"
                     f"• Analyzing real-time market data\n"
                     f"• Executing trades automatically\n"
                     f"• Working 24/7 for you\n\n"
                     f"Welcome to automated crypto trading! 🚀",
                parse_mode="Markdown",
                reply_markup=get_completed_keyboard()
            )
        
        await query.edit_message_text(
            f"✅ *APPROVED*\n\n"
            f"User `{user_id}` has been approved for Step {step_num}.\n\n"
            f"They have been notified and moved to the next step.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_menu")]])
        )
    else:
        # Reject - notify user to retry
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"❌ *STEP {step_num} NEEDS REVISION* ❌\n\n"
                 f"Unfortunately, your submission for '{STEPS[step_num]['title']}' was not approved.\n\n"
                 f"*Reason:* Please review the instructions carefully and ensure you've completed all requirements.\n\n"
                 f"Please try again and click the verification button once done.\n\n"
                 f"Need help? Contact support: http://wa.me/6589691668",
            parse_mode="Markdown"
        )
        
        await query.edit_message_text(
            f"❌ *REJECTED*\n\n"
            f"User `{user_id}`'s submission for Step {step_num} has been rejected.\n\n"
            f"They have been notified to try again.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_menu")]])
        )
    
    # Remove from pending
    if hasattr(context.bot_data, 'pending_verifications'):
        context.bot_data['pending_verifications'].pop(str(user_id), None)

# ============= ADMIN HANDLERS =============
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Access denied. Admin only.")
        return
    
    # Collect pending submissions
    pending = []
    for uid, data in user_data.items():
        step = data.get("step", 0)
        if step > 0 and step < 7:
            step_num = step
            if not data.get(f"step{step_num}_verified", False):
                pending.append((uid, step_num))
    
    if not pending:
        await update.message.reply_text(
            "📋 *ADMIN PANEL*\n\nNo pending verifications at this time.\n\nAll caught up! ✅",
            parse_mode="Markdown"
        )
        return
    
    text = f"📋 *ADMIN PANEL - {len(pending)} Pending*\n\n"
    for uid, step_num in pending:
        text += f"• User `{uid[-8:]}` - Step {step_num}: {STEPS[step_num]['title']}\n"
    
    keyboard = []
    for uid, step_num in pending:
        keyboard.append([InlineKeyboardButton(
            f"Verify User {uid[-6:]} - Step {step_num}",
            callback_data=f"admin_verify_{uid}_{step_num}"
        )])
    keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="admin_menu")])
    
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_verify_view(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, step_num):
    query = update.callback_query
    await query.answer()
    
    text = (
        f"👤 *Verify User Submission*\n\n"
        f"🆔 User ID: `{user_id}`\n"
        f"📌 Step: {step_num}/6 - {STEPS[step_num]['title']}\n"
        f"📋 Task: {STEPS[step_num]['description']}\n\n"
        f"*Verification Checklist:*\n"
        f"• User claims to have completed this step\n"
        f"• Please verify if they actually did\n"
        f"• Contact user if needed\n\n"
        f"*Decision:*"
    )
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_admin_verify_keyboard(user_id, step_num)
    )

# ============= REMINDER SYSTEM =============
async def send_reminder(context: ContextTypes.DEFAULT_TYPE, user_id, user_info):
    current_step = user_info.get("step", 1)
    reminder_count = user_info.get("reminder_count", 0) + 1
    
    # Update reminder count
    user_info["reminder_count"] = reminder_count
    user_info["last_reminder"] = datetime.now().isoformat()
    save_user_data(user_data)
    
    if reminder_count == 1:
        message = (
            f"⏰ *Gentle Reminder* ⏰\n\n"
            f"We noticed you started setting up BitAI but haven't completed Step {current_step} yet.\n\n"
            f"*Remaining:* Complete '{STEPS[current_step]['title']}'\n\n"
            f"Type /start to continue where you left off.\n\n"
            f"Don't miss out on automated 24/7 trading! 🚀"
        )
    elif reminder_count == 2:
        message = (
            f"🔔 *Important Update* 🔔\n\n"
            f"It's been 12+ hours since your last activity.\n\n"
            f"*Step {current_step} pending:* {STEPS[current_step]['title']}\n\n"
            f"Complete your setup to start:\n"
            f"• Automated trading 🤖\n"
            f"• Real-time market analysis 📊\n"
            f"• 24/7 profit opportunities 💰\n\n"
            f"Click below to continue!"
        )
    else:
        message = (
            f"⚠️ *Final Reminder* ⚠️\n\n"
            f"This is your {reminder_count}rd reminder to complete BitAI setup.\n\n"
            f"*Pending Steps:*\n"
            f"• Step {current_step}: {STEPS[current_step]['title']}\n"
            f"• Plus {6 - current_step} more steps after\n\n"
            f"*Benefits you're missing:*\n"
            f"• AI-powered trading\n"
            f"• Eliminate emotions\n"
            f"• Never miss trades\n\n"
            f"Type /start NOW to complete setup!\n\n"
            f"Need help? Contact support: http://wa.me/6589691668"
        )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 CONTINUE SETUP", callback_data=f"resume_step_{current_step}")],
        [InlineKeyboardButton("📞 Contact Support", url="http://wa.me/6589691668")]
    ])
    
    await context.bot.send_message(
        chat_id=int(user_id),
        text=message,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def reminder_loop(context: ContextTypes.DEFAULT_TYPE):
    """Check for users needing reminders every hour"""
    now = datetime.now()
    
    for uid, data in user_data.items():
        step = data.get("step", 0)
        # Skip completed users
        if step == 7:
            continue
        
        # Skip if all steps verified
        all_verified = all(data.get(f"step{i}_verified", False) for i in range(1, 7))
        if all_verified:
            continue
        
        last_action = data.get("last_action")
        if not last_action:
            continue
        
        last_time = datetime.fromisoformat(last_action)
        hours_inactive = (now - last_time).total_seconds() / 3600
        
        # Check if 6+ hours inactive and no reminder in last 6 hours
        if hours_inactive >= 6:
            last_reminder = data.get("last_reminder")
            if not last_reminder:
                await send_reminder(context, uid, data)
            else:
                reminder_time = datetime.fromisoformat(last_reminder)
                if (now - reminder_time).total_seconds() / 3600 >= 6:
                    await send_reminder(context, uid, data)

# ============= CALLBACK HANDLER =============
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    
    await query.answer()
    
    # Start setup
    if data == "start_setup":
        get_user_step(user_id)  # Initialize
        await show_step(update, context, 1, user_id)
        await query.delete_message()
    
    # Verify channel join
    elif data == "verify_channel_join":
        await verify_channel_join(update, context)
    
    # Verify step (2-6)
    elif data.startswith("verify_step_"):
        step_num = int(data.replace("verify_step_", ""))
        # Check if previous steps are verified
        previous_steps_verified = all(is_step_verified(user_id, i) for i in range(1, step_num))
        if not previous_steps_verified and step_num > 1:
            await query.answer("Please complete previous steps first!", show_alert=True)
            return
        
        # Check if step 1 (channel) is verified
        if step_num > 1 and not is_channel_joined(user_id):
            await query.answer("You must join the channel first!", show_alert=True)
            return
        
        await submit_step(update, context, step_num)
    
    # Admin menu
    elif data == "admin_menu":
        if user_id == ADMIN_ID:
            pending = []
            for uid, udata in user_data.items():
                step = udata.get("step", 0)
                if 1 <= step < 7 and not udata.get(f"step{step}_verified", False):
                    pending.append((uid, step))
            
            if pending:
                text = f"📋 *Pending Verifications:* {len(pending)}\n\n"
                keyboard = []
                for uid, step_num in pending:
                    text += f"• User `{uid[-8:]}` - Step {step_num}\n"
                    keyboard.append([InlineKeyboardButton(
                        f"Verify {uid[-6:]} - Step {step_num}",
                        callback_data=f"admin_verify_{uid}_{step_num}"
                    )])
                keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="admin_menu")])
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await query.edit_message_text("📋 No pending verifications.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="admin_menu")]]))
        else:
            await query.answer("Unauthorized", show_alert=True)
    
    # Admin verify view
    elif data.startswith("admin_verify_"):
        if user_id == ADMIN_ID:
            parts = data.replace("admin_verify_", "").split("_")
            target_user = parts[0]
            step_num = int(parts[1])
            await admin_verify_view(update, context, target_user, step_num)
    
    # Approve
    elif data.startswith("approve_"):
        if user_id == ADMIN_ID:
            parts = data.replace("approve_", "").split("_")
            target_user = parts[0]
            step_num = int(parts[1])
            await handle_admin_approval(update, context, target_user, step_num, True)
    
    # Reject
    elif data.startswith("reject_"):
        if user_id == ADMIN_ID:
            parts = data.replace("reject_", "").split("_")
            target_user = parts[0]
            step_num = int(parts[1])
            await handle_admin_approval(update, context, target_user, step_num, False)
    
    # Resume step
    elif data.startswith("resume_step_"):
        step_num = int(data.replace("resume_step_", ""))
        await show_step(update, context, step_num, user_id, True)
    
    # View status
    elif data == "view_status":
        data = get_user_step(user_id)
        all_completed = all(data.get(f"step{i}_verified", False) for i in range(1, 7))
        if all_completed:
            await query.edit_message_text(
                "✅ *BitAI Status: ACTIVE*\n\nYour bot is trading 24/7! 🚀",
                parse_mode="Markdown",
                reply_markup=get_completed_keyboard()
            )
        else:
            progress_bar, completed = get_progress_bar(user_id)
            await query.edit_message_text(
                f"📊 *Your Progress*\n\n{progress_bar}\n\n✅ {completed}/6 steps completed\n\nType /start to continue.",
                parse_mode="Markdown"
            )
    
    # Need help
    elif data.startswith("help_step_"):
        step_num = int(data.replace("help_step_", ""))
        step = STEPS[step_num]
        help_text = (
            f"❓ *Help for Step {step_num}: {step['title']}*\n\n"
            f"*Common Issues:*\n\n"
            f"**Can't join channel?**\n"
            f"• Click the JOIN CHANNEL button\n"
            f"• Telegram will open the channel\n"
            f"• Click 'Join'\n"
            f"• Return to bot and click verification\n\n"
            f"**Registration issues?**\n"
            f"• Check your email for verification\n"
            f"• Use a valid email address\n"
            f"• Check spam folder\n\n"
            f"**Still stuck?** Contact support: http://wa.me/6589691668"
        )
        await query.edit_message_text(
            help_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Step", callback_data=f"resume_step_{step_num}")],
                [InlineKeyboardButton("📞 Contact Support", url="http://wa.me/6589691668")]
            ])
        )
    
    elif data == "no_action":
        await query.answer()
    
    else:
        await query.answer()

# ============= MAIN =============
async def post_init(application: Application):
    """Start reminder loop"""
    application.job_queue.run_repeating(reminder_loop, interval=3600, first=10)

def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN environment variable not set!")
        return
    
    if ADMIN_ID == 0:
        print("WARNING: ADMIN_ID not set. Please add ADMIN_ID environment variable.")
    
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("✅ BitAI Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

# Flask for Render
flask_app = Flask(__name__)

@flask_app.route('/')
def health():
    return "🤖 BitAI Bot is running!", 200

if __name__ == "__main__":
    thread = threading.Thread(target=lambda: flask_app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False))
    thread.start()
    main()
