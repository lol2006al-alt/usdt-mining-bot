from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import psycopg2
from psycopg2.extras import RealDictCursor
import threading
import time
from datetime import datetime, timedelta
import os
import random
import json

# تكوين الأساسيات
BOT_TOKEN = "BOT_TOKEN = "8385331860:AAEcFqGY4vXORINuGUH6XpmSN9-FtluEMj8""
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=10)
app = Flask(__name__)

# 🔐 إعدادات المشرفين - أنت المسؤول الوحيد
ADMIN_IDS = [8400225549]  # ✅ أنت المشرف الرئيسي!

# 🔧 تكوين PostgreSQL من Render
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://localhost:5432/bot_db')

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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deposits (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                amount REAL,
                status TEXT DEFAULT 'completed',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawal_attempts (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                attempt_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                referrals_before INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        print("✅ قاعدة بيانات PostgreSQL جاهزة!")
        return conn
        
    except Exception as e:
        print(f"❌ خطأ في تهيئة PostgreSQL: {e}")
        return None

db_connection = init_db()

# 🔧 دوال مساعدة لـ PostgreSQL
def get_user(user_id):
    try:
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None
    except Exception as e:
        print(f"❌ خطأ في جلب المستخدم: {e}")
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
        print(f"❌ خطأ في حفظ المستخدم: {e}")
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
                
                if is_deposit:
                    cursor.execute(
                        "INSERT INTO deposits (user_id, amount) VALUES (%s, %s)",
                        (user_id, amount)
                    )
                
                db_connection.commit()
                return True
            except Exception as e:
                print(f"❌ خطأ في تسجيل المعاملة: {e}")
                db_connection.rollback()
    return False

# 🛠️ نظام النسخ الاحتياطي الداخلي لـ PostgreSQL
def create_sql_backup():
    """إنشاء نسخة احتياطية داخل قاعدة البيانات"""
    try:
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)
        
        # جمع بيانات جميع المستخدمين
        cursor.execute("SELECT * FROM users")
        users_data = cursor.fetchall()
        
        # جمع بيانات الإحالات
        cursor.execute("SELECT * FROM referrals")
        referrals_data = cursor.fetchall()
        
        # تجميع البيانات
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'users': [dict(user) for user in users_data],
            'referrals': [dict(ref) for ref in referrals_data],
            'total_users': len(users_data),
            'total_referrals': len(referrals_data)
        }
        
        # حفظ النسخة الاحتياطية
        cursor.execute(
            "INSERT INTO backups (backup_data, description) VALUES (%s, %s)",
            (json.dumps(backup_data), f"Backup {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        )
        
        db_connection.commit()
        print(f"✅ تم إنشاء نسخة احتياطية: {len(users_data)} مستخدم")
        return True
        
    except Exception as e:
        print(f"❌ فشل النسخ الاحتياطي: {e}")
        db_connection.rollback()
        return False

def list_sql_backups():
    """عرض النسخ الاحتياطية المخزنة داخلياً"""
    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT id, created_at, description FROM backups ORDER BY created_at DESC LIMIT 10")
        backups = cursor.fetchall()
        return backups
    except Exception as e:
        print(f"❌ فشل جلب النسخ الاحتياطية: {e}")
        return []

# 🛠️ الأوامر الإدارية الشاملة
@bot.message_handler(commands=['quickadd'])
def quick_add_balance(message):
    """إضافة رصيد سريعة - الأمر الأساسي"""
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "❌ استخدم: /quickadd [user_id] [amount]")
            return
        
        target_user_id = int(parts[1])
        amount = float(parts[2])
        
        if add_balance(target_user_id, amount, f"إضافة إدارية بواسطة {message.from_user.id}", is_deposit=True):
            user = get_user(target_user_id)
            bot.send_message(
                message.chat.id, 
                f"✅ تم إضافة {amount} USDT للمستخدم {target_user_id}\n"
                f"💰 الرصيد الجديد: {user['balance']:.1f} USDT\n"
                f"💳 إجمالي الإيداعات: {user['total_deposits']:.1f} USDT"
            )
            
            # إشعار المستخدم
            try:
                bot.send_message(
                    target_user_id,
                    f"🎉 تم إضافة {amount} USDT إلى رصيدك!\n"
                    f"💰 رصيدك الحالي: {user['balance']:.1f} USDT\n"
                    f"💳 إجمالي إيداعاتك: {user['total_deposits']:.1f} USDT"
                )
            except:
                pass
        else:
            bot.send_message(message.chat.id, "❌ فشل في إضافة الرصيد")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['quickremove'])
