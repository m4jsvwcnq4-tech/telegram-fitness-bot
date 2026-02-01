import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return '✅ Фитнес-бот работает!', 200

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/test')
def test():
    return 'Тест пройден', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
