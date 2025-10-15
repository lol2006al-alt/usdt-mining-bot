from flask import Flask, request
import telebot
import os

BOT_TOKEN = "8385331860:AAEcFqGY4vXORINuGUH6XpmSN9-FtluEMj8"
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚀 البوت يعمل! جرب /quickadd")

@bot.message_handler(commands=['quickadd'])
def quickadd(message):
    bot.reply_to(message, "✅ أمر quickadd جاهز - تحت التطوير")

@bot.message_handler(func=lambda message: True)
def all_messages(message):
    bot.reply_to(message, f"📝 البوت يستقبل: {message.text}")

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(f'https://usdt-bot-final.onrender.com/{BOT_TOKEN}')
    app.run(host='0.0.0.0', port=10000)
