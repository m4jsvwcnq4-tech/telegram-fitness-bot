import telebot
from telebot import types
from flask import Flask, request, jsonify
import json
import os
from datetime import date
import logging

# ========= НАСТРОЙКА ЛОГИРОВАНИЯ =========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========= ENV =========
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Проверка переменных окружения
if not TOKEN:
    logger.error("❌ TOKEN не задан в переменных окружения")
if not ADMIN_ID:
    logger.error("❌ ADMIN_ID не задан в переменных окружения")
if not CHANNEL_ID:
    logger.error("❌ CHANNEL_ID не задан в переменных окружения")

try:
    ADMIN_ID = int(ADMIN_ID) if ADMIN_ID else 0
except:
    ADMIN_ID = 0

DATA_FILE = "users_data.json"

# ========= BOT / APP =========
bot = telebot.TeleBot(TOKEN) if TOKEN else None
app = Flask(__name__)

# ========= DATA =========
def today():
    return date.today().isoformat()

def load_data():
    """Загружает данные пользователей из файла"""
    try:
        if not os.path.exists(DATA_FILE):
            return {}
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        return {}

def save_data():
    """Сохраняет данные пользователей в файл"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")

users_data = load_data()

def get_user(uid: int):
    """Получает или создает данные пользователя"""
    uid_str = str(uid)
    
    if uid_str not in users_data:
        users_data[uid_str] = {
            "total": {"pushups": 0, "abs": 0, "plank": 0},
            "daily": {"date": today(), "pushups": 0, "abs": 0, "plank": 0}
        }
    
    # Сброс дневной статистики если новый день
    if users_data[uid_str]["daily"]["date"] != today():
        users_data[uid_str]["daily"] = {
            "date": today(),
            "pushups": 0,
            "abs": 0,
            "plank": 0
        }
    
    return users_data[uid_str]

# ========= KEYBOARDS =========
def main_keyboard(is_admin=False):
    """Создает основную клавиатуру"""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📊 Сегодня", "📈 Всё время")
    kb.row("🔄 Сбросить день")
    if is_admin:
        kb.row("🔁 Перезапуск")
    return kb

# ========= WEBHOOK ROUTES (для Railway) =========
@app.route("/")
def index():
    """Главная страница для проверки работы"""
    return jsonify({
        "status": "running",
        "service": "Telegram Fitness Bot",
        "endpoints": ["/", "/health", "/set_webhook", "/webhook"]
    }), 200

@app.route("/health")
def health():
    """Healthcheck для Railway"""
    if not TOKEN:
        return jsonify({"status": "error", "message": "TOKEN not set"}), 500
    if not bot:
        return jsonify({"status": "error", "message": "Bot not initialized"}), 500
    return jsonify({"status": "healthy"}), 200

@app.route("/set_webhook", methods=["GET"])
def set_webhook_route():
    """Устанавливает вебхук для Telegram"""
    if not bot:
        return "❌ Бот не инициализирован. Проверьте TOKEN.", 400
    
    try:
        # Получаем текущий домен
        webhook_url = os.getenv("RAILWAY_STATIC_URL") or f"https://{request.host}"
        full_url = f"{webhook_url}/webhook"
        
        # Удаляем старый вебхук и устанавливаем новый
        bot.remove_webhook()
        result = bot.set_webhook(url=full_url)
        
        logger.info(f"Webhook установлен: {full_url}")
        return f"""
        ✅ Вебхук установлен!
        <br><br>
        <b>URL:</b> {full_url}
        <br><br>
        <b>Результат:</b> {result}
        <br><br>
        <a href="https://api.telegram.org/bot{TOKEN}/getWebhookInfo">Проверить статус</a>
        """, 200
    except Exception as e:
        logger.error(f"Ошибка установки вебхука: {e}")
        return f"❌ Ошибка: {str(e)}", 500

@app.route("/webhook", methods=["POST"])
def webhook():
    """Основной endpoint для вебхука от Telegram"""
    if not bot:
        return "Bot not initialized", 400
    
    if request.headers.get('content-type') == 'application/json':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return 'OK', 200
        except Exception as e:
            logger.error(f"Ошибка обработки вебхука: {e}")
            return f"Error: {str(e)}", 400
    else:
        return 'Bad Request', 400

# ========= TELEGRAM HANDLERS =========
@bot.message_handler(commands=["start", "help"])
def start_handler(message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    get_user(user_id)
    save_data()
    
    is_admin = (user_id == ADMIN_ID)
    
    bot.send_message(
        message.chat.id,
        "💪 <b>Фитнес-трекер</b>\n\n"
        "Отправляйте результаты в формате:\n"
        "<code>отжимания пресс планка</code>\n\n"
        "<b>Пример:</b> <code>20 30 2</code>\n\n"
        "Используйте кнопки ниже для просмотра статистики.",
        parse_mode="HTML",
        reply_markup=main_keyboard(is_admin)
    )

@bot.message_handler(func=lambda m: m.text == "📊 Сегодня")
def today_stats_handler(message):
    """Показывает статистику за сегодня"""
    user = get_user(message.from_user.id)
    daily = user["daily"]
    
    response = (
        f"📊 <b>Сегодня</b> ({daily['date']}):\n\n"
        f"💪 Отжимания: <b>{daily['pushups']}</b>\n"
        f"🏋️ Пресс: <b>{daily['abs']}</b>\n"
        f"⏱ Планка: <b>{daily['plank']} мин</b>"
    )
    
    bot.send_message(message.chat.id, response, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📈 Всё время")
def total_stats_handler(message):
    """Показывает общую статистику"""
    user = get_user(message.from_user.id)
    total = user["total"]
    
    response = (
        f"📈 <b>Всё время</b>:\n\n"
        f"💪 Отжимания: <b>{total['pushups']}</b>\n"
        f"🏋️ Пресс: <b>{total['abs']}</b>\n"
        f"⏱ Планка: <b>{total['plank']} мин</b>"
    )
    
    bot.send_message(message.chat.id, response, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🔄 Сбросить день")
def reset_day_handler(message):
    """Сбрасывает дневную статистику"""
    user = get_user(message.from_user.id)
    user["daily"] = {
        "date": today(),
        "pushups": 0,
        "abs": 0,
        "plank": 0
    }
    save_data()
    
    bot.send_message(
        message.chat.id,
        "✅ Дневная статистика сброшена!",
        reply_markup=main_keyboard(message.from_user.id == ADMIN_ID)
    )

@bot.message_handler(func=lambda m: m.text == "🔁 Перезапуск")
def restart_handler(message):
    """Перезапуск бота (только для админа)"""
    if message.from_user.id == ADMIN_ID:
        bot.send_message(
            message.chat.id,
            "♻️ Бот будет перезапущен через Railway...\n"
            "Это может занять несколько секунд."
        )
        # В Railway перезапуск происходит автоматически при деплое
    else:
        bot.send_message(message.chat.id, "⛔ Эта команда только для администратора.")

@bot.message_handler(func=lambda m: True)
def numbers_handler(message):
    """Обработчик числовых данных: отжимания пресс планка"""
    try:
        # Пытаемся распарсить три числа
        parts = message.text.split()
        if len(parts) != 3:
            return  # Неправильный формат, игнорируем
        
        pushups, abs_count, plank = map(int, parts)
        
        # Получаем пользователя и обновляем статистику
        user = get_user(message.from_user.id)
        user["daily"]["pushups"] += pushups
        user["daily"]["abs"] += abs_count
        user["daily"]["plank"] += plank
        
        user["total"]["pushups"] += pushups
        user["total"]["abs"] += abs_count
        user["total"]["plank"] += plank
        
        save_data()
        
        # Отправляем подтверждение пользователю
        response = (
            f"✅ <b>Добавлено:</b>\n\n"
            f"💪 Отжимания: +{pushups}\n"
            f"🏋️ Пресс: +{abs_count}\n"
            f"⏱ Планка: +{plank} мин\n\n"
            f"<i>Используйте кнопки для просмотра статистики.</i>"
        )
        
        bot.send_message(
            message.chat.id,
            response,
            parse_mode="HTML",
            reply_markup=main_keyboard(message.from_user.id == ADMIN_ID)
        )
        
        # Отправляем в канал (если настроен)
        if CHANNEL_ID and bot:
            try:
                channel_msg = (
                    f"🏋️ <b>Новая запись</b>\n\n"
                    f"👤 Пользователь: {message.from_user.first_name}\n"
                    f"💪 Отжимания: {pushups}\n"
                    f"🏋️ Пресс: {abs_count}\n"
                    f"⏱ Планка: {plank} мин"
                )
                bot.send_message(CHANNEL_ID, channel_msg, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Ошибка отправки в канал: {e}")
                
    except (ValueError, TypeError):
        # Неправильный формат данных
        pass
    except Exception as e:
        logger.error(f"Ошибка обработки чисел: {e}")

# ========= ОБРАБОТКА ОШИБОК =========
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# ========= ЗАПУСК ПРИЛОЖЕНИЯ =========
# НЕ добавляйте app.run() - Railway использует gunicorn
# Весь запуск через railway.json
