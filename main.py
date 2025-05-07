import logging
import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# وضعیت‌ها
AGE, HEIGHT, WEIGHT = range(3)

# دیتای کاربران
user_data_dict = {}

# 📡 تابع درخواست به Cohere
def get_full_response_from_ai(user_data):
    prompt = f"""اطلاعات کاربر:
سن: {user_data['age']} سال
قد: {user_data['height']} سانتی‌متر
وزن: {user_data['weight']} کیلوگرم

لطفاً موارد زیر را به زبان فارسی و دقیق ارائه بده:
1. محاسبه شاخص توده بدنی (BMI) و توضیح اینکه آیا کاربر اضافه وزن دارد یا کمبود وزن یا نرمال است.
2. بر اساس BMI، یک یا چند ورزش مناسب برای این فرد پیشنهاد بده.
3. یک رژیم غذایی دقیق برای 7 روز هفته بنویس. برای هر روز، صبحانه، ناهار، شام و میان‌وعده‌های مشخص بنویس.
همه مطالب باید ساختاریافته، علمی، قابل درک و کاربردی باشند.
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

# شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! لطفاً سنت را وارد کن (مثلاً 28):")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_data_dict[update.effective_user.id] = {"age": int(update.message.text)}
        await update.message.reply_text("حالا لطفاً قدت رو به سانتی‌متر وارد کن (مثلاً 170):")
        return HEIGHT
    except:
        await update.message.reply_text("لطفاً یک عدد معتبر برای سن وارد کن.")
        return AGE

async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_data_dict[update.effective_user.id]["height"] = int(update.message.text)
        await update.message.reply_text("عالی! حالا وزنت رو به کیلوگرم وارد کن (مثلاً 70):")
        return WEIGHT
    except:
        await update.message.reply_text("لطفاً عدد معتبری برای قد وارد کن.")
        return HEIGHT

async def get_weight_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_data_dict[update.effective_user.id]["weight"] = int(update.message.text)
        await update.message.reply_text("در حال تهیه برنامه‌ی شخصی‌سازی‌شده از هوش مصنوعی... لطفاً صبر کن ⏳")

        user_data = user_data_dict[update.effective_user.id]
        ai_response = get_full_response_from_ai(user_data)

        # ارسال پاسخ نهایی
        await update.message.reply_text(ai_response)
        return ConversationHandler.END
    except:
        await update.message.reply_text("لطفاً عدد معتبری برای وزن وارد کن.")
        return WEIGHT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مکالمه لغو شد.")
    return ConversationHandler.END

# اجرای اصلی
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
