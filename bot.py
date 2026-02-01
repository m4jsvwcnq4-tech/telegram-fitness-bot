import telebot
from telebot import types
from flask import Flask, request, jsonify
import json
import os
from datetime import date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not TOKEN:
    logger.error("TOKEN не задан")

try:
    ADMIN_ID = int(ADMIN_ID) if ADMIN_ID else 0
except:
    ADMIN_ID = 0

DATA_FILE = "users_data.json"
bot = telebot.TeleBot(TOKEN) if TOKEN else None
app = Flask(__name__)

def today():
    return date.today().isoformat()

def load_data():
    try:
        if not os.path.exists(DATA_FILE):
            return {}
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки: {e}")
        return {}

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения: {e}")

users_data = load_data()

def get_user(uid: int):
    uid_str = str(uid)
    
    if uid_str not in users_data:
        users_data[uid_str] = {
            "total": {"pushups": 0, "abs": 0, "plank": 0},
            "daily": {"date": today(), "pushups": 0, "abs": 0, "plank": 0}
        }
    
    if users_data[uid_str]["daily"]["date"] != today():
        users_data[uid_str]["daily"] = {
            "date": today(),
            "pushups": 0,
            "abs": 0,
            "plank": 0
        }
    
    return users_data[uid_str]

def main_keyboard(is_admin=False):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📊 Сегодня", "📈 Всё время")
    kb.row("🔄 Сбросить день")
    if is_admin:
        kb.row("🔁 Перезапуск")
    return kb

@app.route("/")
def index():
    return jsonify({"status": "running", "service": "Telegram Fitness Bot"}), 200

@app.route("/health")
def health():
    if not TOKEN:
        return jsonify({"status": "error", "message": "TOKEN not set"}), 500
    return jsonify({"status": "healthy"}), 200

@app.route("/set_webhook", methods=["GET"])
def set_webhook_route():
    if not bot:
        return "Бот не инициализирован", 400
    
    try:
        webhook_url = os.getenv("RAILWAY_STATIC_URL") or f"https://{request.host}"
        full_url = f"{webhook_url}/webhook"
        
        bot.remove_webhook()
        result = bot.set_webhook(url=full_url)
        
        logger.info(f"Webhook установлен: {full_url}")
        return f"Webhook установлен на {full_url}<br>Результат: {result}", 200
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return f"Ошибка: {str(e)}", 500

@app.route("/webhook", methods=["POST"])
def webhook():
    if not bot:
        return "Bot not initialized", 400
    
    if request.headers.get('content-type') == 'application/json':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return 'OK', 200
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return f"Error: {str(e)}", 400
    return 'Bad Request', 400

@bot.message_handler(commands=["start", "help"])
def start_handler(message):
    user_id = message.from_user.id
    get_user(user_id)
    save_data()
    
    is_admin = (user_id == ADMIN_ID)
    
    bot.send_message(
        message.chat.id,
        "💪 Фитнес-трекер\n\nОтправляйте: отжимания пресс планка\nПример: 20 30 2\n\nИспользуйте кнопки:",
        parse_mode="HTML",
        reply_markup=main_keyboard(is_admin)
    )

@bot.message_handler(func=lambda m: m.text == "📊 Сегодня")
def today_stats_handler(message):
    user = get_user(message.from_user.id)
    daily = user["daily"]
    
    response = f"📊 Сегодня ({daily['date']}):\n💪 {daily['pushups']}\n🏋️ {daily['abs']}\n⏱ {daily['plank']} мин"
    bot.send_message(message.chat.id, response, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📈 Всё время")
def total_stats_handler(message):
    user = get_user(message.from_user.id)
    total = user["total"]
    
    response = f"📈 Всё время:\n💪 {total['pushups']}\n🏋️ {total['abs']}\n⏱ {total['plank']} мин"
    bot.send_message(message.chat.id, response, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🔄 Сбросить день")
def reset_day_handler(message):
    user = get_user(message.from_user.id)
    user["daily"] = {"date": today(), "pushups": 0, "abs": 0, "plank": 0}
    save_data()
    
    bot.send_message(message.chat.id, "✅ День сброшен")

@bot.message_handler(func=lambda m: m.text == "🔁 Перезапуск")
def restart_handler(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "♻️ Перезапуск...")
    else:
        bot.send_message(message.chat.id, "⛔ Только для админа")

@bot.message_handler(func=lambda m: True)
def numbers_handler(message):
    try:
        parts = message.text.split()
        if len(parts) != 3:
            return
        
        pushups, abs_count, plank = map(int, parts)
        
        user = get_user(message.from_user.id)
        user["daily"]["pushups"] += pushups
        user["daily"]["abs"] += abs_count
        user["daily"]["plank"] += plank
        
        user["total"]["pushups"] += pushups
        user["total"]["abs"] += abs_count
        user["total"]["plank"] += plank
        
        save_data()
        
        response = f"✅ Добавлено:\n💪 +{pushups}\n🏋️ +{abs_count}\n⏱ +{plank} мин"
        bot.send_message(message.chat.id, response, parse_mode="HTML")
        
        if CHANNEL_ID and bot:
            try:
                channel_msg = f"🏋️ Новая запись\n👤 {message.from_user.first_name}\n💪 {pushups}\n🏋️ {abs_count}\n⏱ {plank} мин"
                bot.send_message(CHANNEL_ID, channel_msg, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Ошибка канала: {e}")
                
    except (ValueError, TypeError):
        pass
    except Exception as e:
        logger.error(f"Ошибка чисел: {e}")

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500
