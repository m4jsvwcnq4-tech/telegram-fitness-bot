import os
import telebot
from telebot import types
from flask import Flask, request
import json
from datetime import date

# ========= НАСТРОЙКИ =========
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID", "0")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

try:
    ADMIN_ID = int(ADMIN_ID)
except:
    ADMIN_ID = 0

# ========= БОТ И ПРИЛОЖЕНИЕ =========
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ========= ХРАНЕНИЕ ДАННЫХ =========
DATA_FILE = "users.json"
users = {}

def load_data():
    global users
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
    except:
        users = {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

load_data()

def get_user(user_id):
    user_id = str(user_id)
    today_str = date.today().isoformat()
    
    if user_id not in users:
        users[user_id] = {
            "total": {"pushups": 0, "abs": 0, "plank": 0},
            "daily": {"date": today_str, "pushups": 0, "abs": 0, "plank": 0}
        }
    
    if users[user_id]["daily"]["date"] != today_str:
        users[user_id]["daily"] = {
            "date": today_str,
            "pushups": 0,
            "abs": 0,
            "plank": 0
        }
    
    return users[user_id]

# ========= КЛАВИАТУРА =========
def main_keyboard(is_admin=False):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("📊 Сегодня", "📈 Все время")
    keyboard.row("🔄 Сбросить день")
    if is_admin:
        keyboard.row("🔁 Перезапуск")
    return keyboard

# ========= ВЕБХУК ДЛЯ RENDER =========
@app.route('/')
def home():
    return '✅ Фитнес-бот работает!', 200

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = f'https://{request.host}/webhook'
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f'✅ Вебхук установлен: {webhook_url}', 200

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Bad Request', 400

# ========= КОМАНДЫ БОТА =========
@bot.message_handler(commands=['start', 'help'])
def start_command(message):
    get_user(message.from_user.id)
    save_data()
    
    bot.send_message(
        message.chat.id,
        "💪 *Фитнес-трекер*\n\n"
        "Отправьте: *отжимания пресс планка*\n"
        "Пример: *20 30 2*\n\n"
        "Используйте кнопки ниже ↓",
        parse_mode="Markdown",
        reply_markup=main_keyboard(message.from_user.id == ADMIN_ID)
    )

@bot.message_handler(func=lambda m: m.text == "📊 Сегодня")
def today_stats(message):
    user = get_user(message.from_user.id)
    daily = user["daily"]
    
    text = (
        f"📊 *Сегодня ({daily['date']}):*\n\n"
        f"💪 Отжимания: *{daily['pushups']}*\n"
        f"🏋️ Пресс: *{daily['abs']}*\n"
        f"⏱ Планка: *{daily['plank']}* мин"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📈 Все время")
def total_stats(message):
    user = get_user(message.from_user.id)
    total = user["total"]
    
    text = (
        f"📈 *Все время:*\n\n"
        f"💪 Отжимания: *{total['pushups']}*\n"
        f"🏋️ Пресс: *{total['abs']}*\n"
        f"⏱ Планка: *{total['plank']}* мин"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔄 Сбросить день")
def reset_day(message):
    user = get_user(message.from_user.id)
    user["daily"] = {
        "date": date.today().isoformat(),
        "pushups": 0,
        "abs": 0,
        "plank": 0
    }
    save_data()
    bot.send_message(message.chat.id, "✅ День сброшен!")

@bot.message_handler(func=lambda m: m.text == "🔁 Перезапуск")
def restart_bot(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "♻️ Бот перезапускается...")
    else:
        bot.send_message(message.chat.id, "⛔ Нет доступа")

@bot.message_handler(func=lambda m: True)
def handle_numbers(message):
    try:
        a, b, c = map(int, message.text.split())
        
        user = get_user(message.from_user.id)
        user["daily"]["pushups"] += a
        user["daily"]["abs"] += b
        user["daily"]["plank"] += c
        
        user["total"]["pushups"] += a
        user["total"]["abs"] += b
        user["total"]["plank"] += c
        
        save_data()
        
        # Ответ пользователю
        response = (
            f"✅ *Добавлено:*\n\n"
            f"💪 Отжимания: *+{a}*\n"
            f"🏋️ Пресс: *+{b}*\n"
            f"⏱ Планка: *+{c}* мин\n\n"
            f"_Используйте кнопки для статистики_"
        )
        bot.send_message(
            message.chat.id, 
            response, 
            parse_mode="Markdown",
            reply_markup=main_keyboard(message.from_user.id == ADMIN_ID)
        )
        
        # Отправка в канал
        if CHANNEL_ID:
            try:
                channel_msg = (
                    f"🏋️ *Новая запись*\n\n"
                    f"👤 {message.from_user.first_name}\n"
                    f"💪 {a} отжиманий\n"
                    f"🏋️ {b} пресса\n"
                    f"⏱ {c} мин планки"
                )
                bot.send_message(CHANNEL_ID, channel_msg, parse_mode="Markdown")
            except:
                pass
                
    except:
        pass

# ========= ЗАПУСК =========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
