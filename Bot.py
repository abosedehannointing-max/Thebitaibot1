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
PENDING_FILE = "pending_approvals.json"

# User States
STATE_SETUP = "setup"
STATE_COMPLETED = "completed"

# ============= DATA MANAGEMENT =============
def load_json(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

user_data = load_json(USER_DATA_FILE)
pending_approvals = load_json(PENDING_FILE)

def get_user_progress(user_id):
    """Get user's completed steps"""
    uid = str(user_id)
    if uid not in user_data:
        user_data[uid] = {
            "completed_steps": [],
            "current_step": 1,
            "state": STATE_SETUP,
            "last_reminder": None,
            "reminder_count": 0
        }
        save_json(USER_DATA_FILE, user_data)
    return user_data[uid]

def update_user_step(user_id, step_num, is_completed=True):
    uid = str(user_id)
    if uid not in user_data:
        get_user_progress(user_id)
    
    if is_completed and step_num not in user_data[uid]["completed_steps"]:
        user_data[uid]["completed_steps"].append(step_num)
        user_data[uid]["completed_steps"].sort()
    
    # Determine next step
    completed = user_data[uid]["completed_steps"]
    if len(completed) == 6:
        user_data[uid]["state"] = STATE_COMPLETED
        user_data[uid]["current_step"] = 7  # Completed
    else:
        next_step = 1
        for i in range(1, 7):
            if i not in completed:
                next_step = i
                break
        user_data[uid]["current_step"] = next_step
    
    user_data[uid]["last_action"] = datetime.now().isoformat()
    user_data[uid]["reminder_count"] = 0
    save_json(USER_DATA_FILE, user_data)
    return user_data[uid]["current_step"]

def mark_step_pending(user_id, step_num):
    uid = str(user_id)
    pending_approvals[uid] = {
        "step": step_num,
        "user_id": user_id,
        "requested_at": datetime.now().isoformat(),
        "status": "pending"
    }
    save_json(PENDING_FILE, pending_approvals)

def approve_user_step(user_id):
    uid = str(user_id)
    if uid in pending_approvals:
        step_num = pending_approvals[uid]["step"]
        del pending_approvals[uid]
        save_json(PENDING_FILE, pending_approvals)
        return step_num
    return None

def get_pending_users():
    return {uid: data for uid, data in pending_approvals.items() if data.get("status") == "pending"}

def get_incomplete_steps(user_id):
    """Returns list of steps not yet completed"""
    progress = get_user_progress(user_id)
    all_steps = {1, 2, 3, 4, 5, 6}
    completed = set(progress.get("completed_steps", []))
    return list(all_steps - completed)

# ============= STEP DETAILS =============
STEP_DETAILS = {
    1: {
        "name": "Binance Account",
        "emoji": "🏦",
        "instruction": "Create and verify your Binance account (KYC Level 2 required)",
        "action_buttons": [
            [InlineKeyboardButton("🆓 Create Binance Account", url="https://accounts.binance.com/en/register?ref=1154159582")],
            [InlineKeyboardButton("📱 Download Binance App", url="https://www.binance.com/en/download")]
        ],
        "verification_note": "Make sure your account is fully verified with KYC Level 2"
    },
    2: {
        "name": "BitAI License",
        "emoji": "🔑",
        "instruction": "Activate your BitAI license inside the BitAI app",
        "action_buttons": [
            [InlineKeyboardButton("📝 Register BitAI", url="https://app.bitai.com.sg/h5/#/pages/sign/sign?invite=888")],
            [InlineKeyboardButton("📱 Download BitAI App", url="https://fir.bitai.app/app.html")]
        ],
        "verification_note": "You need a valid license key from BitAI"
    },
    3: {
        "name": "Binance Futures",
        "emoji": "📈",
        "instruction": "Activate Binance Futures trading on your account",
        "action_buttons": [],
        "verification_note": "Open Binance → Futures → Activate → Complete quiz"
    },
    4: {
        "name": "API Connection",
        "emoji": "🔌",
        "instruction": "Create API keys and connect to BitAI",
        "action_buttons": [],
        "verification_note": "API must have Futures and Read permissions only"
    },
    5: {
        "name": "USDT Transfer",
        "emoji": "💰",
        "instruction": "Transfer USDT to your Binance Futures Wallet",
        "action_buttons": [],
        "verification_note": "Minimum 50 USDT recommended"
    },
    6: {
        "name": "Risk Profile",
        "emoji": "⚡",
        "instruction": "Select your preferred risk level in BitAI",
        "action_buttons": [],
        "verification_note": "Choose: Conservative (🟢), Moderate (🟡), or Aggressive (🔴)"
    }
}

# ============= KEYBOARDS =============
def get_main_menu_keyboard(user_id):
    progress = get_user_progress(user_id)
    completed = progress.get("completed_steps", [])
    current_step = progress.get("current_step", 1)
    
    keyboard = []
    
    # Show progress bar
    progress_text = ""
    for i in range(1, 7):
        if i in completed:
            progress_text += "✅"
        elif i == current_step:
            progress_text += "▶️"
        else:
            progress_text += "⬜"
        if i < 6:
            progress_text += "→"
    
    # Show current step button
    keyboard.append([InlineKeyboardButton(f"📌 Continue: Step {current_step} - {STEP_DETAILS[current_step]['name']}", 
                                         callback_data=f"continue_step_{current_step}")])
    
    # Show all steps
    keyboard.append([InlineKeyboardButton("📋 View All Steps", callback_data="view_all_steps")])
    
    # Show completed steps
    if completed:
        completed_text = f"✅ Completed: {len(completed)}/6 steps"
        keyboard.append([InlineKeyboardButton(completed_text, callback_data="show_completed")])
    
    keyboard.append([InlineKeyboardButton("❓ Need Help?", callback_data="need_help")])
    keyboard.append([InlineKeyboardButton("📞 Contact Support", url="http://wa.me/6589691668")])
    
    return InlineKeyboardMarkup(keyboard), progress_text

def get_step_keyboard(step_num, user_id):
    step = STEP_DETAILS[step_num]
    keyboard = step["action_buttons"].copy()
    
    # Submit button
    keyboard.append([InlineKeyboardButton("✅ I have completed this step", callback_data=f"submit_step_{step_num}")])
    
    # Navigation buttons
    nav_buttons = []
    if step_num > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ Previous Step", callback_data=f"go_to_step_{step_num-1}"))
    if step_num < 6:
        nav_buttons.append(InlineKeyboardButton("Next Step ▶️", callback_data=f"go_to_step_{step_num+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Help and support
    keyboard.append([InlineKeyboardButton("❓ Step Help", callback_data=f"help_step_{step_num}")])
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    keyboard.append([InlineKeyboardButton("📞 Contact Support", url="http://wa.me/6589691668")])
    
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard():
    pending = get_pending_users()
    if not pending:
        return InlineKeyboardMarkup([[InlineKeyboardButton("📋 No Pending Approvals", callback_data="no_action")]])
    
    buttons = []
    for uid, data in pending.items():
        step = data['step']
        step_name = STEP_DETAILS[step]['name']
        buttons.append([InlineKeyboardButton(
            f"👤 User {uid[:8]}... - Step {step}: {step_name}", 
            callback_data=f"review_user_{uid}"
        )])
    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="admin_menu")])
    return InlineKeyboardMarkup(buttons)

