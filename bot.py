import os
from flask import Flask, request
import telebot

app = Flask(__name__)

# Инициализируем бота (токен возьмем из переменных окружения)
TOKEN = os.getenv("TOKEN")
if TOKEN:
    bot = telebot.TeleBot(TOKEN)
else:
    bot = None

# Healthcheck для Railway
@app.route("/")
def index():
    return "✅ Бот работает!", 200

@app.route("/health")
def health():
    return "OK", 200

# Простой вебхук для проверки
@app.route("/webhook", methods=["POST"])
def webhook():
    if bot:
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return "OK", 200
        except Exception as e:
            return f"Error: {str(e)}", 400
    return "Bot not initialized", 400

@app.route("/set_webhook")
def set_webhook():
    if bot:
        webhook_url = f"https://{request.host}/webhook"
        bot.remove_webhook()
        result = bot.set_webhook(url=webhook_url)
        return f"Webhook set to {webhook_url}<br>Result: {result}", 200
    return "Bot not initialized", 400