def quick_remove_balance(message):
    """سحب رصيد سريع"""
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "❌ استخدم: /quickremove [user_id] [amount]")
            return
        
        target_user_id = int(parts[1])
        amount = float(parts[2])
        
        user = get_user(target_user_id)
        if user:
            if user['balance'] >= amount:
                old_balance = user['balance']
                user['balance'] -= amount
                if save_user(user):
                    bot.send_message(
                        message.chat.id, 
                        f"✅ تم سحب {amount} USDT من المستخدم {target_user_id}\n"
                        f"📊 الرصيد السابق: {old_balance:.1f} USDT\n"
                        f"💰 الرصيد الجديد: {user['balance']:.1f} USDT"
                    )
                else:
                    bot.send_message(message.chat.id, "❌ فشل في سحب الرصيد")
            else:
                bot.send_message(message.chat.id, f"❌ رصيد المستخدم غير كافٍ! الرصيد الحالي: {user['balance']:.1f}")
        else:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

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
                "**أمثلة:**\n"
                "`/adduser 8003454476 1500.0`\n"
                "`/adduser 8003454476 1500.0 5 2 1500.0 2000.0 50`")
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
            last_name = chat.last_name if chat.last_name else ""
            username = chat.username if chat.username else ""
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
        
        if save_user(user_data):
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
                f"🏆 **إجمالي الأرباح:** {total_earned} USDT\n\n"
                f"💾 **التخزين:** PostgreSQL (آمن 100%)")
        else:
            bot.send_message(message.chat.id, "❌ فشل في إضافة المستخدم")
            
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

