import logging
import os
import requests
import re
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, CallbackQueryHandler, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AGE, HEIGHT, WEIGHT, ASK_WEEKLY_PLAN, ASK_NEXT_WEEK = range(5)
user_data_dict = {}

# عدد فارسی به انگلیسی
def fix_persian_numbers(text):
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    table = str.maketrans("".join(persian_digits), "".join(english_digits))
    return text.translate(table)

# استخراج عدد از متن
def extract_number(text):
    text = fix_persian_numbers(text)
    match = re.search(r'\d+(\.\d+)?', text)
    if match:
        return float(match.group())
    else:
        raise ValueError("no valid number found")

# درخواست اولیه به AI (BMI و ورزش)
def prompt_bmi_and_sports(user_data):
    prompt = f"""اطلاعات کاربر:
سن: {user_data['age']} سال
قد: {user_data['height']} سانتی‌متر
وزن: {user_data['weight']} کیلوگرم

فقط موارد زیر را بنویس:
1. مقدار عددی BMI بدون هیچ توضیحی
2. چند کیلو باید وزن کم کند یا اضافه کند
3. ۵ ورزش مناسب فقط نام ورزش‌ها، بدون هیچ توضیح

همه خروجی باید فارسی و لیستی باشد. هیچ توضیح اضافه یا تحلیل نده."""
    return prompt

# درخواست رژیم هفتگی
def prompt_weekly_diet(week_num):
    return f"""لطفاً یک برنامه رژیم غذایی دقیق برای هفته {week_num} بنویس.
هر روز باید شامل صبحانه، ناهار، شام و میان‌وعده باشد.
پاسخ فقط به زبان فارسی و ساختارمند باشد."""

# تابع ارسال به Cohere
def get_ai_response(prompt):
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

# شروع گفتگو
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! لطفاً سنت را وارد کن:")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = extract_number(update.message.text)
        user_data_dict[update.effective_user.id] = {"age": age}
        await update.message.reply_text("قدت به سانتی‌متر:")
        return HEIGHT
    except:
        await update.message.reply_text("فقط عدد وارد کن. مثل 25")
        return AGE

async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        height = extract_number(update.message.text)
        user_data_dict[update.effective_user.id]["height"] = height
        await update.message.reply_text("وزنت به کیلوگرم:")
        return WEIGHT
    except:
        await update.message.reply_text("فقط عدد وارد کن. مثل 170")
        return HEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = extract_number(update.message.text)
        user_data_dict[update.effective_user.id]["weight"] = weight
        await update.message.reply_text("در حال محاسبه توسط هوش مصنوعی...")

        user_data = user_data_dict[update.effective_user.id]
        prompt = prompt_bmi_and_sports(user_data)
        result = get_ai_response(prompt)

        await update.message.reply_text(result)

        # دکمه دریافت رژیم
        keyboard = [[InlineKeyboardButton("بله", callback_data="yes_diet"),
                     InlineKeyboardButton("خیر", callback_data="no_diet")]]
        await update.message.reply_text("آیا مایل به دریافت رژیم غذایی هفتگی هستی؟", reply_markup=InlineKeyboardMarkup(keyboard))
        return ASK_WEEKLY_PLAN
    except:
        await update.message.reply_text("فقط عدد وارد کن. مثل 70 یا 82.5")
        return WEIGHT

# واکنش به درخواست رژیم هفته اول
async def handle_weekly_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "yes_diet":
        await query.edit_message_text("در حال دریافت رژیم هفته اول از هوش مصنوعی...")
        plan = get_ai_response(prompt_weekly_diet(1))
        await context.bot.send_message(chat_id=query.message.chat_id, text=plan)

        # دکمه هفته دوم
        keyboard = [[InlineKeyboardButton("بله", callback_data="next_week"),
                     InlineKeyboardButton("خیر", callback_data="restart")]]
        await context.bot.send_message(chat_id=query.message.chat_id, text="آیا مایل به دریافت رژیم هفته دوم هستی؟", reply_markup=InlineKeyboardMarkup(keyboard))
        return ASK_NEXT_WEEK
    else:
        await query.edit_message_text("باشه. بیایم از اول شروع کنیم.")
        return await start(update, context)

# واکنش به هفته دوم یا ریست
async def handle_next_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "next_week":
        await query.edit_message_text("در حال دریافت رژیم هفته دوم...")
        plan = get_ai_response(prompt_weekly_diet(2))
        await context.bot.send_message(chat_id=query.message.chat_id, text=plan)
        await context.bot.send_message(chat_id=query.message.chat_id, text="رژیم هفته دوم هم ارسال شد. برای شروع دوباره /start رو بزن.")
        return ConversationHandler.END
    else:
        await query.edit_message_text("مکالمه از نو شروع می‌شه.")
        return await start(update, context)

# ریست دستی
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
            ASK_WEEKLY_PLAN: [CallbackQueryHandler(handle_weekly_plan)],
            ASK_NEXT_WEEK: [CallbackQueryHandler(handle_next_week)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()
