import os
import subprocess
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = 130657071  # آی‌دی عددی تلگرام شما
SAVE_PATH = "./downloads"
os.makedirs(SAVE_PATH, exist_ok=True)

# پیام خوش‌آمد
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! 👋\n"
        "فقط لینک یوتیوب رو بفرست و بعد کیفیت MP4 یا MP3 رو انتخاب کن.\n"
        "فایل مستقیماً به Saved Messages شما ارسال می‌شه ✅"
    )

# دریافت لینک و نمایش دکمه کیفیت‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "youtu" not in url:
        await update.message.reply_text("❌ لطفاً یک لینک معتبر یوتیوب بفرست.")
        return

    context.user_data["youtube_url"] = url

    keyboard = [
        [InlineKeyboardButton("🎧 MP3 128kbps (~3MB/min)", callback_data="mp3_128")],
        [
            InlineKeyboardButton("📽️ MP4 360p (~5MB/min)", callback_data="mp4_360"),
            InlineKeyboardButton("📽️ MP4 480p (~8MB/min)", callback_data="mp4_480"),
        ],
        [
            InlineKeyboardButton("📽️ MP4 720p (~15MB/min)", callback_data="mp4_720"),
            InlineKeyboardButton("📽️ MP4 1080p (~25MB/min)", callback_data="mp4_1080"),
        ],
    ]

    await update.message.reply_text(
        "✅ لینک دریافت شد. حالا کیفیت رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# اجرای دانلود و ارسال به OWNER_ID
async def handle_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    url = context.user_data.get("youtube_url")

    if not url:
        await query.edit_message_text("❌ لینک پیدا نشد.")
        return

    await query.edit_message_text(f"⬇️ در حال دانلود {choice.upper()} ... لطفاً منتظر بمان.")

    if choice.startswith("mp3"):
        cmd = f'yt-dlp --no-mtime --no-cache-dir -x --audio-format mp3 --audio-quality 0 -o "{SAVE_PATH}/%(title)s.%(ext)s" "{url}"'
    elif choice == "mp4_360":
        cmd = f'yt-dlp --no-mtime --no-cache-dir -f "best[ext=mp4][height<=360]" -o "{SAVE_PATH}/%(title)s.%(ext)s" "{url}"'
    elif choice == "mp4_480":
        cmd = f'yt-dlp --no-mtime --no-cache-dir -f "best[ext=mp4][height<=480]" -o "{SAVE_PATH}/%(title)s.%(ext)s" "{url}"'
    elif choice == "mp4_720":
        cmd = f'yt-dlp --no-mtime --no-cache-dir -f "best[ext=mp4][height<=720]" -o "{SAVE_PATH}/%(title)s.%(ext)s" "{url}"'
    elif choice == "mp4_1080":
        cmd = f'yt-dlp --no-mtime --no-cache-dir -f "best[ext=mp4][height<=1080]" -o "{SAVE_PATH}/%(title)s.%(ext)s" "{url}"'
    else:
        await query.edit_message_text("❌ انتخاب نامعتبر بود.")
        return

    subprocess.run(cmd, shell=True)

    files = sorted(os.listdir(SAVE_PATH), key=lambda x: os.path.getmtime(os.path.join(SAVE_PATH, x)), reverse=True)
    filepath = os.path.join(SAVE_PATH, files[0])

    # ارسال فایل به آی‌دی شما (Saved Messages)
    try:
        await context.bot.send_document(chat_id=OWNER_ID, document=open(filepath, 'rb'))
        await query.message.reply_text("✅ فایل با موفقیت به Saved Messages شما ارسال شد.")
    except Exception as e:
        await query.message.reply_text(f"❌ خطا در ارسال فایل: {e}")

# راه‌اندازی ربات
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("https?://"), handle_message))
app.add_handler(CallbackQueryHandler(handle_format))
app.run_polling()