def get_review_keyboard(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ APPROVE - Verified Correct", callback_data=f"approve_{user_id}")],
        [InlineKeyboardButton("❌ REJECT - Not Completed", callback_data=f"reject_{user_id}")],
        [InlineKeyboardButton("💬 Message User", url=f"tg://user?id={user_id}")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_menu")]
    ])

def get_completed_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 View My Progress", callback_data="view_progress")],
        [InlineKeyboardButton("📞 Support", url="http://wa.me/6589691668")],
        [InlineKeyboardButton("🔄 Restart Setup", callback_data="restart_setup")]
    ])

def get_progress_keyboard(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        [InlineKeyboardButton("📞 Contact Support", url="http://wa.me/6589691668")]
    ])

# ============= MESSAGE HANDLERS =============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    
    progress = get_user_progress(user_id)
    completed = len(progress.get("completed_steps", []))
    
    if completed == 6:
        await update.message.reply_text(
            f"🎉 *Welcome back, {username}!* 🎉\n\n"
            f"✅ Your BitAI setup is COMPLETE!\n"
            f"🤖 BitAI is actively trading for you 24/7\n\n"
            f"Use the buttons below to check your status or get support.",
            parse_mode="Markdown",
            reply_markup=get_completed_keyboard()
        )
    else:
        keyboard, progress_bar = get_main_menu_keyboard(user_id)
        await update.message.reply_text(
            f"🚀 *Welcome to BitAI Setup, {username}!* 🚀\n\n"
            f"*Your Progress:*\n"
            f"{progress_bar}\n"
            f"📊 *Completed:* {completed}/6 steps\n\n"
            f"✨ *Next Step:* Step {progress['current_step']} - {STEP_DETAILS[progress['current_step']]['name']}\n\n"
            f"Click below to continue your setup:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

async def show_step(update: Update, context: ContextTypes.DEFAULT_TYPE, step_num, user_id=None, edit_mode=False):
    if not user_id:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
    else:
        chat_id = user_id
    
    step = STEP_DETAILS[step_num]
    progress = get_user_progress(user_id)
    completed = progress.get("completed_steps", [])
    
    if step_num in completed:
        # Step already completed, show next incomplete step
        next_step = get_user_progress(user_id)["current_step"]
        if next_step <= 6:
            await show_step(update, context, next_step, user_id, edit_mode)
        return
    
    # Get progress bar
    progress_bar = ""
    for i in range(1, 7):
        if i in completed:
            progress_bar += "✅"
        elif i == step_num:
            progress_bar += "▶️"
        else:
            progress_bar += "⬜"
        if i < 6:
            progress_bar += "→"
    
    message = (
        f"{step['emoji']} *STEP {step_num}/6: {step['name']}* {step['emoji']}\n\n"
        f"*Progress:* {progress_bar}\n"
        f"📊 *Completed:* {len(completed)}/6 steps\n\n"
        f"*📌 Instructions:*\n{step['instruction']}\n\n"
        f"*⚠️ Important:*\n{step['verification_note']}\n\n"
        f"✅ *After completing this step*, click the 'I have completed this step' button below.\n"
        f"Admin will verify and approve your submission.\n\n"
        f"*🔒 Security Note:* Never share your API keys with anyone!"
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

async def submit_step(update: Update, context: ContextTypes.DEFAULT_TYPE, step_num):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    
    progress = get_user_progress(user_id)
    
    # Check if already completed
    if step_num in progress.get("completed_steps", []):
        await query.answer("This step is already completed!", show_alert=True)
        return
    
    await query.answer("Submitting for verification...")
    
    # Mark as pending approval
    mark_step_pending(user_id, step_num)
    
    # Notify user
    await query.edit_message_text(
        f"⏳ *Submission Received!* ⏳\n\n"
        f"Step {step_num}/6 - {STEP_DETAILS[step_num]['name']} has been submitted for verification.\n\n"
        f"*What happens next?*\n"
        f"1️⃣ Admin will review your submission\n"
        f"2️⃣ You'll receive notification when approved/rejected\n"
        f"3️⃣ Once approved, you can proceed to the next step\n\n"
        f"📝 *Submitted by:* @{username}\n"
        f"⏰ *Time:* {datetime.now().strftime('%I:%M %p')}\n\n"
        f"Thank you for your patience! 🙏",
        parse_mode="Markdown"
    )
    
    # Notify admin
    if ADMIN_ID and ADMIN_ID != 0:
        admin_text = (
            f"🔔 *NEW SUBMISSION READY FOR REVIEW* 🔔\n\n"
            f"👤 *User:* @{username}\n"
            f"🆔 *User ID:* `{user_id}`\n"
            f"📌 *Step:* {step_num}/6 - {STEP_DETAILS[step_num]['name']}\n"
            f"⏰ *Submitted:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Use /admin to review and approve this submission."
        )
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Go to Admin Panel", callback_data="admin_menu")]
            ])
        )

