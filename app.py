from flask import Flask, request
import telebot
import os
import logging

# الأساسيات
BOT_TOKEN = "8385331860:AAEcFqGY4vXORINuGUH6XpmSN9-FtluEMj8"
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

# المشرفين
ADMIN_IDS = [8400225549]

# الأوامر الأساسية
@bot.message_handler(commands=['start'])
def start_command(message):
    welcome = f"""🎮 أهلاً {message.from_user.first_name}!

✅ البوت يعمل بنجاح
💰 جرب الأوامر الإدارية

/quickadd - إضافة رصيد
/testpostgres - فحص النظام"""
    
    bot.reply_to(message, welcome)

@bot.message_handler(commands=['testpostgres'])
def test_postgres(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    bot.reply_to(message, "✅ البوت يستقبل الأوامر! جرب /quickadd")

@bot.message_handler(commands=['quickadd'])
def quick_add(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) == 3:
            user_id = int(parts[1])
            amount = float(parts[2])
            bot.reply_to(message, f"✅ (تجريبي) تم إضافة {amount} USDT للمستخدم {user_id}")
        else:
            bot.reply_to(message, "❌ استخدم: /quickadd [user_id] [amount]")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(func=lambda message: True)
def all_messages(message):
    logging.info(f"📨 رسالة: {message.text}")
    bot.reply_to(message, f"🔍 البوت يستقبل: {message.text}")

# نظام الصحة
@app.route('/health')
def health_check():
    return {"status": "healthy", "version": "2.0"}

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

if __name__ == "__main__":
    print("🚀 البوت يعمل...")
    bot.remove_webhook()
    import time
    time.sleep(2)
    bot.set_webhook(f'https://usdt-bot-working.onrender.com/{BOT_TOKEN}')
    app.run(host='0.0.0.0', port=10000)
