from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import threading
import time
from datetime import datetime, timedelta
import os
import random
import json
import shutil

# تكوين الأساسيات
BOT_TOKEN = "8385331860:AAFTz51bMqPjtEBM50p_5WY_pbMytnqS0zc"
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=10)
app = Flask(__name__)

# 🔐 إعدادات المشرفين - أنت المسؤول الوحيد
ADMIN_IDS = [8400225549]  # ✅ أنت المشرف الرئيسي!

# 🔧 نظام التخزين الدائم والنسخ الاحتياطي
DB_PATH = 'bot_database.db'
BACKUP_DIR = 'backups'

# 🔧 إنشاء مجلد النسخ الاحتياطية
os.makedirs(BACKUP_DIR, exist_ok=True)

def create_backup():
    """إنشاء نسخة احتياطية تلقائية"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{BACKUP_DIR}/backup_{timestamp}.db"
        shutil.copy2(DB_PATH, backup_file)
        
        # الاحتفاظ بآخر 10 نسخ فقط
        backup_files = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith('backup_')])
        if len(backup_files) > 10:
            for old_file in backup_files[:-10]:
                os.remove(f"{BACKUP_DIR}/{old_file}")
        
        print(f"✅ تم إنشاء نسخة احتياطية: {backup_file}")
        return True
    except Exception as e:
        print(f"❌ فشل إنشاء النسخة الاحتياطية: {e}")
        return False

def auto_backup():
    """نسخ احتياطي تلقائي كل ساعة"""
    while True:
        time.sleep(3600)  # كل ساعة
        create_backup()

# 🔧 بدء النسخ الاحتياطي التلقائي في خيط منفصل
backup_thread = threading.Thread(target=auto_backup, daemon=True)
backup_thread.start()

# 🔧 تهيئة قاعدة البيانات مع النسخ الاحتياطي
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    
    # إعدادات الأداء
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=10000")
    cursor.execute("PRAGMA temp_store=MEMORY")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance REAL DEFAULT 0.0,
            referrals_count INTEGER DEFAULT 0,
            referrer_id INTEGER,
            vip_level INTEGER DEFAULT 0,
            vip_expiry TIMESTAMP,
            games_played_today INTEGER DEFAULT 0,
            total_games_played INTEGER DEFAULT 0,
            total_earned REAL DEFAULT 0.0,
            total_deposits REAL DEFAULT 0.0,
            games_counter INTEGER DEFAULT 0,
            last_daily_bonus TIMESTAMP,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            withdrawal_attempts INTEGER DEFAULT 0,
            new_referrals_count INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            bonus_given BOOLEAN DEFAULT FALSE,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            game_type TEXT,
            bet_amount REAL,
            win_amount REAL,
            result TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            description TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            status TEXT DEFAULT 'completed',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdrawal_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            attempt_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            referrals_before INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    
    # إنشاء نسخة احتياطية بعد التهيئة
    create_backup()
    
    return conn

db_connection = init_db()

# 🔧 دوال مساعدة
def get_user(user_id):
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user:
        return {
            'user_id': user[0],
            'username': user[1],
            'first_name': user[2],
            'last_name': user[3],
            'balance': user[4],
            'referrals_count': user[5],
            'referrer_id': user[6],
            'vip_level': user[7],
            'vip_expiry': user[8],
            'games_played_today': user[9],
            'total_games_played': user[10],
            'total_earned': user[11],
            'total_deposits': user[12],
            'games_counter': user[13],
            'last_daily_bonus': user[14],
            'registration_date': user[15],
            'withdrawal_attempts': user[16],
            'new_referrals_count': user[17]
        }
    return None

def save_user(user_data):
    cursor = db_connection.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, username, first_name, last_name, balance, referrals_count, 
         referrer_id, vip_level, vip_expiry, games_played_today, total_games_played, 
         total_earned, total_deposits, games_counter, last_daily_bonus, withdrawal_attempts, new_referrals_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_data['user_id'],
        user_data.get('username'),
        user_data.get('first_name'),
        user_data.get('last_name'),
        user_data.get('balance', 0.0),
        user_data.get('referrals_count', 0),
        user_data.get('referrer_id'),
        user_data.get('vip_level', 0),
        user_data.get('vip_expiry'),
        user_data.get('games_played_today', 0),
        user_data.get('total_games_played', 0),
        user_data.get('total_earned', 0.0),
        user_data.get('total_deposits', 0.0),
        user_data.get('games_counter', 0),
        user_data.get('last_daily_bonus'),
        user_data.get('withdrawal_attempts', 0),
        user_data.get('new_referrals_count', 0)
    ))
    db_connection.commit()
    
    # نسخ احتياطي بعد كل حفظ مهم
    create_backup()

# 🛠️ الأوامر الإدارية الجديدة الشاملة
@bot.message_handler(commands=['adduser'])
def add_user_complete(message):
    """إضافة مستخدم جديد بجميع البيانات"""
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.send_message(message.chat.id,
                "📝 **استخدم:**\n"
                "`/adduser user_id balance [referrals] [vip_level] [total_deposits] [total_earned] [games_played]`\n\n"
                "**مثال:**\n"
                "`/adduser 8003454476 1500.0 5 2 1500.0 2000.0 50`\n"
                "`/adduser 123456789 500.0 3 1 500.0 800.0 30`")
            return
        
        user_id = int(parts[1])
        balance = float(parts[2])
        referrals = int(parts[3]) if len(parts) > 3 else 0
        vip_level = int(parts[4]) if len(parts) > 4 else 0
        total_deposits = float(parts[5]) if len(parts) > 5 else balance
        total_earned = float(parts[6]) if len(parts) > 6 else balance
        total_games = int(parts[7]) if len(parts) > 7 else referrals * 10
        
        # محاولة جلب معلومات المستخدم من التليجرام
        try:
            chat = bot.get_chat(user_id)
            first_name = chat.first_name
            last_name = chat.last_name
            username = chat.username
        except:
            first_name = "مستخدم"
            last_name = ""
            username = ""
        
        user_data = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'balance': balance,
            'referrals_count': referrals,
            'referrer_id': None,
            'vip_level': vip_level,
            'vip_expiry': None,
            'games_played_today': 0,
            'total_games_played': total_games,
            'total_earned': total_earned,
            'total_deposits': total_deposits,
            'games_counter': 0,
            'last_daily_bonus': None,
            'withdrawal_attempts': 0,
            'new_referrals_count': 0
        }
        
        save_user(user_data)
        
        bot.send_message(message.chat.id,
            f"✅ **تم إضافة المستخدم بنجاح:**\n\n"
            f"🆔 **الآيدي:** `{user_id}`\n"
            f"👤 **الاسم:** {first_name} {last_name}\n"
            f"📛 **اليوزر:** @{username if username else 'لا يوجد'}\n"
            f"💰 **الرصيد:** {balance} USDT\n"
            f"👥 **الإحالات:** {referrals}\n"
            f"💎 **مستوى VIP:** {vip_level}\n"
            f"💳 **إجمالي الإيداعات:** {total_deposits} USDT\n"
            f"🎯 **إجمالي الألعاب:** {total_games}\n"
            f"🏆 **إجمالي الأرباح:** {total_earned} USDT")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['updateuser'])
def update_user_complete(message):
    """تحديث بيانات مستخدم موجود"""
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.send_message(message.chat.id,
                "📝 **استخدم:**\n"
                "`/updateuser user_id field value`\n\n"
                "**الحقول المتاحة:**\n"
                "`balance, referrals, vip_level, deposits, earned, games`\n\n"
                "**أمثلة:**\n"
                "`/updateuser 8003454476 balance 2000.0`\n"
                "`/updateuser 8003454476 referrals 10`\n"
                "`/updateuser 8003454476 vip_level 3`")
            return
        
        user_id = int(parts[1])
        field = parts[2].lower()
        value = parts[3] if len(parts) > 3 else ""
        
        user = get_user(user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود! استخدم `/adduser` أولاً")
            return
        
        field_map = {
            'balance': ('balance', float(value)),
            'referrals': ('referrals_count', int(value)),
            'vip_level': ('vip_level', int(value)),
            'deposits': ('total_deposits', float(value)),
            'earned': ('total_earned', float(value)),
            'games': ('total_games_played', int(value))
        }
        
        if field in field_map:
            field_name, field_value = field_map[field]
            user[field_name] = field_value
            save_user(user)
            
            bot.send_message(message.chat.id,
                f"✅ **تم تحديث المستخدم:**\n\n"
                f"🆔 **الآيدي:** `{user_id}`\n"
                f"📊 **الحقل:** {field}\n"
                f"🎯 **القيمة الجديدة:** {field_value}")
        else:
            bot.send_message(message.chat.id, "❌ حقل غير صحيح! الحقول المتاحة: balance, referrals, vip_level, deposits, earned, games")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['userfullinfo'])
def user_full_info(message):
    """عرض معلومات كاملة عن المستخدم"""
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ استخدم: /userfullinfo [user_id]")
            return
        
        user_id = int(parts[1])
        user = get_user(user_id)
        
        if user:
            remaining_games = 3 - user['games_played_today']
            vip_expiry = user['vip_expiry'][:10] if user['vip_expiry'] else "غير محدد"
            reg_date = user['registration_date'][:10] if user['registration_date'] else "غير معروف"
            
            info_text = f"""
