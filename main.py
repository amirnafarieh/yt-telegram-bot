for f in formats:
        h = f['height']
        text = f"📽️ MP4 {h}p ({f['size']})"
        buttons.append([InlineKeyboardButton(text, callback_data=f"yt_{f['format_id']}")])])

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
