from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import psycopg2
from psycopg2.extras import RealDictCursor
import time
from datetime import datetime
import os
import random
import json
import logging

# تكوين الأساسيات
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8385331860:AAEcFqGY4vXORINuGUH6XpmSN9-FtluEMj8")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# تفعيل الـ logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔐 إعدادات المشرفين
ADMIN_IDS = [8400225549]

# 🔧 تكوين PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL')

def init_db():
    """تهيئة قاعدة بيانات PostgreSQL"""
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        
        # إنشاء الجداول
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                balance REAL DEFAULT 0.0,
                referrals_count INTEGER DEFAULT 0,
                referrer_id BIGINT,
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
                id SERIAL PRIMARY KEY,
                referrer_id BIGINT,
                referred_id BIGINT,
                bonus_given BOOLEAN DEFAULT FALSE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backups (
                id SERIAL PRIMARY KEY,
                backup_data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                type TEXT,
                amount REAL,
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        logger.info("✅ قاعدة بيانات PostgreSQL جاهزة!")
        return conn
        
    except Exception as e:
        logger.error(f"❌ خطأ في تهيئة PostgreSQL: {e}")
        return None

# تهيئة قاعدة البيانات
db_connection = init_db()

# 🔧 دوال مساعدة لـ PostgreSQL
def get_user(user_id):
    try:
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None
    except Exception as e:
        logger.error(f"❌ خطأ في جلب المستخدم: {e}")
        return None

def save_user(user_data):
    try:
        cursor = db_connection.cursor()
        cursor.execute('''
            INSERT INTO users 
            (user_id, username, first_name, last_name, balance, referrals_count, 
             referrer_id, vip_level, vip_expiry, games_played_today, total_games_played, 
             total_earned, total_deposits, games_counter, last_daily_bonus, withdrawal_attempts, new_referrals_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            balance = EXCLUDED.balance,
            referrals_count = EXCLUDED.referrals_count,
            referrer_id = EXCLUDED.referrer_id,
            vip_level = EXCLUDED.vip_level,
            vip_expiry = EXCLUDED.vip_expiry,
            games_played_today = EXCLUDED.games_played_today,
            total_games_played = EXCLUDED.total_games_played,
            total_earned = EXCLUDED.total_earned,
            total_deposits = EXCLUDED.total_deposits,
            games_counter = EXCLUDED.games_counter,
            last_daily_bonus = EXCLUDED.last_daily_bonus,
            withdrawal_attempts = EXCLUDED.withdrawal_attempts,
            new_referrals_count = EXCLUDED.new_referrals_count
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
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ المستخدم: {e}")
        db_connection.rollback()
        return False

def add_balance(user_id, amount, description="", is_deposit=False):
    user = get_user(user_id)
    if user:
        user['balance'] += amount
        user['total_earned'] += amount
        
        if is_deposit:
            user['total_deposits'] += amount
        
        if save_user(user):
            try:
                cursor = db_connection.cursor()
                transaction_type = 'deposit' if is_deposit else 'bonus'
                cursor.execute(
                    "INSERT INTO transactions (user_id, type, amount, description) VALUES (%s, %s, %s, %s)",
                    (user_id, transaction_type, amount, description)
                )
                db_connection.commit()
                return True
            except Exception as e:
                logger.error(f"❌ خطأ في تسجيل المعاملة: {e}")
                db_connection.rollback()
    return False

# 🛠️ الأوامر الإدارية
@bot.message_handler(commands=['quickadd'])
def quick_add_balance(message):
    """إضافة رصيد سريعة"""
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
        
        if add_balance(target_user_id, amount, f"إضافة إدارية بواسطة {message.from_user.id}", is_deposit=True):
            user = get_user(target_user_id)
            bot.reply_to(
                message.chat.id, 
                f"✅ تم إضافة {amount} USDT للمستخدم {target_user_id}\n"
                f"💰 الرصيد الجديد: {user['balance']:.1f} USDT"
            )
        else:
            bot.reply_to(message.chat.id, "❌ فشل في إضافة الرصيد")
            
    except Exception as e:
        bot.reply_to(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['testpostgres'])
def test_postgres(message):
    """فحص قاعدة البيانات"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        cursor = db_connection.cursor()
        cursor.execute('SELECT version()')
        version = cursor.fetchone()
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        bot.reply_to(
            message.chat.id,
            f"✅ **PostgreSQL يعمل بنجاح!**\n\n"
            f"📊 **إحصائيات:**\n"
            f"• عدد المستخدمين: {user_count}\n"
            f"• الإصدار: {version[0]}\n"
            f"• الحالة: 🟢 نشط"
        )
    except Exception as e:
        bot.reply_to(message.chat.id, f"❌ خطأ في PostgreSQL: {e}")

@bot.message_handler(commands=['adduser'])
def add_user_complete(message):
    """إضافة مستخدم جديد بجميع البيانات"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message.chat.id,
                "📝 **استخدم:**\n"
                "`/adduser user_id balance [referrals] [vip_level] [total_deposits] [total_earned] [games_played]`")
            return
        
        user_id = int(parts[1])
        balance = float(parts[2])
        referrals = int(parts[3]) if len(parts) > 3 else 0
        vip_level = int(parts[4]) if len(parts) > 4 else 0
        total_deposits = float(parts[5]) if len(parts) > 5 else balance
        total_earned = float(parts[6]) if len(parts) > 6 else balance
        total_games = int(parts[7]) if len(parts) > 7 else referrals * 10
        
        user_data = {
            'user_id': user_id,
            'username': "",
            'first_name': "مستخدم",
            'last_name': "",
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
        
        if save_user(user_data):
            bot.reply_to(message.chat.id,
                f"✅ **تم إضافة المستخدم بنجاح:**\n\n"
                f"🆔 **الآيدي:** `{user_id}`\n"
                f"💰 **الرصيد:** {balance} USDT\n"
                f"👥 **الإحالات:** {referrals}\n"
                f"💎 **VIP:** {vip_level}\n"
                f"💳 **الإيداعات:** {total_deposits} USDT"
            )
        else:
            bot.reply_to(message.chat.id, "❌ فشل في إضافة المستخدم")
            
    except Exception as e:
        bot.reply_to(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['userfullinfo'])
def user_full_info(message):
    """عرض معلومات كاملة عن المستخدم"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message.chat.id, "❌ استخدم: /userfullinfo [user_id]")
            return
        
        user_id = int(parts[1])
        user = get_user(user_id)
        
        if user:
            info_text = f"""
📊 **معلومات كاملة عن المستخدم:**

🆔 **الآيدي:** `{user['user_id']}`
💰 **الرصيد:** {user['balance']:.1f} USDT
💳 **الإيداعات:** {user['total_deposits']:.1f} USDT
🏆 **الأرباح:** {user['total_earned']:.1f} USDT

👥 **الإحالات:** {user['referrals_count']}
💎 **VIP:** {user['vip_level']}
🎮 **الألعاب:** {user['total_games_played']}
"""
            bot.reply_to(message.chat.id, info_text)
        else:
            bot.reply_to(message.chat.id, "❌ المستخدم غير موجود!")
    except Exception as e:
        bot.reply_to(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['manualbackup'])
def manual_backup(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM users")
        users_data = cursor.fetchall()
        
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'users': [dict(user) for user in users_data],
            'total_users': len(users_data)
        }
        
        cursor.execute(
            "INSERT INTO backups (backup_data, description) VALUES (%s, %s)",
            (json.dumps(backup_data), f"Backup {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        )
        
        db_connection.commit()
        bot.reply_to(message.chat.id, f"✅ تم إنشاء نسخة احتياطية: {len(users_data)} مستخدم")
        
    except Exception as e:
        bot.reply_to(message.chat.id, f"❌ خطأ: {str(e)}")

# 🎯 كل الأزرار والوظائف الحالية تبقى كما هي
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

def create_games_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🎰 سلوتس", callback_data="game_slots"),
        InlineKeyboardButton("🎲 النرد", callback_data="game_dice")
    )
    keyboard.add(
        InlineKeyboardButton("⚽ كرة القدم", callback_data="game_football"),
        InlineKeyboardButton("🏀 السلة", callback_data="game_basketball")
    )
    keyboard.add(
        InlineKeyboardButton("🎯 السهم", callback_data="game_darts"),
        InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")
    )
    return keyboard

def create_vip_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("🟢 برونزي - 5 USDT", callback_data="buy_bronze"))
    keyboard.add(InlineKeyboardButton("🔵 فضى - 10 USDT", callback_data="buy_silver"))
    keyboard.add(InlineKeyboardButton("🟡 ذهبي - 20 USDT", callback_data="buy_gold"))
    keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
    return keyboard

def create_withdraw_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("💳 تأكيد استخدام BEP20", callback_data="confirm_bep20"))
    keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
    return keyboard

def create_referral_keyboard(user_id):
    keyboard = InlineKeyboardMarkup()
    referral_link = f"https://t.me/BNBMini1Bot?start={user_id}"
    
    keyboard.add(InlineKeyboardButton("📤 مشاركة الرابط", 
                url=f"https://t.me/share/url?url={referral_link}&text=انضم إلى هذا البوت الرائع واحصل على 1.0 USDT مجاناً! 🎮"))
    
    keyboard.add(InlineKeyboardButton("🔗 نسخ الرابط", callback_data="copy_link"))
    keyboard.add(InlineKeyboardButton("📊 إحالاتي", callback_data="my_referrals"))
    keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
    
    return keyboard, referral_link

# 🎮 دوال الألعاب (تبقى كما هي)
def play_slots_game(user_id):
    symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎"]
    return [random.choice(symbols) for _ in range(3)]

def play_dice_game(user_id):
    user_dice = random.randint(1, 6)
    bot_dice = random.randint(1, 6)
    result = "فوز" if user_dice > bot_dice else "خسارة" if user_dice < bot_dice else "تعادل"
    return user_dice, bot_dice, result

# 🎯 الأمر start الأساسي
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        # إنشاء مستخدم جديد
        new_user = {
            'user_id': user_id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name or "",
            'balance': 0.0,
            'referrals_count': 0,
            'vip_level': 0,
            'total_deposits': 0.0,
            'total_earned': 0.0,
            'total_games_played': 0
        }
        save_user(new_user)
    
    welcome_text = f"""
🎮 أهلاً وسهلاً {message.from_user.first_name}!

💰 رصيدك: {user['balance'] if user else 0:.1f} USDT
🎯 المحاولات المتبقية: 3
👥 عدد الإحالات: {user['referrals_count'] if user else 0}

🏆 اربح 5 USDT كل 3 محاولات!
"""
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_main_menu())

# 🌐 نظام الصحة
@app.route('/health')
def health_check():
    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        return {
            "status": "healthy",
            "database": "PostgreSQL",
            "total_users": total_users,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}, 500

@app.route('/')
def index():
    return "🤖 البوت يعمل بشكل صحيح مع PostgreSQL! استخدم /start في التلجرام"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    else:
        return 'Forbidden', 403

# 🚀 بدء التشغيل
if __name__ == "__main__":
    print("🚀 بدأ تشغيل البوت على Render مع PostgreSQL...")
    
    try:
        # إعداد ويب هوك
        bot.remove_webhook()
        time.sleep(2)
        
        WEBHOOK_URL = f'https://usdt-bot-working.onrender.com/{BOT_TOKEN}'
        bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ Webhook مضبوط على: {WEBHOOK_URL}")
        print("✅ جميع الأوامر جاهزة!")
        
        # تشغيل الخادم
        PORT = int(os.environ.get('PORT', 10000))
        app.run(host='0.0.0.0', port=PORT, debug=False)
        
    except Exception as e:
        print(f"❌ خطأ في التشغيل: {e}")