📊 **معلومات كاملة عن المستخدم:**

🆔 **الآيدي:** `{user['user_id']}`
👤 **الاسم:** {user['first_name']} {user.get('last_name', '')}
📛 **اليوزرنيم:** @{user.get('username', 'غير متوفر')}

💰 **الحساب المالي:**
• الرصيد: {user['balance']:.1f} USDT
• إجمالي الإيداعات: {user['total_deposits']:.1f} USDT
• إجمالي الأرباح: {user['total_earned']:.1f} USDT

🎮 **إحصائيات الألعاب:**
• المحاولات المتبقية: {remaining_games}/3
• إجمالي الألعاب: {user['total_games_played']}
• عداد المكافآت: {user['games_counter']}/3

👥 **نظام الإحالات:**
• عدد الإحالات: {user['referrals_count']}
• الإحالات الجديدة: {user['new_referrals_count']}
• محاولات السحب: {user['withdrawal_attempts']}

💎 **معلومات VIP:**
• المستوى: {user['vip_level']}
• انتهاء الصلاحية: {vip_expiry}

📅 **معلومات عامة:**
• تاريخ التسجيل: {reg_date}
• آخر مكافأة يومية: {user['last_daily_bonus'] or 'غير محدد'}
"""
            bot.send_message(message.chat.id, info_text, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['listbackups'])
def list_backups(message):
    """عرض قائمة النسخ الاحتياطية"""
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        backup_files = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith('backup_')])
        
        if backup_files:
            backups_list = "📂 **النسخ الاحتياطية المتاحة:**\n\n"
            for idx, backup in enumerate(backup_files[-10:], 1):  # آخر 10 نسخ
                size = os.path.getsize(f"{BACKUP_DIR}/{backup}") / 1024  # حجم بالكيلوبايت
                backups_list += f"{idx}. `{backup}` ({size:.1f} KB)\n"
            
            backups_list += f"\n📊 **إجمالي النسخ:** {len(backup_files)}"
        else:
            backups_list = "❌ لا توجد نسخ احتياطية حالياً"
        
        bot.send_message(message.chat.id, backups_list)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['manualbackup'])
def manual_backup(message):
    """إنشاء نسخة احتياطية يدوية"""
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    if create_backup():
        bot.send_message(message.chat.id, "✅ تم إنشاء نسخة احتياطية يدوية بنجاح")
    else:
        bot.send_message(message.chat.id, "❌ فشل إنشاء النسخة الاحتياطية")

# 🛡️ نظام الحماية من فقدان البيانات
def emergency_recovery():
    """استعادة طارئة تلقائية عند التشغيل"""
    try:
        # التحقق من وجود قاعدة البيانات الرئيسية
        if not os.path.exists(DB_PATH):
            # البحث عن أحدث نسخة احتياطية
            backup_files = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith('backup_')])
            if backup_files:
                latest_backup = backup_files[-1]
                shutil.copy2(f"{BACKUP_DIR}/{latest_backup}", DB_PATH)
                print(f"🆘 تم الاستعادة الطارئة من: {latest_backup}")
                return True
        return False
    except Exception as e:
        print(f"❌ فشل الاستعادة الطارئة: {e}")
        return False

# تشغيل الاستعادة الطارئة عند البدء
if emergency_recovery():
    print("✅ تم استعادة البيانات تلقائياً من النسخ الاحتياطية")

# ⚠️ كل الأزرار والوظائف الحالية تبقى كما هي دون أي تغيير ⚠️
# ... [كل الكود الأصلي للأزرار والألعاب يبقى تماماً كما هو]
# ... [بداية من إنشاء الأزرار -> دوال الألعاب -> الأوامر الأساسية -> معالجة الأزرار]
# ... [كل شيء يبقى يعمل بنفس الطريقة دون أي تغيير]

# 🎯 إنشاء الأزرار (تبقى كما هي تماماً)
def create_main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🎮 الألعاب (3 محاولات)", callback_data="games_menu"),
        InlineKeyboardButton("📊 الملف الشخصي", callback_data="profile")
    )
    keyboard.add(
        InlineKeyboardButton("👥 الإحالات (+1 محاولة)", callback_data="referral"),
        InlineKeyboardButton("💰 سحب رصيد", callback_data="withdraw")
    )
    keyboard.add(
        InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_3"),
        InlineKeyboardButton("💎 باقات VIP", callback_data="vip_packages")
    )
    return keyboard

# ... [باقي دوال إنشاء الأزرار تبقى كما هي]

# 🎮 دوال الألعاب (تبقى كما هي تماماً)
def play_slots_game(user_id):
    symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎"]
    result = [random.choice(symbols) for _ in range(3)]
    return result

# ... [باقي دوال الألعاب تبقى كما هي]

# 🎯 الأوامر الأساسية (تبقى كما هي تماماً)
@bot.message_handler(commands=['start'])
def start_command(message):
    # ... [الكود الأصلي يبقى كما هو]
    pass

# ... [كل الكود الأصلي يبقى دون تغيير]

# 🌐 نظام الصحة (يبقى كما هو)
@app.route('/health')
def health_check():
    # ... [الكود الأصلي]
    pass

# 🌐 إعداد ويب هوك (يبقى كما هو)
@app.route('/')
def index():
    return "🤖 البوت يعمل بشكل صحيح! استخدم /start في التلجرام"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    # ... [الكود الأصلي]
    pass

# 🚀 بدء التشغيل على Render (مع تحسينات)
if __name__ == "__main__":
    print("🚀 بدأ تشغيل البوت على Render مع نظام النسخ الاحتياطي...")
    
    try:
        # إعداد ويب هوك
        bot.remove_webhook()
        time.sleep(2)
        
        # ✅ استخدام Webhook مع الرابط الصحيح
        WEBHOOK_URL = f'https://usdt-bot-working.onrender.com/{BOT_TOKEN}'
        bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ Webhook مضبوط على: {WEBHOOK_URL}")
        print(f"✅ نظام النسخ الاحتياطي يعمل تلقائياً")
        print(f"✅ قاعدة البيانات محمية من الفقدان")
        
        # تشغيل الخادم
        PORT = int(os.environ.get('PORT', 10000))
        print(f"🌐 بدأ تشغيل الخادم على المنفذ {PORT}")
        app.run(host='0.0.0.0', port=PORT, debug=False)
        
    except Exception as e:
        print(f"❌ خطأ في التشغيل: {e}")
