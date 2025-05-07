import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
AGE, HEIGHT, WEIGHT, SPORT_CONFIRM, DIET_CONFIRM = range(5)

user_data_dict = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! لطفاً سنت رو وارد کن:")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_dict[update.effective_user.id] = {"age": int(update.message.text)}
    await update.message.reply_text("قدت رو به سانتی‌متر وارد کن:")
    return HEIGHT

async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_dict[update.effective_user.id]["height"] = int(update.message.text)
    await update.message.reply_text("وزنت رو به کیلوگرم وارد کن:")
    return WEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_dict[update.effective_user.id]["weight"] = int(update.message.text)
    data = user_data_dict[update.effective_user.id]
    height_m = data["height"] / 100
    bmi = data["weight"] / (height_m ** 2)
    data["bmi"] = bmi

    if bmi >= 25:
        msg = f"شاخص توده بدنی (BMI) شما {bmi:.1f} است و شما اضافه وزن دارید."
    elif bmi >= 18.5:
        msg = f"شاخص توده بدنی (BMI) شما {bmi:.1f} است و در محدوده نرمال هستید."
    else:
        msg = f"شاخص توده بدنی (BMI) شما {bmi:.1f} است و شما کمبود وزن دارید."

    await update.message.reply_text(msg)

    keyboard = [[InlineKeyboardButton("بله", callback_data="yes_sport"),
                 InlineKeyboardButton("خیر", callback_data="no_sport")]]
    await update.message.reply_text("آیا مایل به دریافت پیشنهاد ورزشی هستی؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return SPORT_CONFIRM

async def sport_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "yes_sport":
        bmi = user_data_dict[query.from_user.id]["bmi"]
        if bmi >= 25:
            sport = "پیاده‌روی تند، دوچرخه‌سواری، شنا یا ایروبیک"
        elif bmi < 18.5:
            sport = "تمرینات مقاومتی و افزایش توده عضلانی"
        else:
            sport = "فعالیت بدنی منظم مثل یوگا و تمرینات ترکیبی"

        await query.edit_message_text(f"پیشنهاد ورزشی: {sport}")
    else:
        await query.edit_message_text("درخواست ورزش نادیده گرفته شد.")

    keyboard = [[InlineKeyboardButton("بله", callback_data="yes_diet"),
                 InlineKeyboardButton("خیر", callback_data="no_diet")]]
    await context.bot.send_message(chat_id=query.message.chat.id, text="آیا مایل به دریافت رژیم غذایی برای یک ماه آینده هستی؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return DIET_CONFIRM

async def diet_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "yes_diet":
        diet_plan = "\n".join([
            "هفته اول: کاهش مصرف قند و چربی، مصرف سبزیجات و میوه بیشتر",
            "هفته دوم: افزایش پروتئین و حذف غذاهای فرآوری‌شده",
            "هفته سوم: وعده‌های منظم، نوشیدن آب کافی، پیاده‌روی روزانه",
            "هفته چهارم: کنترل مقدار غذا، تنقلات سالم مثل مغزها"
        ])
        await query.edit_message_text(f"برنامه رژیم غذایی:\n{diet_plan}")
    else:
        await query.edit_message_text("درخواست رژیم نادیده گرفته شد.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مکالمه لغو شد.")
    return ConversationHandler.END

def main():
    import os
    TOKEN = os.getenv("BOT_TOKEN")  # Set this in Railway
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            SPORT_CONFIRM: [CallbackQueryHandler(sport_confirm)],
            DIET_CONFIRM: [CallbackQueryHandler(diet_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()
