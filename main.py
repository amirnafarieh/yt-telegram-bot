import os
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")
SAVE_PATH = "./downloads"
os.makedirs(SAVE_PATH, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! لینک یوتیوب رو بفرست، بعد بگو mp3 یا mp4.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "youtu" not in url:
        await update.message.reply_text("لطفاً لینک یوتیوب معتبر بفرست.")
        return
    context.user_data["youtube_url"] = url
    await update.message.reply_text("✅ لینک دریافت شد. حالا فقط بنویس mp3 یا mp4.")

async def handle_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fmt = update.message.text.lower()
    url = context.user_data.get("youtube_url")
    if not url:
        await update.message.reply_text("اول لینک رو بفرست.")
        return
    await update.message.reply_text(f"در حال دانلود {fmt.upper()}...")

    if fmt == "mp3":
        cmd = f'yt-dlp -x --audio-format mp3 -o "{SAVE_PATH}/%(title)s.%(ext)s" "{url}"'
    elif fmt == "mp4":
        cmd = f'yt-dlp -f bestvideo+bestaudio --merge-output-format mp4 -o "{SAVE_PATH}/%(title)s.%(ext)s" "{url}"'
    else:
        await update.message.reply_text("❌ فقط mp3 یا mp4 مجازه.")
        return

    subprocess.run(cmd, shell=True)
    files = sorted(os.listdir(SAVE_PATH), key=lambda x: os.path.getmtime(os.path.join(SAVE_PATH, x)), reverse=True)
    filepath = os.path.join(SAVE_PATH, files[0])
    await update.message.reply_document(document=open(filepath, 'rb'))

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("https?://"), handle_message))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_format))
app.run_polling()
