import logging
import os
import requests
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AGE, HEIGHT, WEIGHT = range(3)
user_data_dict = {}

# 🔤 تبدیل اعداد فارسی به انگلیسی
def fix_persian_numbers(text):
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    table = str.maketrans("".join(persian_digits), "".join(english_digits))
    return text.translate(table)

# 🔍 استخراج عدد اعشاری از متن
def extract_number(text):
    text = fix_persian_numbers(text)
    match = re.search(r'\d+(\.\d+)?', text)
    if match:
        return float(match.group())
    else:
        raise ValueError("no valid number found")

# 🧠 درخواست به Cohere
def get_full_response_from_ai(user_data):
    prompt = f"""اطلاعات کاربر:
سن: {user_data['age']} سال
قد: {user_data['height']} سانتی‌متر
وزن: {user_data['weight']} کیلوگرم

لطفاً موارد زیر را به زبان فارسی و دقیق ارائه بده:
1. محاسبه شاخص توده بدنی (BMI) و توضیح اینکه آیا کاربر اضافه وزن دارد یا کمبود وزن یا نرمال است.
2. بر اساس BMI، یک یا چند ورزش مناسب برای این فرد پیشنهاد بده.
3. یک رژیم غذایی دقیق برای 7 روز هفته بنویس. برای هر روز، صبحانه، ناهار، شام و میان‌وعده‌های مشخص بنویس.
پاسخ باید فارسی، علمی و کاربردی باشد.
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

# 🎯 مکالمه ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! لطفاً سنت را وارد کن:")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = extract_number(update.message.text)
        user_data_dict[update.effective_user.id] = {"age": age}
        await update.message.reply_text("قدت رو به سانتی‌متر وارد کن:")
        return HEIGHT
    except:
        await update.message.reply_text("❗ لطفاً فقط عدد وارد کن. مثلاً 25")
        return AGE

async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        height = extract_number(update.message.text)
        user_data_dict[update.effective_user.id]["height"] = height
        await update.message.reply_text("وزنت رو به کیلوگرم وارد کن:")
        return WEIGHT
    except:
        await update.message.reply_text("❗ لطفاً فقط عدد وارد کن. مثلاً 170")
        return HEIGHT

async def get_weight_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = extract_number(update.message.text)
        user_data_dict[update.effective_user.id]["weight"] = weight

        await update.message.reply_text("در حال تهیه برنامه از هوش مصنوعی... لطفاً صبر کن ⏳")

        user_data = user_data_dict[update.effective_user.id]
        ai_response = get_full_response_from_ai(user_data)

        await update.message.reply_text(ai_response)
        return ConversationHandler.END
    except Exception as e:
        print("خطا در وزن:", e)
        await update.message.reply_text("❗ لطفاً فقط عدد وارد کن. مثلاً 75 یا 70.5")
        return WEIGHT

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
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight_and_generate)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()
