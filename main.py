import logging
import os
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler

# فعال‌سازی لاگ‌ها
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# وضعیت‌های گفتگو
AGE, HEIGHT, WEIGHT, SPORT_CONFIRM, DIET_CONFIRM, DETAILED_DIET_CONFIRM, NEXT_DIET = range(7)

# ذخیره اطلاعات کاربران
user_data_dict = {}

# 🎯 تابع اصلی تولید رژیم هوش مصنوعی از DeepSeek
def get_ai_diet_plan(user_data):
    prompt = f"""سن: {user_data['age']}، قد: {user_data['height']} سانتی‌متر، وزن: {user_data['weight']} کیلوگرم
لطفاً یک رژیم غذایی دقیق، متعادل و مناسب با هدف {'کاهش وزن' if user_data['bmi'] >= 25 else 'افزایش وزن' if user_data['bmi'] < 18.5 else 'سلامت عمومی'} برای این کاربر ارائه بده. برای هر وعده غذایی (صبحانه، ناهار، شام و میان‌وعده) غذاهای مشخص و مقدار حدودی بنویس. رژیم باید فارسی باشد.
"""

    headers = {
        "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "شما یک متخصص تغذیه هستی."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]

# ✅ توابع ربات
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

    # مرحله بعدی: سوال درباره رژیم دقیق
    keyboard = [[InlineKeyboardButton("بله", callback_data="yes_detailed"),
                 InlineKeyboardButton("خیر", callback_data="no_detailed")]]
    await context.bot.send_message(chat_id=query.message.chat.id, text="آیا مایل هستی رژیم غذایی دقیق‌تری برای هر روز دریافت کنی؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return DETAILED_DIET_CONFIRM

async def send_detailed_diet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bmi = user_data_dict[query.from_user.id]["bmi"]

    if query.data == "yes_detailed":
        if bmi >= 25:
            diet = "صبحانه: 2 عدد تخم‌مرغ آب‌پز + یک کف دست نان\nناهار: 100 گرم تن ماهی + سالاد\nشام: سوپ سبزیجات"
        elif bmi < 18.5:
            diet = "صبحانه: شیر و تخم‌مرغ\nناهار: برنج و مرغ\nشام: پاستا با آبمیوه"
        else:
            diet = "برای وزن نرمال، رژیم متعادل و سبک بهترین انتخاب است."

        await query.edit_message_text(f"رژیم دقیق:\n{diet}")
    else:
        await query.edit_message_text("درخواست رژیم دقیق نادیده گرفته شد.")

    keyboard = [[InlineKeyboardButton("رژیم متفاوت از هوش مصنوعی", callback_data="ai_diet")]]
    await context.bot.send_message(chat_id=query.message.chat.id, text="آیا مایل به دریافت رژیم متفاوت از هوش مصنوعی هستی؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return NEXT_DIET

async def send_ai_diet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_data = user_data_dict[query.from_user.id]
    await query.edit_message_text("در حال تهیه رژیم غذایی هوشمند، لطفاً صبر کنید...")

    try:
        ai_diet = get_ai_diet_plan(user_data)
        await context.bot.send_message(chat_id=query.message.chat.id, text=ai_diet)
    except Exception as e:
        await context.bot.send_message(chat_id=query.message.chat.id, text="متأسفانه در دریافت رژیم از هوش مصنوعی خطایی رخ داد.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مکالمه لغو شد.")
    return ConversationHandler.END

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            SPORT_CONFIRM: [CallbackQueryHandler(sport_confirm)],
            DIET_CONFIRM: [CallbackQueryHandler(diet_confirm)],
            DETAILED_DIET_CONFIRM: [CallbackQueryHandler(send_detailed_diet)],
            NEXT_DIET: [CallbackQueryHandler(send_ai_diet, pattern="^ai_diet$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()
