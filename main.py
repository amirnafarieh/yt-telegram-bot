import logging
import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

# فعال‌سازی لاگ‌ها
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# وضعیت‌ها
AGE, HEIGHT, WEIGHT = range(3)
user_data_dict = {}

# 🔤 تابع تبدیل اعداد فارسی به انگلیسی
def fix_persian_numbers(text):
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    table = str.maketrans("".join(persian_digits), "".join(english_digits))
    return text.translate(table)

# 📡 ارتباط با Cohere
def get_full_response_from_ai(user_data):
    prompt = f"""اطلاعات کاربر:
سن: {user_data['age']} سال
قد: {user_data['height']} سانتی‌متر
وزن: {user_data['weight']} کیلوگرم

لطفاً موارد زیر را به زبان فارسی و دقیق ارائه بده:
1. محاسبه شاخص توده بدنی (BMI) و توضیح اینکه آیا کاربر اضافه وزن دارد یا کمبود وزن یا نرمال است.
2. بر اساس BMI، یک یا چند ورزش مناسب برای این فرد پیشنهاد بده.
3. یک رژیم غذایی دقیق برای 7 روز هفته بنویس. برای هر روز، صبحانه، ناهار، شام و میان‌وعده‌های مشخص بنویس.
خروجی باید ساختاریافته، علمی، و قابل درک باشد.
"""

    headers = {
        "Authorization": f"Bearer {os.getenv('COHERE_API_KEY')}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "command-r-plus",
        "chat_history": [],
        "message": prompt,
        "temperature": 0.7,
        "max_tokens": 1000
    }

    response = requests.post("https://api.cohere.ai/v1/chat", headers=headers, json=data)
    if response.status_code != 200:
        print("AI ERROR:", response.status_code, response.text)
        raise Exception("AI request failed")

    return response.json()["text"]

# 👤 مرحله سن
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! لطفاً سنت را وارد کن (مثلاً ۲۵):")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = fix_persian_numbers(update.message.text.strip())
        age = int(float(text))
        user_data_dict[update.effective_user.id] = {"age": age}
        await update.message.reply_text("قدت را به سانتی‌متر وارد کن (مثلاً ۱۷۵):")
        return HEIGHT
    except:
        await update.message.reply_text("❗ لطفاً سن را فقط با عدد وارد کن. مثلاً 25")
        return AGE

# 👤 مرحله قد
async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = fix_persian_numbers(update.message.text.strip())
        height = float(text)
        user_data_dict[update.effective_user.id]["height"] = height
        await update.message.reply_text("وزنت را به کیلوگرم وارد کن (مثلاً ۷۲ یا ۷۲.۵):")
        return WEIGHT
    except:
        await update.message.reply_text("❗ لطفاً قد را فقط با عدد وارد کن. مثلاً 170")
        return HEIGHT

# 👤 مرحله وزن و دریافت پاسخ از AI
async def get_weight_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = fix_persian_numbers(update.message.text.strip())
        weight = float(text)
        user_data_dict[update.effective_user.id]["weight"] = weight

        await update.message.reply_text("در حال تهیه برنامه شخصی از هوش مصنوعی... لطفاً چند لحظه صبر کنید ⏳")

        user_data = user_data_dict[update.effective_user.id]
        ai_response = get_full_response_from_ai(user_data)

        await update.message.reply_text(ai_response)
        return ConversationHandler.END
    except Exception as e:
        print("خطای وزن:", e)
        await update.message.reply_text("❗ لطفاً وزن را فقط با عدد وارد کن. مثلاً 75 یا 70.5")
        return WEIGHT

# لغو
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مکالمه لغو شد.")
    return ConversationHandler.END

# شروع برنامه
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight_and_generate)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()