async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, is_approved):
    query = update.callback_query
    await query.answer()
    
    step_num = approve_user_step(user_id) if is_approved else None
    
    if is_approved and step_num:
        # Update user progress
        next_step = update_user_step(user_id, step_num, True)
        
        # Notify user
        if next_step <= 6:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=f"✅ *APPROVED!* ✅\n\n"
                     f"Great job! Step {step_num} - {STEP_DETAILS[step_num]['name']} has been verified and approved!\n\n"
                     f"Moving you to Step {next_step}...\n\n"
                     f"Click the button below to continue:",
                parse_mode="Markdown"
            )
            # Show next step
            await show_step(update, context, next_step, user_id)
        else:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=f"🎉 *CONGRATULATIONS!* 🎉\n\n"
                     f"✅ All 6 steps have been approved!\n"
                     f"✅ BitAI is now ACTIVE and trading for you!\n"
                     f"✅ Your account is fully configured for 24/7 automated trading\n\n"
                     f"Welcome to the future of crypto trading! 🚀",
                parse_mode="Markdown",
                reply_markup=get_completed_keyboard()
            )
        
        await query.edit_message_text(
            f"✅ *Approval Complete*\n\n"
            f"User `{user_id}` has been approved for Step {step_num}.\n"
            f"They have been notified and moved to the next step.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_menu")]])
        )
    
    elif not is_approved:
        # Remove from pending
        if str(user_id) in pending_approvals:
            del pending_approvals[str(user_id)]
            save_json(PENDING_FILE, pending_approvals)
        
        # Notify user
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"❌ *Submission Not Approved* ❌\n\n"
                 f"Unfortunately, your submission for Step {step_num} - {STEP_DETAILS[step_num]['name']} could not be approved.\n\n"
                 f"*Possible reasons:*\n"
                 f"• Task was not completed properly\n"
                 f"• Required verification missing\n"
                 f"• Need to double-check instructions\n\n"
                 f"Please review the step carefully and try again.\n\n"
                 f"Type /start to continue or contact support for help.",
            parse_mode="Markdown"
        )
        
        await query.edit_message_text(
            f"❌ *Submission Rejected*\n\n"
            f"User `{user_id}`'s submission for Step {step_num} has been rejected.\n\n"
            f"They have been notified to try again.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_menu")]])
        )

