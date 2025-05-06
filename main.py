import os
import subprocess
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ChatMember
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = "@amirnafarieh_co"
SAVE_PATH = "./downloads"
os.makedirs(SAVE_PATH, exist_ok=True)

# بررسی عضویت در کانال
async def is_user_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in [ChatMember.MEMBER, ChatMember.OWNER, ChatMember.ADMINISTRATOR]
    except:
        return False

# پیام خوش‌آمد
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_subscribed(context.bot, user_id):
        keyboard = [[InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
                    [InlineKeyboardButton("✅ عضو شدم", callback_data="check_subscription")]]
        await update.message.reply_text("برای استفاده از ربات لطفاً ابتدا در کانال عضو شوید:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    await update.message.reply_text("سلام! 👋\nلینک یوتیوب رو بفرست و بعد کیفیت دلخواه رو انتخاب کن.")

# بررسی دوباره عضویت پس از کلیک "عضو شدم"
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if await is_user_subscribed(context.bot, user_id):
        await query.edit_message_text("✅ عضویت تأیید شد. حالا لینک یوتیوب رو بفرست.")
    else:
        await query.edit_message_text("❌ هنوز عضو نیستی! لطفاً دوباره امتحان کن با زدن دکمه عضو شدم.")

# گرفتن لینک و نمایش دکمه‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_subscribed(context.bot, user_id):
        keyboard = [[InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
                    [InlineKeyboardButton("✅ عضو شدم", callback_data="check_subscription")]]
        await update.message.reply_text("❗ برای استفاده از ربات لطفاً ابتدا در کانال عضو شوید:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    url = update.message.text
    if "youtu" not in url:
        await update.message.reply_text("❌ لطفاً لینک معتبر یوتیوب بفرست.")
        return

    context.user_data["youtube_url"] = url

    keyboard = [
        [InlineKeyboardButton("🎧 MP3 128kbps", callback_data="mp3_128")],
        [InlineKeyboardButton("📽️ MP4 360p", callback_data="mp4_360"),
         InlineKeyboardButton("📽️ MP4 480p", callback_data="mp4_480")],
        [InlineKeyboardButton("📽️ MP4 720p", callback_data="mp4_720"),
         InlineKeyboardButton("📽️ MP4 1080p", callback_data="mp4_1080")],
    ]

    await update.message.reply_text(
        "✅ لینک دریافت شد. لطفاً کیفیت فایل رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# دانلود و نمایش نوار پیشرفت عددی
async def handle_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if not await is_user_subscribed(context.bot, user_id):
        await query.edit_message_text("❗ برای ادامه باید عضو کانال بشی.")
        return

    choice = query.data
    url = context.user_data.get("youtube_url")
    chat_id = query.message.chat.id

    if not url:
        await query.edit_message_text("❌ لینک پیدا نشد.")
        return

    progress_msg = await query.message.reply_text("📦 آماده‌سازی فایل...")

    filename_template = f"{SAVE_PATH}/%(title)s.%(ext)s"

    if choice == "mp3_128":
        cmd = f'yt-dlp --cookies cookies.txt -x --audio-format mp3 --audio-quality 0 -o "{filename_template}" "{url}"'
    elif choice == "mp4_360":
        cmd = f'yt-dlp --cookies cookies.txt -f "best[ext=mp4][height<=360]" -o "{filename_template}" "{url}"'
    elif choice == "mp4_480":
        cmd = f'yt-dlp --cookies cookies.txt -f "best[ext=mp4][height<=480]" -o "{filename_template}" "{url}"'
    elif choice == "mp4_720":
        cmd = f'yt-dlp --cookies cookies.txt -f "best[ext=mp4][height<=720]" -o "{filename_template}" "{url}"'
    elif choice == "mp4_1080":
        cmd = f'yt-dlp --cookies cookies.txt -f "best[ext=mp4][height<=1080]" -o "{filename_template}" "{url}"'
    else:
        await progress_msg.edit_text("❌ کیفیت نامعتبر.")
        return

    # اجرای yt-dlp با بروزرسانی پیام درصدی ساده
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        text=True
    )

    percent = 0
    async for line in process.stdout:
        if "%" in line:
            parts = line.strip().split()
            for p in parts:
                if "%" in p:
                    try:
                        percent = int(p.strip().replace("%", "").split(".")[0])
                        await progress_msg.edit_text(f"📦 آماده‌سازی فایل... {percent}%")
                    except:
                        continue

    await process.wait()

    files = sorted(os.listdir(SAVE_PATH), key=lambda x: os.path.getmtime(os.path.join(SAVE_PATH, x)), reverse=True)
    if not files:
        await progress_msg.edit_text("❌ فایل پیدا نشد.")
        return

    filepath = os.path.join(SAVE_PATH, files[0])

    try:
        await context.bot.send_document(chat_id=chat_id, document=open(filepath, 'rb'))
        await progress_msg.edit_text("✅ فایل ارسال شد.")
    except Exception as e:
        await progress_msg.edit_text(f"❌ خطا در ارسال فایل:\n{e}")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("https?://"), handle_message))
app.add_handler(CallbackQueryHandler(check_subscription, pattern="check_subscription"))
app.add_handler(CallbackQueryHandler(handle_format))
app.run_polling()
