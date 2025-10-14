import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
from datetime import datetime, timedelta
import time
import sqlite3
import json
import os
import logging
from flask import Flask, request
import threading
import requests
import schedule
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# 🔧 إعدادات متقدمة للـ Render
app = Flask(__name__)
PORT = int(os.environ.get('PORT', 10000))

# 🔧 إعدادات البوت
BOT_TOKEN = "8385331860:AAFTz51bMqPjtEBM50p_5WY_pbMytnqS0zc"
SUPPORT_USER_ID = "8400225549"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
WEBHOOK_URL = f"https://usdt-mining-bot-wmvf.onrender.com/{BOT_TOKEN}"

# 🗄️ قاعدة بيانات SQLite
def init_db():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            mining_earnings REAL DEFAULT 0.0,
            referrals_count INTEGER DEFAULT 0,
            referral_list TEXT DEFAULT '[]',
            referral_earnings REAL DEFAULT 0.0,
            referral_link TEXT,
            total_deposited REAL DEFAULT 0.0,
            vip_level TEXT,
            vip_expiry TEXT,
            games_played_today INTEGER DEFAULT 0,
            max_games_daily INTEGER DEFAULT 3,
            withdraw_eligible INTEGER DEFAULT 0,
            last_mining_time TEXT,
            last_active TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول طلبات الإيداع
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deposit_requests (
            code TEXT PRIMARY KEY,
            user_id TEXT,
            vip_type TEXT,
            amount REAL,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            expires_at TEXT
        )
    ''')
    
    # جدول أعضاء VIP
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vip_users (
            user_id TEXT PRIMARY KEY,
            level TEXT,
            activated_at TEXT,
            expires_at TEXT
        )
    ''')
    
    # جدول المعاملات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            type TEXT,
            amount REAL,
            description TEXT,
            status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    return conn

# تهيئة قاعدة البيانات
db_connection = init_db()

# 🎯 نظام VIP المحسن
vip_system = {
    "BRONZE": {
        "name": "🟢 VIP برونزي",
        "price": 5.0,
        "bonus": 0.10,
        "features": ["+10% أرباح تعدين", "دعم سريع", "مهام إضافية", "ألعاب حصرية"],
        "duration": 30,
        "color": "🟢",
        "daily_bonus": 0.5
    },
    "SILVER": {
        "name": "🔵 VIP فضى", 
        "price": 10.0,
        "bonus": 0.25,
        "features": ["+25% أرباح تعدين", "دعم مميز", "مهام حصرية", "مكافآت يومية"],
        "duration": 30,
        "color": "🔵",
        "daily_bonus": 1.0
    },
    "GOLD": {
        "name": "🟡 VIP ذهبي",
        "price": 20.0, 
        "bonus": 0.50,
        "features": ["+50% أرباح تعدين", "دعم فوري", "مكافآت يومية", "خصومات حصرية"],
        "duration": 30,
        "color": "🟡",
        "daily_bonus": 2.0
    }
}

# 🔧 دوال قاعدة البيانات
def get_user(user_id):
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (str(user_id),))
    user = cursor.fetchone()
    if user:
        return {
            'user_id': user[0],
            'balance': user[1],
            'mining_earnings': user[2],
            'referrals_count': user[3],
            'referral_list': json.loads(user[4]),
            'referral_earnings': user[5],
            'referral_link': user[6],
            'total_deposited': user[7],
            'vip_level': user[8],
            'vip_expiry': user[9],
            'games_played_today': user[10],
            'max_games_daily': user[11],
            'withdraw_eligible': bool(user[12]),
            'last_mining_time': user[13],
            'last_active': user[14]
        }
    return None

def save_user(user_data):
    cursor = db_connection.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, balance, mining_earnings, referrals_count, referral_list, referral_earnings, 
         referral_link, total_deposited, vip_level, vip_expiry, games_played_today, 
         max_games_daily, withdraw_eligible, last_mining_time, last_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_data['user_id'],
        user_data['balance'],
        user_data['mining_earnings'],
        user_data['referrals_count'],
        json.dumps(user_data['referral_list']),
        user_data['referral_earnings'],
        user_data['referral_link'],
        user_data['total_deposited'],
        user_data['vip_level'],
        user_data['vip_expiry'],
        user_data['games_played_today'],
        user_data['max_games_daily'],
        int(user_data['withdraw_eligible']),
        user_data['last_mining_time'],
        user_data['last_active']
    ))
    db_connection.commit()

