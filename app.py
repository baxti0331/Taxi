import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from flask import Flask, request, abort

API_TOKEN = os.getenv('API_TOKEN')
if not API_TOKEN:
    raise RuntimeError("Ошибка: переменная окружения API_TOKEN не установлена")

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

clean_token = API_TOKEN.replace(':', '')
WEBHOOK_URL_BASE = 'https://taxi-w5ww.onrender.com'  # ОБЯЗАТЕЛЬНО проверьте!
WEBHOOK_URL_PATH = f"/{clean_token}/"

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
    web_app_url = "https://findly-bird.vercel.app/"

    web_app_button = InlineKeyboardButton(
        text="PLAY🕹️",
        web_app=WebAppInfo(url=web_app_url)
    )
    markup.add(web_app_button)

    bot.send_message(message.chat.id, "Assalome Aleykum Xurmatli mijoz TEZKOR TAXI Xizmatiga Xush Kelibsz TAXI Buyurtma Berish uchun Pastdagi tugmani bosing!:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "button_click")
def callback_button(call):
    bot.answer_callback_query(call.id, "Ты нажал кнопку!")
    bot.send_message(call.message.chat.id, "Спасибо за нажатие!")

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