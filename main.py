import os
import re
import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)

API_TOKEN = os.getenv("API_TOKEN")
PORT = int(os.getenv("PORT", "8443"))
RENDER_HOST = os.getenv('RENDER_EXTERNAL_HOSTNAME')  # Render-host e.g. taxi-xxxxx.onrender.com
WEBHOOK_PATH = f"/{API_TOKEN}"
WEBHOOK_URL = f"https://{RENDER_HOST}{WEBHOOK_PATH}"

ADMIN_CHAT_ID = -1002886954464  # Замените на свой
user_data = {}

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("TAXI CHAQIRISH 🚕", callback_data="order_taxi"),
            InlineKeyboardButton("TEZKOR 24/7🚕", web_app=WebAppInfo(url="https://taxi-prototip.vercel.app/"))
        ]
    ])
    await update.message.reply_text(
        "Assalomu Aleykum, Xurmatli mijoz!\nTAXI buyurtma berish uchun quyidagi tugmalardan foydalaning:",
        reply_markup=keyboard
    )

# Step 1: Запрос номера
async def order_taxi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    user_data[chat_id] = {'step': 1}

    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )

    await query.message.reply_text(
        "Iltimos, telefon raqamingizni yuboring.\n"
        "Yoki quyidagicha kiriting:\n`+998901234567`",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# Обработка контакта
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    contact = update.message.contact
    phone = contact.phone_number

    if phone.startswith("998"):
        phone = "+" + phone
    elif not phone.startswith("+998"):
        await update.message.reply_text("❗️Faqat O'zbekiston raqamlari (+998). Iltimos, tekshiring.")
        return

    user_data[chat_id] = {'step': 2, 'phone': phone}

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚕 TAXI", callback_data="service_taxi"),
            InlineKeyboardButton("📦 POCHTA", callback_data="service_pochta")
        ]
    ])
    await update.message.reply_text("Xizmat turini tanlang:", reply_markup=keyboard)

# Выбор сервиса
async def select_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    service = "TAXI" if query.data == "service_taxi" else "POCHTA"
    user_data[chat_id]['service'] = service

    if service == "TAXI":
        user_data[chat_id]['step'] = 3
        people_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{i} kishi", callback_data=f"people_{i}")] for i in range(1, 6)
        ])
        await query.message.reply_text("Nechta odam ketadi?", reply_markup=people_keyboard)
    else:
        user_data[chat_id]['step'] = 4
        await query.message.reply_text("Manzilingizni kiriting:", reply_markup=ReplyKeyboardRemove())

# Выбор количества людей
async def select_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id

    count = int(query.data.split("_")[1])
    user_data[chat_id]['people'] = count
    user_data[chat_id]['step'] = 4

    await query.message.reply_text("Manzilingizni kiriting:", reply_markup=ReplyKeyboardRemove())

# Обработка номера телефона вручную и адреса
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = user_data.get(chat_id)

    if not state:
        return

    if state['step'] == 1:
        phone = update.message.text.strip()
        if not re.fullmatch(r"\+998\d{9}", phone):
            await update.message.reply_text(
                "❗️ Telefon raqam noto'g'ri. Quyidagicha kiriting:\n`+998901234567`",
                parse_mode="Markdown"
            )
            return

        user_data[chat_id] = {'step': 2, 'phone': phone}
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚕 TAXI", callback_data="service_taxi"),
             InlineKeyboardButton("📦 POCHTA", callback_data="service_pochta")]
        ])
        await update.message.reply_text("Xizmat turini tanlang:", reply_markup=keyboard)

    elif state['step'] == 4:
        state['address'] = update.message.text
        order_text = (
            f"🛺 Yangi buyurtma:\n"
            f"🚩 Xizmat: {state['service']}\n"
            f"📍 Manzil: {state['address']}\n"
            f"📞 Telefon: {state['phone']}\n"
            f"💬 Foydalanuvchi: @{update.message.from_user.username or update.message.from_user.first_name}"
        )
        if state['service'] == "TAXI":
            order_text += f"\n👥 Odamlar soni: {state['people']}"

        await context.bot.send_message(ADMIN_CHAT_ID, order_text)
        await update.message.reply_text("✅ Buyurtmangiz qabul qilindi! Tez orada operator siz bilan bog'lanadi.")

        # Сброс данных
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("TAXI CHAQIRISH 🚕", callback_data="order_taxi"),
                InlineKeyboardButton("TEZKOR 24/7🚕", web_app=WebAppInfo(url="https://taxi-prototip.vercel.app/"))
            ]
        ])
        await update.message.reply_text("Yana buyurtma bermoqchimisiz?", reply_markup=keyboard)

        user_data.pop(chat_id, None)

# MAIN
if __name__ == "__main__":
    app = ApplicationBuilder().token(API_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(order_taxi, pattern="^order_taxi$"))
    app.add_handler(CallbackQueryHandler(select_service, pattern="^service_"))
    app.add_handler(CallbackQueryHandler(select_people, pattern="^people_"))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print(f"Устанавливаю вебхук: {WEBHOOK_URL}")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=API_TOKEN,
        webhook_url=WEBHOOK_URL
    )
