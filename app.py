from flask import Flask, request
import telebot
import os
import json

# ⚠️ ضع التوكن الجديد هنا ⚠️
BOT_TOKEN = "8385331860:AAG8CjeP8QCaucgbWATrkrevY44c-ETmcQY"
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

print("🤖 Bot starting...")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    tr عنy:
        print(f"🎮 Start from: {message.from_user.id}")
        bot.reply_to(message, "🎉 **أهلاً! البوت شغال!**\n\nجرب /test", parse_mode='Markdown')
    except Exception as e:
        print(f"❌ Error: {e}")

@bot.message_handler(commands=['test'])
def send_test(message):
    try:
        print(f"🧪 Test from: {message.from_user.id}")
        bot.reply_to(message, "✅ **اختبار ناجح!**\nالبوت يرد!", parse_mode='Markdown')
    except Exception as e:
        print(f"❌ Error: {e}")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    try:
        print(f"💬 Message: {message.text}")
        bot.reply_to(message, f"📝 استلمت: {message.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return ''
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return 'ERROR'

@app.route('/')
def index():
    return "🤖 Bot is LIVE!"

@app.route('/setwebhook')
def set_webhook():
    try:
        bot.remove_webhook()
        url = f"https://{request.host}/{BOT_TOKEN}"
        bot.set_webhook(url=url)
        return f"✅ Webhook set to: {url}"
    except Exception as e:
        return f"❌ Error: {e}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Starting on port {port}")
    app.run(host='0.0.0.0', port=port)
