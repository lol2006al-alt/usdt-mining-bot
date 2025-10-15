from flask import Flask, request
import telebot
import os

# التوكن الصحيح
BOT_TOKEN = "8385331860:AAHj0uPnpJf_JYtHjALIkmavsBNnpa_Gd2Y"
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# المشرفين
ADMIN_IDS = [8400225549]

@bot.message_handler(commands=['start'])
def start_command(message):
    welcome_text = f"""
🎮 أهلاً وسهلاً {message.from_user.first_name}!

✅ البوت يعمل بنجاح
💰 جرب الأوامر الإدارية

/quickadd - إضافة رصيد
/test - فحص النظام
/myid - معرفك"""
    
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['test'])
def test_command(message):
    bot.reply_to(message, "✅ البوت يعمل! جرب /quickadd")

@bot.message_handler(commands=['myid'])
def myid_command(message):
    bot.reply_to(message, f"🆔 معرفك: `{message.from_user.id}`", parse_mode='Markdown')

@bot.message_handler(commands=['quickadd'])
def quickadd_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) == 3:
            user_id = int(parts[1])
            amount = float(parts[2])
            bot.reply_to(message, f"✅ تم إضافة {amount} USDT للمستخدم {user_id}")
        else:
            bot.reply_to(message, "❌ استخدم: /quickadd [user_id] [amount]")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['adduser'])
def adduser_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) >= 3:
            user_id = int(parts[1])
            balance = float(parts[2])
            referrals = int(parts[3]) if len(parts) > 3 else 0
            
            bot.reply_to(message, f"✅ تم إنشاء المستخدم {user_id}\n💰 الرصيد: {balance} USDT\n👥 الإحالات: {referrals}")
        else:
            bot.reply_to(message, "📝 استخدم: /adduser [user_id] [balance] [referrals]")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(func=lambda message: True)
def all_messages(message):
    bot.reply_to(message, f"📝 البوت يستقبل: {message.text}")

# نظام الصحة
@app.route('/health')
def health_check():
    return {"status": "healthy", "version": "1.0"}

@app.route('/')
def home():
    return "🤖 البوت يعمل بنجاح! استخدم /start في التليجرام"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

if __name__ == "__main__":
    print("🚀 بدأ تشغيل البوت...")
    try:
        # إعداد ويب هوك
        bot.remove_webhook()
        import time
        time.sleep(2)
        
        WEBHOOK_URL = f'https://usdt-bot-live.onrender.com/{BOT_TOKEN}'
        bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ Webhook مضبوط: {WEBHOOK_URL}")
        
        # تشغيل الخادم
        PORT = int(os.environ.get('PORT', 10000))
        print(f"🌐 الخادم يعمل على المنفذ {PORT}")
        app.run(host='0.0.0.0', port=PORT, debug=False)
        
    except Exception as e:
        print(f"❌ خطأ في التشغيل: {e}")
