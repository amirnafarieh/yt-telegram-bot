import logging
import os
import requests
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    ConversationHandler, CallbackQueryHandler, filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AGE, HEIGHT, WEIGHT, MENU, DIET, WORKOUT, GROCERY, DIET_NEXT = range(8)
user_data_dict = {}

def fix_persian_numbers(text):
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    table = str.maketrans("".join(persian_digits), "".join(english_digits))
    return text.translate(table)

def extract_number(text):
    text = fix_persian_numbers(text)
    text = text.strip()
    try:
        return float(text)
    except:
        match = re.search(r'(\d+)(\.\d+)?', text)
        if match:
            return float(match.group())
    raise ValueError("no valid number found")

def call_ai(prompt):
    headers = {
        "Authorization": f"Bearer {os.getenv('GEMINI_API_KEY')}",
        "Content-Type": "application/json"
    }
    data = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}]
    }
    response = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=" + os.getenv('GEMINI_API_KEY'),
        headers=headers,
        json=data
    )
    if response.status_code != 200:
        print("AI ERROR:", response.status_code, response.text)
        raise Exception("AI request failed")
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("به ربات هوش مصنوعی باشگاه ماکوان خوش آمدی!\nلطفاً سنت رو وارد کن:")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = extract_number(update.message.text)
        user_data_dict[update.effective_user.id] = {"age": age}
        await update.message.reply_text("قدت به سانتی‌متر:")
        return HEIGHT
    except:
        await update.message.reply_text("لطفاً عدد معتبر وارد کن.")
        return AGE

async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        height = extract_number(update.message.text)
        user_data_dict[update.effective_user.id]["height"] = height
        await update.message.reply_text("وزنت به کیلوگرم:")
        return WEIGHT
    except:
        await update.message.reply_text("فقط عدد وارد کن.")
        return HEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = extract_number(update.message.text)
        user_data_dict[update.effective_user.id]["weight"] = weight
        await update.message.reply_text("در حال پردازش اطلاعات بدنی...")
        user = user_data_dict[update.effective_user.id]
        prompt = f"""سن: {user['age']}, قد: {user['height']} سانتی‌متر, وزن: {user['weight']} کیلوگرم
شاخص توده بدنی کاربر را محاسبه کن و فقط به این صورت پاسخ بده:
- شاخص توده بدنی شما: عدد
- شما باید حدود X کیلو وزن کم یا زیاد کنید.
- ورزش‌های مناسب برای شما:
- لیست ۵ ورزش (فقط اسم‌ها، بدون هیچ توضیحی)"""
        response = call_ai(prompt)
        await update.message.reply_text(response, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("برنامه غذایی", callback_data="diet"),
             InlineKeyboardButton("برنامه ورزشی", callback_data="workout")]
        ]))
        return MENU
    except Exception as e:
        print("وزن خطا:", e)
        await update.message.reply_text("لطفاً عدد معتبر وارد کن.")
        return WEIGHT

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "diet":
        prompt = "برنامه رژیم غذایی دقیق برای ۷ روز بنویس. فقط برای هر روز، صبحانه، ناهار، شام و میان‌وعده بنویس. توضیح اضافه نده."
        context.user_data["diet_prompt"] = prompt
        response = call_ai(prompt)
        await query.edit_message_text(response, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("تبدیل به لیست خرید", callback_data="grocery")],
            [InlineKeyboardButton("برنامه هفته بعد", callback_data="diet_next")],
            [InlineKeyboardButton("منوی اصلی", callback_data="main_menu")]
        ]))
        return DIET
    elif query.data == "workout":
        prompt = "برنامه تمرینی سبک ۷ روزه برای منزل بنویس. فقط تمرینات، بدون هیچ توضیح اضافی."
        response = call_ai(prompt)
        await query.edit_message_text(response, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("برنامه هفته بعد", callback_data="workout_next")],
            [InlineKeyboardButton("منوی اصلی", callback_data="main_menu")]
        ]))
        return WORKOUT

async def handle_grocery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    diet_prompt = context.user_data.get("diet_prompt", "")
    prompt = f"بر اساس این برنامه غذایی، یک لیست خرید برای ۷ روز تهیه کن:\n{diet_prompt}"
    response = call_ai(prompt)
    await query.edit_message_text(response, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("برنامه هفته بعد", callback_data="diet_next")],
        [InlineKeyboardButton("منوی اصلی", callback_data="main_menu")]
    ]))
    return GROCERY

async def handle_diet_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prompt = "برنامه رژیم هفته دوم رو بنویس. فقط غذاها، بدون هیچ توضیحی."
    response = call_ai(prompt)
    await query.edit_message_text(response, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("منوی اصلی", callback_data="main_menu")]
    ]))
    return DIET_NEXT

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("لطفاً مسیر مورد نظرت را انتخاب کن:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("برنامه غذایی", callback_data="diet"),
         InlineKeyboardButton("برنامه ورزشی", callback_data="workout")]
    ]))
    return MENU

async def handle_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    return await start(update, context)

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            MENU: [CallbackQueryHandler(handle_menu)],
            DIET: [CallbackQueryHandler(handle_grocery, pattern="^grocery$"),
                   CallbackQueryHandler(handle_diet_next, pattern="^diet_next$"),
                   CallbackQueryHandler(handle_main_menu, pattern="^main_menu$")],
            WORKOUT: [CallbackQueryHandler(handle_main_menu, pattern="^main_menu$")],
            GROCERY: [CallbackQueryHandler(handle_diet_next, pattern="^diet_next$"),
                      CallbackQueryHandler(handle_main_menu, pattern="^main_menu$")],
            DIET_NEXT: [CallbackQueryHandler(handle_main_menu, pattern="^main_menu$")],
        },
        fallbacks=[CallbackQueryHandler(handle_restart, pattern="^restart$")]
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
