import os
import subprocess
import asyncio
import json
import uuid
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ChatMember
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = "@amirnafarieh_co"
OWNER_ID = 130657071
SAVE_PATH = "./downloads"
os.makedirs(SAVE_PATH, exist_ok=True)

# بررسی عضویت در کانال
async def is_user_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in [ChatMember.MEMBER, ChatMember.OWNER, ChatMember.ADMINISTRATOR]
    except:
        return False

# استخراج فرمت‌ها و حجم فایل‌ها

def get_video_formats(url):
    cmd = f'yt-dlp -j "{url}"'
    result = subprocess.run(cmd, shell=True, capture_output=True)
    formats = []
    try:
        info = json.loads(result.stdout.decode())
        for f in info['formats']:
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('ext') == 'mp4':
                height = f.get('height')
                filesize = f.get('filesize') or f.get('filesize_approx')
                if height and filesize:
                    size_mb = round(filesize / (1024 * 1024), 1)
                    formats.append({
                        'format_id': f['format_id'],
                        'height': height,
                        'size': f"{size_mb} MB"
                    })
    except:
        pass
    return formats

# پیام خوش‌آمد
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_subscribed(context.bot, user_id):
        keyboard = [[InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
                    [InlineKeyboardButton("✅ عضو شدم", callback_data="check_subscription")]]
        await update.message.reply_text("برای استفاده از ربات لطفاً ابتدا در کانال عضو شوید:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    await update.message.reply_text("سلام! 👋\nلینک یوتیوب رو بفرست و بعد کیفیت دلخواه رو انتخاب کن.")

# بررسی دوباره عضویت
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if await is_user_subscribed(context.bot, user_id):
        await query.edit_message_text("✅ عضویت تأیید شد. حالا لینک یوتیوب رو بفرست.")
    else:
        await query.edit_message_text("❌ هنوز عضو نیستی! لطفاً دوباره امتحان کن با زدن دکمه عضو شدم.")

# دریافت لینک و ساخت دکمه‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_subscribed(context.bot, user_id):
        keyboard = [[InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
                    [InlineKeyboardButton("✅ عضو شدم", callback_data="check_subscription")]]
        await update.message.reply_text("❗ برای استفاده از ربات لطفاً ابتدا در کانال عضو شوید:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    url = update.message.text.strip()
    if "youtu" not in url:
        await update.message.reply_text("❌ لطفاً لینک معتبر یوتیوب بفرست.")
        return

    context.user_data["youtube_url"] = url
    formats = get_video_formats(url)

    buttons = []
    used_heights = set()
    for f in formats:
        h = f['height']
        if h not in used_heights and h in [480, 720, 1080, 1440, 2160]:
            used_heights.add(h)
            text = f"📽️ MP4 {h}p ({f['size']})"
            buttons.append([InlineKeyboardButton(text, callback_data=f"yt_{f['format_id']}")])

    if not buttons:
        await update.message.reply_text("❌ کیفیت قابل پشتیبانی پیدا نشد.")
        return

    await update.message.reply_text(
        "✅ لینک دریافت شد. لطفاً کیفیت فایل رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# دانلود ویدیو با نمایش نوار پیشرفت
async def handle_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if not await is_user_subscribed(context.bot, user_id):
        await query.edit_message_text("❗ برای ادامه باید عضو کانال بشی.")
        return

    choice = query.data
    url = context.user_data.get("youtube_url")

    if not url:
        await query.edit_message_text("❌ لینک پیدا نشد.")
        return

    progress_msg = await query.message.reply_text("📦 در حال آماده‌سازی فایل... لطفاً کمی صبر کنید. 0%")
    unique_id = uuid.uuid4().hex
    filename_template = f"{SAVE_PATH}/{unique_id}.%(ext)s"

    if choice.startswith("yt_"):
        format_id = choice.split("_")[1]
        cmd = f'yt-dlp --cookies cookies.txt -f "{format_id}+bestaudio[ext=m4a]" --merge-output-format mp4 -o "{filename_template}" "{url}"'
    else:
        await progress_msg.edit_text("❌ انتخاب نامعتبر.")
        return

    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )

    percent = 0
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        decoded_line = line.decode("utf-8").strip()
        if "%" in decoded_line and ("Downloading" in decoded_line or "[download]" in decoded_line):
            for part in decoded_line.split():
                if "%" in part:
                    try:
                        percent = int(float(part.replace("%", "").replace(",", ".")))
                        await progress_msg.edit_text(f"📦 در حال آماده‌سازی فایل... لطفاً کمی صبر کنید. {percent}%")
                        break
                    except:
                        continue

    await process.wait()
    downloaded_file = next((f for f in os.listdir(SAVE_PATH) if f.startswith(unique_id)), None)
    if not downloaded_file:
        await progress_msg.edit_text("❌ فایل پیدا نشد.")
        return

    filepath = os.path.join(SAVE_PATH, downloaded_file)

    try:
        await context.bot.send_document(chat_id=user_id, document=open(filepath, 'rb'))
        await progress_msg.edit_text("✅ فایل آماده دانلود است.\nبرای فایل جدید، لینک دیگری ارسال کنید.")
    except Exception as e:
        await progress_msg.edit_text(f"❌ خطا در ارسال فایل:\n{e}")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("https?://"), handle_message))
app.add_handler(CallbackQueryHandler(check_subscription, pattern="check_subscription"))
app.add_handler(CallbackQueryHandler(handle_format))

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run_polling())
