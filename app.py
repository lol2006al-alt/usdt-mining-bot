from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json
from datetime import datetime

# التوكن من Environment Variable
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8385331860:AAEcFqGY4vXORINuGUH6XpmSN9-FtluEMj8")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# المشرفين
ADMIN_IDS = [8400225549]

# تخزين المستخدمين في الذاكرة (مؤقت)
users_db = {}
backups_db = []

# 🔧 دوال مساعدة
def get_user(user_id):
    return users_db.get(user_id)

def save_user(user_data):
    users_db[user_data['user_id']] = user_data
    return True

def add_balance(user_id, amount, description="", is_deposit=False):
    user = get_user(user_id)
    if not user:
        user = {
            'user_id': user_id,
            'balance': 0.0,
            'total_earned': 0.0,
            'total_deposits': 0.0,
            'referrals_count': 0
        }
    
    user['balance'] += amount
    user['total_earned'] += amount
    if is_deposit:
        user['total_deposits'] += amount
    
    return save_user(user)

# 🛠️ الأوامر الإدارية
@bot.message_handler(commands=['quickadd'])
def quick_add_balance(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /quickadd [user_id] [amount]")
            return
        
        target_user_id = int(parts[1])
        amount = float(parts[2])
        
        if add_balance(target_user_id, amount, "إضافة إدارية", True):
            user = get_user(target_user_id)
            bot.reply_to(message, f"✅ تم إضافة {amount} USDT للمستخدم {target_user_id}\n💰 الرصيد الجديد: {user['balance']:.1f} USDT")
        else:
            bot.reply_to(message, "❌ فشل في إضافة الرصيد")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['adduser'])
def add_user_complete(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "📝 استخدم: /adduser [user_id] [balance] [referrals] [vip_level]")
            return
        
        user_id = int(parts[1])
        balance = float(parts[2])
        referrals = int(parts[3]) if len(parts) > 3 else 0
        vip_level = int(parts[4]) if len(parts) > 4 else 0
        
        user_data = {
            'user_id': user_id,
            'balance': balance,
            'referrals_count': referrals,
            'vip_level': vip_level,
            'total_deposits': balance,
            'total_earned': balance,
            'total_games_played': referrals * 10
        }
        
        if save_user(user_data):
            bot.reply_to(message, f"✅ تم إضافة المستخدم {user_id}\n💰 الرصيد: {balance} USDT\n👥 الإحالات: {referrals}\n💎 VIP: {vip_level}")
        else:
            bot.reply_to(message, "❌ فشل في إضافة المستخدم")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['userfullinfo'])
def user_full_info(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ استخدم: /userfullinfo [user_id]")
            return
        
        user_id = int(parts[1])
        user = get_user(user_id)
        
        if user:
            info_text = f"""
📊 معلومات المستخدم:

🆔 الآيدي: {user['user_id']}
💰 الرصيد: {user.get('balance', 0):.1f} USDT
💳 الإيداعات: {user.get('total_deposits', 0):.1f} USDT
🏆 الأرباح: {user.get('total_earned', 0):.1f} USDT
👥 الإحالات: {user.get('referrals_count', 0)}
💎 VIP: {user.get('vip_level', 0)}
🎮 الألعاب: {user.get('total_games_played', 0)}
"""
            bot.reply_to(message, info_text)
        else:
            bot.reply_to(message, "❌ المستخدم غير موجود!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['manualbackup'])
def manual_backup(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'users_count': len(users_db),
            'users': users_db
        }
        backups_db.append(backup_data)
        bot.reply_to(message, f"✅ تم إنشاء نسخة احتياطية: {len(users_db)} مستخدم")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['listbackups'])
def list_backups(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        if backups_db:
            response = f"📂 النسخ الاحتياطية: {len(backups_db)}\n"
            for i, backup in enumerate(backups_db[-5:], 1):
                response += f"{i}. {backup['timestamp']} - {backup['users_count']} مستخدم\n"
        else:
            response = "❌ لا توجد نسخ احتياطية"
        bot.reply_to(message, response)
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# 🎯 الأوامر الأساسية
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        user_data = {
            'user_id': user_id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'balance': 0.0,
            'referrals_count': 0,
            'total_deposits': 0.0,
            'total_earned': 0.0,
            'vip_level': 0
        }
        save_user(user_data)
        user = user_data
    
    welcome_text = f"""
🎮 أهلاً {message.from_user.first_name}!

💰 رصيدك: {user['balance']:.1f} USDT
👥 إحالاتك: {user['referrals_count']}
💎 مستوى VIP: {user['vip_level']}

🚀 البوت يعمل بنجاح!"""
    
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['test'])
def test_command(message):
    bot.reply_to(message, "✅ البوت يعمل! جرب الأوامر الإدارية")

@bot.message_handler(commands=['myid'])
def myid_command(message):
    bot.reply_to(message, f"🆔 معرفك: `{message.from_user.id}`", parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def all_messages(message):
    bot.reply_to(message, f"📝 البوت يستقبل: {message.text}")

# 🌐 نظام الصحة
@app.route('/health')
def health_check():
    return {
        "status": "healthy", 
        "users_count": len(users_db),
        "backups_count": len(backups_db),
        "version": "2.0"
    }

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
    print("🚀 بدأ تشغيل البوت مع نظام الذاكرة...")
    try:
        bot.remove_webhook()
        import time
        time.sleep(2)
        
        WEBHOOK_URL = f'https://usdt-bot-live.onrender.com/{BOT_TOKEN}'
        bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ Webhook مضبوط: {WEBHOOK_URL}")
        print(f"✅ نظام الذاكرة جاهز")
        
        PORT = int(os.environ.get('PORT', 10000))
        app.run(host='0.0.0.0', port=PORT, debug=False)
        
    except Exception as e:
        print(f"❌ خطأ في التشغيل: {e}")
