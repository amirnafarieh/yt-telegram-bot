import os
import subprocess
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")
SAVE_PATH = "./downloads"
os.makedirs(SAVE_PATH, exist_ok=True)

# پیام خوش‌آمد و آموزش
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "سلام! 👋\n"
        "من یک ربات دانلود یوتیوب هستم. فقط کافیه لینک ویدئو رو بفرستی 🎥\n\n"
        "بعدش می‌تونی انتخاب کنی که فایل رو MP3 یا MP4 و با چه کیفیتی می‌خوای 🎧📽️"
    )
    await update.message.reply_text(welcome_text)

# دریافت لینک
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "youtu" not in url:
        await update.message.reply_text("❌ لطفاً یک لینک معتبر یوتیوب ارسال کن.")
        return

    context.user_data["youtube_url"] = url

    keyboard = [
        [
            InlineKeyboardButton("🎧 MP3 (128kbps)", callback_data="mp3_128"),
            InlineKeyboardButton("🎧 MP3 (192kbps)", callback_data="mp3_192"),
        ],
        [
            InlineKeyboardButton("📽️ MP4 (480p)", callback_data="mp4_480"),
            InlineKeyboardButton("📽️ MP4 (720p)", callback_data="mp4_720"),
        ]
    ]

    await update.message.reply_text(
        "✅ لینک دریافت شد.\nحالا یکی از گزینه‌های زیر رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# اجرای دانلود بر اساس انتخاب کاربر
async def handle_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    url = context.user_data.get("youtube_url")

    if not url:
        await query.edit_message_text("❌ لینک یوتیوب پیدا نشد. لطفاً دوباره لینک بفرست.")
        return

    await query.edit_message_text(f"⬇️ در حال دانلود {choice.upper()}... لطفاً منتظر بمان.")

    # ساخت دستور yt-dlp
    if choice.startswith("mp3"):
        cmd = f'yt-dlp -x --audio-format mp3 --audio-quality 0 -o "{SAVE_PATH}/%(title)s.%(ext)s" "{url}"'
    elif choice == "mp4_480":
        cmd = f'yt-dlp -f "bestvideo[height<=480]+bestaudio" --merge-output-format mp4 -o "{SAVE_PATH}/%(title)s.%(ext)s" "{url}"'
    elif choice == "mp4_720":
        cmd = f'yt-dlp -f "bestvideo[height<=720]+bestaudio" --merge-output-format mp4 -o "{SAVE_PATH}/%(title)s.%(ext)s" "{url}"'
    else:
        await query.edit_message_text("❌ انتخاب نامعتبر.")
        return

    subprocess.run(cmd, shell=True)
    files = sorted(os.listdir(SAVE_PATH), key=lambda x: os.path.getmtime(os.path.join(SAVE_PATH, x)), reverse=True)
    filepath = os.path.join(SAVE_PATH, files[0])

    await query.message.reply_document(document=open(filepath, 'rb'))
    await query.message.reply_text("✅ دانلود و ارسال با موفقیت انجام شد.")

# ساخت و اجرای ربات
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("https?://"), handle_message))
app.add_handler(CallbackQueryHandler(handle_format))

app.run_polling()