def init_user(user_id):
    user = get_user(user_id)
    if not user:
        user_data = {
            'user_id': str(user_id),
            'balance': 0.0,
            'mining_earnings': 0.0,
            'referrals_count': 0,
            'referral_list': [],
            'referral_earnings': 0.0,
            'referral_link': f"https://t.me/BNBMini1Bot?start=ref_{user_id}",
            'total_deposited': 0.0,
            'vip_level': None,
            'vip_expiry': None,
            'games_played_today': 0,
            'max_games_daily': 3,
            'withdraw_eligible': False,
            'last_mining_time': None,
            'last_active': datetime.now().isoformat()
        }
        save_user(user_data)
        return user_data
    return user

# 🔄 نظام منع النوم المحسن
def keep_alive():
    while True:
        try:
            requests.get("https://usdt-mining-bot-wmvf.onrender.com/health", timeout=10)
            # تحديث إحصائيات النظام
            update_system_stats()
            print(f"🔄 pinged and updated at {datetime.now()}")
        except Exception as e:
            print(f"❌ ping failed: {e}")
        time.sleep(240)  # كل 4 دقائق

# 📊 نظام الإحصائيات المتقدم
def update_system_stats():
    cursor = db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM vip_users")
    total_vip = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(balance) FROM users")
    total_balance = cursor.fetchone()[0] or 0
    
    print(f"📊 System Stats - Users: {total_users}, VIP: {total_vip}, Balance: {total_balance}")

# 🎮 نظام الألعاب المتقدم
GAMES_SYSTEM = {
    "slots": {"name": "🎰 سلات ماشين", "base_reward": 2.0, "vip_bonus": 0.5},
    "shooting": {"name": "🎯 الرماية", "base_reward": 2.0, "vip_bonus": 0.5},
    "mining_race": {"name": "🏆 سباق التعدين", "base_reward": 2.0, "vip_bonus": 0.5},
    "price_prediction": {"name": "📈 توقع الأسعار", "base_reward": 2.0, "vip_bonus": 0.5},
    "mining_cards": {"name": "🃏 أوراق التعدين", "base_reward": 2.0, "vip_bonus": 0.5}
}

# 🛡️ نظام الأمان المتقدم
def validate_wallet_address(address):
    """التحقق من صحة عنوان المحفظة"""
    if not address or len(address) != 42 or not address.startswith('0x'):
        return False
    return True