@bot.message_handler(commands=['manualbackup'])
def manual_backup(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        bot.send_message(message.chat.id, "🔄 جاري إنشاء نسخة احتياطية داخلية...")
        
        if create_sql_backup():
            backups = list_sql_backups()
            latest = backups[0] if backups else None
            
            if latest:
                backup_id, created_at, description = latest
                response = f"""✅ تم إنشاء نسخة احتياطية بنجاح!

📊 **تفاصيل النسخة:**
🆔 المعرف: {backup_id}
📅 التاريخ: {created_at}
📝 الوصف: {description}

💾 **التخزين:** PostgreSQL (آمن 100%)
🛡️ **الحماية:** بياناتك محمية من الضياع"""
            else:
                response = "✅ تم إنشاء النسخة ولكن لم يتم العثور على تفاصيلها"
        else:
            response = "❌ فشل إنشاء النسخة الاحتياطية"
        
        bot.send_message(message.chat.id, response)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")

@bot.message_handler(commands=['listbackups'])
def list_backups(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        backups = list_sql_backups()
        
        if backups:
            backups_list = "📂 **النسخ الاحتياطية المخزنة في PostgreSQL:**\n\n"
            for backup in backups:
                backup_id, created_at, description = backup
                backups_list += f"🆔 {backup_id} | 📅 {created_at.strftime('%Y-%m-%d %H:%M')}\n📝 {description}\n\n"
            
            backups_list += f"💾 **إجمالي النسخ:** {len(backups)}"
        else:
            backups_list = "❌ لا توجد نسخ احتياطية حالياً\nاستخدم `/manualbackup` لإنشاء أول نسخة"
        
        bot.send_message(message.chat.id, backups_list)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")

# 🎯 كل الأزرار والوظائف الحالية تبقى كما هي تماماً
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

# 🎮 دوال الألعاب
def play_slots_game(user_id):
    symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎"]
    result = [random.choice(symbols) for _ in range(3)]
    return result

def play_dice_game(user_id):
    user_dice = random.randint(1, 6)
    bot_dice = random.randint(1, 6)
    result = "فوز" if user_dice > bot_dice else "خسارة" if user_dice < bot_dice else "تعادل"
    return user_dice, bot_dice, result

def play_football_game(user_id):
    outcomes = ["هدف 🥅", "إصابة القائم 🚩", "حارس يصد ⛔"]
    result = random.choices(outcomes, k=3)
    return result

def play_basketball_game(user_id):
    shots = []
    for i in range(3):
        shot_type = "🎯 تسجيل ✅" if random.random() > 0.3 else "🎯 أخطأت ❌"
        shots.append(shot_type)
    return shots

def play_darts_game(user_id):
    scores = []
    for i in range(3):
        score = random.randint(10, 50)
        scores.append(f"🎯 نقاط: {score}")
    return scores

# 🎯 الأوامر الأساسية
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        referrer_id = None
        referral_bonus = 0
        
        if len(message.text.split()) > 1:
            try:
                referrer_id = int(message.text.split()[1])
                referrer_user = get_user(referrer_id)
                
                if referrer_user and referrer_id != user_id:
                    if add_referral(referrer_id, user_id):
                        add_balance(user_id, 1.0, "مكافأة انضمام بالإحالة")
                        referral_bonus = 1.0
                        
                        try:
                            bot.send_message(
                                referrer_id,
                                f"🎉 تم انضمام صديقك باستخدام رابطك!\n"
                                f"💰 حصلت على 1.0 USDT مكافأة إحالة\n"
                                f"🎯 وحصلت على محاولة لعب إضافية!"
                            )
                        except:
                            pass
            except:
                referrer_id = None
        
        new_user = {
            'user_id': user_id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            'referrer_id': referrer_id,
            'balance': 0.0 + referral_bonus,
            'games_played_today': 3,
            'total_deposits': 0.0,
            'withdrawal_attempts': 0,
            'new_referrals_count': 0
        }
        save_user(new_user)
        user = new_user
        
        welcome_text = f"""
        🎮 أهلاً وسهلاً {message.from_user.first_name}!

        🎯 لديك 3 محاولات لعب مجانية
        💰 مكافأة الإحالة: 1.0 USDT لكل صديق
        👥 كل إحالة تمنحك محاولة إضافية

        🏆 اربح 5 USDT كل 3 محاولات!
        """
    else:
        welcome_text = f"""
        🎮 مرحباً بعودتك {message.from_user.first_name}!

        💰 رصيدك: {user['balance']:.1f} USDT
        👥 عدد الإحالات: {user['referrals_count']}
        🎯 المحاولات المتبقية: {3 - user['games_played_today']}
        🏆 مستوى VIP: {user['vip_level']}
        """
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_main_menu())

def add_referral(referrer_id, referred_id):
    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT * FROM referrals WHERE referrer_id = %s AND referred_id = %s", 
                      (referrer_id, referred_id))
        if cursor.fetchone():
            return False
        
        cursor.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (%s, %s)", 
                      (referrer_id, referred_id))
        cursor.execute("UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = %s", 
                      (referrer_id,))
        
        # تحديث الإحالات الجديدة إذا كان لديه محاولات سحب
        cursor.execute("SELECT withdrawal_attempts FROM users WHERE user_id = %s", (referrer_id,))
        result = cursor.fetchone()
        if result and result[0] > 0:
            cursor.execute("UPDATE users SET new_referrals_count = new_referrals_count + 1 WHERE user_id = %s", 
                          (referrer_id,))
        
        # منح مكافأة 1.0 USDT للمُحيل
        referrer_user = get_user(referrer_id)
        if referrer_user:
            referrer_user['balance'] += 1.0
            referrer_user['total_earned'] += 1.0
            save_user(referrer_user)
            
            cursor.execute(
                "INSERT INTO transactions (user_id, type, amount, description) VALUES (%s, %s, %s, %s)",
                (referrer_id, 'referral_bonus', 1.0, f"مكافأة إحالة للمستخدم {referred_id}")
            )
        
        db_connection.commit()
        return True
    except Exception as e:
        print(f"❌ خطأ في إضافة الإحالة: {e}")
        db_connection.rollback()
        return False

# 🌐 نظام الصحة
@app.route('/health')
def health_check():
    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM referrals")
        total_referrals = cursor.fetchone()[0]
        
        return {
            "status": "healthy",
            "database": "PostgreSQL",
            "timestamp": datetime.now().isoformat(),
            "total_users": total_users,
            "total_referrals": total_referrals,
            "version": "8.0",
            "performance": "excellent"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}, 500

# 🌐 إعداد ويب هوك
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

# 🚀 بدء التشغيل على Render
if __name__ == "__main__":
    print("🚀 بدأ تشغيل البوت على Render مع PostgreSQL...")
    
    try:
        # إعداد ويب هوك
        bot.remove_webhook()
        time.sleep(2)
        
        WEBHOOK_URL = f'https://usdt-bot-working.onrender.com/{BOT_TOKEN}'
        bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ Webhook مضبوط على: {WEBHOOK_URL}")
        print(f"✅ قاعدة بيانات PostgreSQL تعمل")
        print(f"✅ نظام النسخ الاحتياطي الداخلي جاهز")
        
        # تشغيل الخادم
        PORT = int(os.environ.get('PORT', 10000))
        print(f"🌐 بدأ تشغيل الخادم على المنفذ {PORT}")
        app.run(host='0.0.0.0', port=PORT, debug=False)
        
    except Exception as e:
        print(f"❌ خطأ في التشغيل: {e}")
