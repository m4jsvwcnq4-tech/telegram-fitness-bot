import telebot
from telebot import types
from flask import Flask, request
import json
import os
from datetime import date

# ========= ENV =========

TOKEN = os.getenv("8516625902:AAGJ6FsLVFS3ewX95b26RyI7tA0dMMkA9Zc")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = os.getenv("-1003796059377")

DATA_FILE = "users_data.json"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ========= DATA =========

def today():
    return date.today().isoformat()

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users_data, f, ensure_ascii=False, indent=2)

users_data = load_data()

def get_user(uid):
    if uid not in users_data:
        users_data[uid] = {
            "total": {"pushups": 0, "abs": 0, "plank": 0},
            "daily": {"date": today(), "pushups": 0, "abs": 0, "plank": 0}
        }

    if users_data[uid]["daily"]["date"] != today():
        users_data[uid]["daily"] = {
            "date": today(),
            "pushups": 0,
            "abs": 0,
            "plank": 0
        }

    return users_data[uid]

# ========= KEYBOARDS =========

def main_keyboard(is_admin=False):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📊 Сегодня", "📈 Всё время")
    kb.row("🔄 Сбросить день")
    if is_admin:
        kb.row("🔁 Перезапуск")
    return kb

# ========= WEBHOOK =========

@app.route("/", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(
        request.stream.read().decode("utf-8")
    )
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/set")
def set_webhook():
    url = request.url_root
    bot.remove_webhook()
    bot.set_webhook(url=url)
    return "Webhook установлен ✅"

# ========= HANDLERS =========

@bot.message_handler(commands=["start"])
def start(m):
    get_user(str(m.from_user.id))
    save_data()
    bot.send_message(
        m.chat.id,
        "💪 Формат: отжимания пресс планка\nПример: 20 30 2",
        reply_markup=main_keyboard(m.from_user.id == ADMIN_ID)
    )

@bot.message_handler(func=lambda m: m.text == "📊 Сегодня")
def today_stats(m):
    u = get_user(str(m.from_user.id))["daily"]
    bot.send_message(m.chat.id,
        f"📊 Сегодня:\n"
        f"💪 {u['pushups']}\n"
        f"🏋️ {u['abs']}\n"
        f"⏱ {u['plank']} мин"
    )

@bot.message_handler(func=lambda m: m.text == "📈 Всё время")
def total_stats(m):
    u = get_user(str(m.from_user.id))["total"]
    bot.send_message(m.chat.id,
        f"📈 Всё время:\n"
        f"💪 {u['pushups']}\n"
        f"🏋️ {u['abs']}\n"
        f"⏱ {u['plank']} мин"
    )

@bot.message_handler(func=lambda m: m.text == "🔄 Сбросить день")
def reset_day(m):
    users_data[str(m.from_user.id)]["daily"] = {
        "date": today(), "pushups": 0, "abs": 0, "plank": 0
    }
    save_data()
    bot.send_message(m.chat.id, "✅ День сброшен")

@bot.message_handler(func=lambda m: m.text == "🔁 Перезапуск")
def restart(m):
    if m.from_user.id == ADMIN_ID:
        bot.send_message(m.chat.id, "♻️ Railway перезапустит сервис автоматически")

@bot.message_handler(func=lambda m: True)
def numbers(m):
    try:
        p, a, pl = map(int, m.text.split())
    except:
        return

    user = get_user(str(m.from_user.id))
    for k, v in zip(("pushups", "abs", "plank"), (p, a, pl)):
        user["daily"][k] += v
        user["total"][k] += v

    save_data()

    text = f"💪 Отчёт:\n{p} / {a} / {pl}"
    bot.send_message(m.chat.id, text)
    bot.send_message(CHANNEL_ID, text)

# ========= START =========

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