def log_transaction(user_id, trans_type, amount, description="", status="completed"):
    """تسجيل المعاملات"""
    cursor = db_connection.cursor()
    cursor.execute('''
        INSERT INTO transactions (user_id, type, amount, description, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (str(user_id), trans_type, amount, description, status))
    db_connection.commit()

# 🔧 الدوال الرئيسية المحسنة
def vip_mining_rewards(user_id):
    user = get_user(user_id)
    if user and user['vip_level']:
        base_reward = 3.0
        vip_info = vip_system[user['vip_level']]
        reward = base_reward * (1 + vip_info['bonus'])
        return round(reward, 2)
    return 0.0

def can_play_game(user_id):
    user = get_user(user_id)
    if user:
        return user['games_played_today'] < user['max_games_daily']
    return False

def play_game(user_id, game_id):
    if can_play_game(user_id):
        user = get_user(user_id)
        game_info = GAMES_SYSTEM[game_id]
        reward = game_info['base_reward']
        
        # مكافأة VIP إضافية
        if user['vip_level']:
            reward += vip_system[user['vip_level']]['daily_bonus']
        
        user['games_played_today'] += 1
        user['balance'] += reward
        user['last_active'] = datetime.now().isoformat()
        save_user(user)
        
        # تسجيل المعاملة
        log_transaction(user_id, "game_reward", reward, f"ربح من لعبة {game_info['name']}")
        
        return reward
    return 0

def check_withdraw_eligibility(user_id):
    user = get_user(user_id)
    if user and user['balance'] >= 100 and user['referrals_count'] >= 15:
        user['withdraw_eligible'] = True
        save_user(user)
        return True
    return False

def handle_referral_join(new_user_id, referrer_id):
    if str(referrer_id) != str(new_user_id):
        referrer = get_user(referrer_id)
        if referrer:
            referral_bonus = 1.5
            
            referrer['referrals_count'] += 1
            referrer['referral_list'].append(new_user_id)
            referrer['max_games_daily'] += 1
            referrer['balance'] += referral_bonus
            referrer['referral_earnings'] += referral_bonus
            referrer['last_active'] = datetime.now().isoformat()
            save_user(referrer)
            
            # تسجيل المعاملة
            log_transaction(referrer_id, "referral_bonus", referral_bonus, "مكافأة إحالة")
            
            try:
                bot.send_message(
                    referrer_id,
                    f"🎉 **تمت إحالة جديدة!**\n\n"
                    f"👤 دخل مستخدم جديد عبر رابطك\n"
                    f"💰 ربحت: {referral_bonus} USDT\n"
                    f"🎮 حصلت على محاولة إضافية في الألعاب\n"
                    f"📊 إجمالي الإحالات: {referrer['referrals_count']}/15\n"
                    f"💵 أرباح الإحالات: {referrer['referral_earnings']} USDT"
                )
            except Exception as e:
                print(f"Error sending referral notification: {e}")
            
            check_withdraw_eligibility(referrer_id)

# 🎨 واجهات المستخدم المحسنة
def main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("⚡ التعدين", callback_data="mining"),
        InlineKeyboardButton("🎮 الألعاب", callback_data="games"),
        InlineKeyboardButton("💰 الإيداع", callback_data="deposit"),
        InlineKeyboardButton("👥 الإحالات", callback_data="referral"),
        InlineKeyboardButton("🎖️ نظام VIP", callback_data="vip_menu"),
        InlineKeyboardButton("🚀 خدمات VIP", callback_data="vip_services"),
        InlineKeyboardButton("📊 إحصائيات", callback_data="stats"),
        InlineKeyboardButton("📞 الدعم", callback_data="support"),
        InlineKeyboardButton("🌐 اللغة", callback_data="language")
    ]
    
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            keyboard.add(buttons[i], buttons[i + 1])
        else:
            keyboard.add(buttons[i])
    
    return keyboard

# ... (استمرار الكود مع كل handlers محسنة) ...

@bot.message_handler(commands=['start'])
def start_command(message):
    try:
        user_id = message.from_user.id
        init_user(user_id)
        
        # التحقق من رابط الإحالة
        if len(message.text.split()) > 1:
            referral_code = message.text.split()[1]
            if referral_code.startswith('ref_'):
                referrer_id = referral_code.replace('ref_', '')
                handle_referral_join(user_id, referrer_id)
        
        user = get_user(user_id)
        welcome_text = f"""🤖 **BNB Mini Bot - النسخة المطورة**

💰 الرصيد: {user['balance']:.1f} USDT
🎮 الألعاب: {user['games_played_today']}/{user['max_games_daily']} محاولات
👥 الإحالات: {user['referrals_count']}/15
🎖️ العضوية: {vip_system[user['vip_level']]['name'] if user['vip_level'] else 'بدون'}

⚡ **مزايا جديدة:**
• قاعدة بيانات آمنة
• إحصائيات متقدمة
• نظام أمان محسن
• دعم فوري

📋 **القائمة الرئيسية:**"""
        
        bot.send_message(user_id, welcome_text, reply_markup=main_keyboard())
        log_transaction(user_id, "bot_start", 0, "بدء استخدام البوت")
        
    except Exception as e:
        logging.error(f"Error in start_command: {e}")

# 🌐 نظام Webhook المحسن
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BNB Mini Bot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .status { color: green; font-size: 24px; }
            .stats { margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>🤖 BNB Mini Bot</h1>
        <div class="status">✅ البوت يعمل بشكل مثالي</div>
        <div class="stats">
            <p>🚀 النسخة: 2.0 المطورة</p>
            <p>🛡️ نظام أمان متقدم</p>
            <p>🗄️ قاعدة بيانات آمنة</p>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health_check():
    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "total_users": total_users,
            "version": "2.0",
            "performance": "excellent"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}, 500

# 🔧 نظام الصيانة التلقائية
def daily_maintenance():
    """صيانة يومية تلقائية"""
    try:
        cursor = db_connection.cursor()
        # إعادة تعيين محاولات الألعاب اليومية
        cursor.execute("UPDATE users SET games_played_today = 0")
        # تحديث حالة VIP
        cursor.execute("DELETE FROM vip_users WHERE expires_at < datetime('now')")
        cursor.execute("UPDATE users SET vip_level = NULL WHERE vip_expiry < datetime('now')")
        db_connection.commit()
        print("✅ Daily maintenance completed")
    except Exception as e:
        print(f"❌ Maintenance error: {e}")

# 🚀 بدء التشغيل
if __name__ == "__main__":
    print("🚀 بدأ تشغيل البوت المتطور...")
    
    # بدء نظام منع النوم
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    
    # جدولة الصيانة اليومية
    scheduler = BackgroundScheduler()
    scheduler.add_job(daily_maintenance, 'cron', hour=0, minute=0)  # منتصف الليل
    scheduler.start()
    
    # تعيين Webhook
    try:
        bot.remove_webhook()
        time.sleep(2)
        bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ Webhook مضبوط على: {WEBHOOK_URL}")
    except Exception as e:
        print(f"⚠️ تحذير في تعيين Webhook: {e}")
    
    # تشغيل الخادم
    print(f"🌐 بدأ تشغيل الخادم المتطور على المنفذ {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
    
    # تنظيف عند الإغلاق
    atexit.register(lambda: scheduler.shutdown())
    atexit.register(lambda: db_connection.close())
