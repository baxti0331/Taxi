import os
import re
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from flask import Flask, request, abort

API_TOKEN = os.getenv('API_TOKEN')
if not API_TOKEN:
    raise RuntimeError("Ошибка: переменная окружения API_TOKEN не установлена")

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

clean_token = API_TOKEN.replace(':', '')
WEBHOOK_URL_BASE = 'https://taxi-w5ww.onrender.com'  # Проверь адрес!
WEBHOOK_URL_PATH = f"/{clean_token}/"

user_data = {}  # Хранение состояния диалога
ADMIN_CHAT_ID = -1002886954464  # Заменить на ID группы или админа

@app.route('/', methods=['GET'])
def index():
    return "Бот запущен и готов к работе!"

@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()

    web_app_url = "https://taxi-prototip.vercel.app/"

    web_app_button = InlineKeyboardButton(
        text="TEZKOR 24/7🚕",
        web_app=WebAppInfo(url=web_app_url)
    )

    order_button = InlineKeyboardButton(
        text="TAXI CHAQIRISH 🚕",
        callback_data="order_taxi"
    )

    markup.add(order_button)
    markup.add(web_app_button)

    bot.send_message(message.chat.id,
        "Assalome Aleykum, Xurmatli mijoz!\nTAXI buyurtma berish uchun quyidagi tugmalardan foydalaning:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "order_taxi")
def start_order(call):
    chat_id = call.message.chat.id
    user_data[chat_id] = {'step': 1}
    bot.answer_callback_query(call.id)

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    phone_button = KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
    keyboard.add(phone_button)

    bot.send_message(chat_id,
        "Iltimos, telefon raqamingizni yuboring.\n"
        "Agar yuqoridagi tugma ishlamasa, raqamni qo'lda quyidagi shaklda kiriting:\n"
        "`+998901234567`",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    chat_id = message.chat.id
    if chat_id not in user_data or user_data[chat_id].get('step') != 1:
        return

    contact = message.contact
    phone = contact.phone_number

    if phone.startswith('998'):
        phone = '+' + phone
    elif not phone.startswith('+998'):
        bot.send_message(chat_id, "❗️Faqat O'zbekiston raqamlari qabul qilinadi (+998). Iltimos, raqamni tekshiring.")
        return

    user_data[chat_id]['phone'] = phone
    user_data[chat_id]['step'] = 2

    bot.send_message(chat_id, "Manzilingizni kiriting:", reply_markup=ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: message.chat.id in user_data)
def process_order(message):
    chat_id = message.chat.id
    state = user_data.get(chat_id)

    if state['step'] == 1:
        phone = message.text.strip()

        if not re.fullmatch(r"\+998\d{9}", phone):
            bot.send_message(chat_id,
                "❗️ Telefon raqam noto'g'ri. Raqamni quyidagicha kiriting:\n"
                "`+998901234567`",
                parse_mode='Markdown'
            )
            return

        state['phone'] = phone
        state['step'] = 2
        bot.send_message(chat_id, "Manzilingizni kiriting:", reply_markup=ReplyKeyboardRemove())

    elif state['step'] == 2:
        state['address'] = message.text
        state['step'] = 3
        bot.send_message(chat_id, "Nechta odam ketadi?")

    elif state['step'] == 3:
        state['people'] = message.text
elif state['step'] == 3:
    if message.text.isdigit():
        state['people'] = int(message.text)
        state['step'] = 4
        bot.send_message(chat_id, "Buyurtma qabul qilindi! Rahmat!")
    else:
        bot.send_message(chat_id, "Iltimos, faqat son kiriting. Nechta odam ketadi?")

elif state['step'] == 3:
    if message.text.isdigit():
        state['people'] = int(message.text)
        state['step'] = 4
        bot.send_message(chat_id, "Buyurtma qabul qilindi! Rahmat!")
        # Здесь можно продолжить логику оформления заказа
    else:
        bot.send_message(chat_id, "Iltimos, faqat son kiriting. Nechta odam ketadi?")
elif state['step'] == 3:
    if message.text.isdigit():
        state['people'] = int(message.text)
        state['step'] = 4
        bot.send_message(chat_id, "Buyurtma qabul qilindi! Rahmat!")
        # Здесь можно продолжить логику оформления заказа
    else:
        bot.send_message(chat_id, "Iltimos, faqat son kiriting. Nechta odam ketadi?")

        order_text = (
            f"🛺 Yangi TAXI buyurtma:\n"
            f"📍 Manzil: {state['address']}\n"
            f"👥 Odamlar soni: {state['people']}\n"
            f"📞 Telefon: {state['phone']}\n"
            f"💬 Foydalanuvchi: @{message.from_user.username or message.from_user.first_name}"
        )

        bot.send_message(ADMIN_CHAT_ID, order_text)
        bot.send_message(chat_id, "✅ Buyurtmangiz qabul qilindi! Tez orada operator siz bilan bog'lanadi.")
        user_data.pop(chat_id)

if __name__ == '__main__':
    print("Удаляю старый вебхук...")
    bot.remove_webhook()
    print("Устанавливаю новый вебхук...")
    success = bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)
    if success:
        print(f"Вебхук успешно установлен: {WEBHOOK_URL_BASE + WEBHOOK_URL_PATH}")
    else:
        print("Ошибка при установке вебхука.")

    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)