# ============= REMINDER SYSTEM =============
async def send_smart_reminder(context: ContextTypes.DEFAULT_TYPE, user_id, user_progress):
    """Send professional reminder based on user's progress"""
    user_id = int(user_id)
    completed = user_progress.get("completed_steps", [])
    current_step = user_progress.get("current_step", 1)
    reminder_count = user_progress.get("reminder_count", 0) + 1
    user_progress["reminder_count"] = reminder_count
    save_json(USER_DATA_FILE, user_data)
    
    # Calculate hours since last action
    last_action = datetime.fromisoformat(user_progress.get("last_action", datetime.now().isoformat()))
    hours_passed = int((datetime.now() - last_action).total_seconds() / 3600)
    
    # Different reminder messages based on reminder count
    if reminder_count == 1:
        message = (
            f"⏰ *Gentle Reminder* ⏰\n\n"
            f"Hi there! We noticed you started your BitAI setup but haven't completed Step {current_step} yet.\n\n"
            f"*Your Progress:* {len(completed)}/6 steps completed\n"
            f"*Current Step:* {STEP_DETAILS[current_step]['name']}\n\n"
            f"Need help? Just reply or use the buttons below to continue where you left off.\n\n"
            f"Don't let manual trading hold you back - complete your setup to start automated 24/7 trading! 🚀"
        )
    elif reminder_count == 2:
        message = (
            f"🔔 *Important Update* 🔔\n\n"
            f"It's been {hours_passed} hours since your last activity, and your BitAI setup is still incomplete.\n\n"
            f"📊 *Current Status:*\n"
            f"• ✅ Completed: {len(completed)} steps\n"
            f"• ⏳ Pending: Step {current_step} - {STEP_DETAILS[current_step]['name']}\n\n"
            f"*Why complete setup?*\n"
            f"• Eliminate emotional trading mistakes\n"
            f"• Execute trades 24/7 automatically\n"
            f"• Based on real-time market data\n\n"
            f"Click below to continue your setup now!"
        )
    elif reminder_count == 3:
        message = (
            f"⚠️ *Final Reminder* ⚠️\n\n"
            f"This is your {reminder_count}rd reminder to complete your BitAI setup.\n\n"
            f"*Remaining Steps:* {', '.join([f'Step {s}' for s in get_incomplete_steps(user_id)])}\n\n"
            f"*Benefits you're missing out on:*\n"
            f"• AI-powered trading signals\n"
            f"• Automated risk management\n"
            f"• 24/7 market monitoring\n"
            f"• No emotions, just execution\n\n"
            f"Don't let this opportunity pass! Complete your setup now."
        )
    else:
        message = (
            f"🚨 *URGENT: Action Required* 🚨\n\n"
            f"You have received multiple reminders to complete your BitAI setup.\n\n"
            f"*Unfinished Steps:* {', '.join([f'Step {s}' for s in get_incomplete_steps(user_id)])}\n\n"
            f"To activate your automated trading bot:\n"
            f"1️⃣ Type /start\n"
            f"2️⃣ Complete the remaining steps\n"
            f"3️⃣ Get admin approval\n\n"
            f"Need assistance? Contact support directly: http://wa.me/6589691668\n\n"
            f"Don't delay - every hour of manual trading is potential profit lost! 💰"
        )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Continue Setup", callback_data=f"continue_step_{current_step}")],
        [InlineKeyboardButton("📞 Contact Support", url="http://wa.me/6589691668")],
        [InlineKeyboardButton("❓ I Need Help", callback_data="need_help")]
    ])
    
    await context.bot.send_message(
        chat_id=user_id,
        text=message,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    
    user_progress["last_reminder"] = datetime.now().isoformat()
    save_json(USER_DATA_FILE, user_data)

async def reminder_loop(context: ContextTypes.DEFAULT_TYPE):
    """Check for users who need reminders (6-hour intervals)"""
    now = datetime.now()
    
    for uid, data in user_data.items():
        # Skip completed users
        if data.get("state") == STATE_COMPLETED:
            continue
        
        # Skip if recently reminded (within 6 hours)
        last_reminder = data.get("last_reminder")
        if last_reminder:
            last_reminder_time = datetime.fromisoformat(last_reminder)
            if (now - last_reminder_time) < timedelta(hours=6):
                continue
        
        # Check last action
        last_action = datetime.fromisoformat(data.get("last_action", datetime.now().isoformat()))
        hours_inactive = (now - last_action).total_seconds() / 3600
        
        # Send reminder after 6 hours of inactivity
        if hours_inactive >= 6:
            await send_smart_reminder(context, uid, data)

# ============= CALLBACK HANDLERS =============
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    
    await query.answer()
    
    # Continue setup
    if data.startswith("continue_step_"):
        step_num = int(data.replace("continue_step_", ""))
        await show_step(update, context, step_num, edit_mode=True)
    
    # Go to step
    elif data.startswith("go_to_step_"):
        step_num = int(data.replace("go_to_step_", ""))
        await show_step(update, context, step_num, edit_mode=True)
    
    # Submit step
    elif data.startswith("submit_step_"):
        step_num = int(data.replace("submit_step_", ""))
        await submit_step(update, context, step_num)
    
    # View all steps
    elif data == "view_all_steps":
        progress = get_user_progress(user_id)
        completed = progress.get("completed_steps", [])
        text = "*📋 All Setup Steps:*\n\n"
        for i in range(1, 7):
            status = "✅" if i in completed else "⏳"
            name = STEP_DETAILS[i]['name']
            text += f"{status} **Step {i}:** {name}\n"
            if i not in completed:
                text += f"   → {STEP_DETAILS[i]['instruction'][:50]}...\n"
            text += "\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")],
            [InlineKeyboardButton(f"📌 Continue Step {progress['current_step']}", 
                                  callback_data=f"continue_step_{progress['current_step']}")]
        ])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    
    # Help
    elif data.startswith("help_step_"):
        step_num = int(data.replace("help_step_", ""))
        step = STEP_DETAILS[step_num]
        help_text = (
            f"❓ *Help for Step {step_num}: {step['name']}* ❓\n\n"
            f"*Common Issues:*\n\n"
            f"**Problem:** Can't verify my Binance account\n"
            f"**Solution:** Make sure you have submitted valid ID and completed facial verification. Wait 5-15 minutes for approval.\n\n"
            f"**Problem:** API keys not working\n"
            f"**Solution:** Ensure you enabled Futures trading in API settings and whitelisted the IP address.\n\n"
            f"**Problem:** Transfer not showing in Futures\n"
            f"**Solution:** Make sure you selected 'Futures' as destination when transferring.\n\n"
            f"Still need help? Contact support: http://wa.me/6589691668"
        )
        await query.edit_message_text(help_text, parse_mode="Markdown", 
                                      reply_markup=InlineKeyboardMarkup([
                                          [InlineKeyboardButton("🔙 Back to Step", callback_data=f"continue_step_{step_num}")],
                                          [InlineKeyboardButton("📞 Contact Support", url="http://wa.me/6589691668")]
                                      ]))
    
    # Main menu
    elif data == "main_menu":
        keyboard, progress_bar = get_main_menu_keyboard(user_id)
        progress = get_user_progress(user_id)
        completed = len(progress.get("completed_steps", []))
        await query.edit_message_text(
            f"🏠 *Main Menu*\n\n"
            f"*Your Progress:*\n{progress_bar}\n"
            f"📊 *Completed:* {completed}/6 steps\n\n"
            f"*Current Step:* {STEP_DETAILS[progress['current_step']]['name']}\n\n"
            f"Choose an option below:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    
    # Need help
    elif data == "need_help":
        await query.edit_message_text(
            f"🆘 *How can we help you?* 🆘\n\n"
            f"• 💬 *Chat Support:* {http://wa.me/6589691668}\n"
            f"• 📧 *Email:* info@bitai.app\n"
            f"• 📖 *FAQ:* https://bitai.app/faq\n\n"
            f"*Common Solutions:*\n"
            f"1️⃣ Tyoe /start to reset your session\n"
            f"2️⃣ Use the 'Back' buttons to revisit steps\n"
            f"3️⃣ Contact admin for urgent issues\n\n"
            f"Our support team is available 24/7!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")],
                [InlineKeyboardButton("📞 WhatsApp Support", url="http://wa.me/6589691668")]
            ])
        )
    
    # Admin menu
    elif data == "admin_menu":
        if ADMIN_ID and user_id == ADMIN_ID:
            pending = get_pending_users()
            if pending:
                text = f"📋 *ADMIN PANEL* - {len(pending)} Pending Review(s)\n\n"
                for uid, pend in pending.items():
                    step = pend['step']
                    text += f"• User `{uid}` - Step {step}: {STEP_DETAILS[step]['name']}\n"
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=get_admin_keyboard())
            else:
                await query.edit_message_text("📋 No pending approvals. Great job!", 
                                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="admin_menu")]]))
        else:
            await query.answer("Unauthorized access!", show_alert=True)
    
    # Review user
    elif data.startswith("review_user_"):
        if ADMIN_ID and user_id == ADMIN_ID:
            target_user = data.replace("review_user_", "")
            pend_data = pending_approvals.get(target_user, {})
            step_num = pend_data.get("step", 1)
            step = STEP_DETAILS[step_num]
            
            review_text = (
                f"👤 *Review Submission*\n\n"
                f"🆔 *User ID:* `{target_user}`\n"
                f"📌 *Step:* {step_num}/6 - {step['name']}\n"
                f"📋 *Required Task:* {step['instruction']}\n"
                f"✅ *Verification Point:* {step['verification_note']}\n"
                f"⏰ *Submitted:* {pend_data.get('requested_at', 'Unknown')}\n\n"
                f"*Action Required:* Verify the user has completed this step correctly."
            )
            await query.edit_message_text(review_text, parse_mode="Markdown", reply_markup=get_review_keyboard(target_user))
    
    # Approve
    elif data.startswith("approve_"):
        if ADMIN_ID and user_id == ADMIN_ID:
            target_user = data.replace("approve_", "")
            await handle_approval(update, context, target_user, True)
    
    # Reject
    elif data.startswith("reject_"):
        if ADMIN_ID and user_id == ADMIN_ID:
            target_user = data.replace("reject_", "")
            await handle_approval(update, context, target_user, False)
    
    # View progress
    elif data == "view_progress":
        progress = get_user_progress(user_id)
        completed = progress.get("completed_steps", [])
        text = f"🏆 *Your BitAI Progress* 🏆\n\n"
        for i in range(1, 7):
            status = "✅" if i in completed else "⏳"
            text += f"{status} Step {i}: {STEP_DETAILS[i]['name']}\n"
        text += f"\n📊 *Total:* {len(completed)}/6 steps completed\n"
        text += f"🤖 Status: {'ACTIVE 🟢' if len(completed) == 6 else 'In Progress 🟡'}"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=get_progress_keyboard(user_id))
    
    # Show completed
    elif data == "show_completed":
        progress = get_user_progress(user_id)
        completed = progress.get("completed_steps", [])
        if completed:
            text = f"✅ *Completed Steps:*\n\n"
            for step in completed:
                text += f"✓ Step {step}: {STEP_DETAILS[step]['name']}\n"
                text += f"  Completed: {progress.get(f'step_{step}_completed', 'Date not available')[:10]}\n\n"
            await query.edit_message_text(text, parse_mode="Markdown", 
                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
        else:
            await query.answer("No steps completed yet. Start with Step 1!")
    
    # Restart setup
    elif data == "restart_setup":
        user_data[str(user_id)] = {
            "completed_steps": [],
            "current_step": 1,
            "state": STATE_SETUP,
            "last_reminder": None,
            "reminder_count": 0,
            "last_action": datetime.now().isoformat()
        }
        save_json(USER_DATA_FILE, user_data)
        await show_step(update, context, 1, edit_mode=True)

# ============= ADMIN COMMAND =============
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if ADMIN_ID and user_id == ADMIN_ID:
        pending = get_pending_users()
        if pending:
            text = f"📋 *ADMIN PANEL* - {len(pending)} Pending Review(s)\n\n"
            for uid, data in pending.items():
                step = data['step']
                text += f"• User `{uid}` - Step {step}: {STEP_DETAILS[step]['name']}\n"
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_admin_keyboard())
        else:
            await update.message.reply_text("✅ No pending approvals to review.")
    else:
        await update.message.reply_text("⛔ Access denied. Admin only.")

# ============= MAIN =============
async def post_init(application: Application):
    # Run reminder check every hour
    application.job_queue.run_repeating(reminder_loop, interval=3600, first=10)

def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN not set!")
        return
    
    if ADMIN_ID == 0:
        print("WARNING: ADMIN_ID not set!")
    
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("✅ Bot is running!")
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
