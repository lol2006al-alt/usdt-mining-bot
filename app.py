from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import threading
import time
from datetime import datetime, timedelta
import os
import random

# تكوين الأساسيات
BOT_TOKEN = "8385331860:AAFTz51bMqPjtEBM50p_5WY_pbMytnqS0zc"
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=10)
app = Flask(__name__)

# 🔐 إعدادات المشرفين - أنت المسؤول الوحيد
ADMIN_IDS = [8400225549]  # ✅ أنت المشرف الرئيسي!

# 🔧 تهيئة قاعدة البيانات
def init_db():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
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
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    conn.commit()
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
            'registration_date': user[15]
        }
    return None

def save_user(user_data):
    cursor = db_connection.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, username, first_name, last_name, balance, referrals_count, 
         referrer_id, vip_level, vip_expiry, games_played_today, total_games_played, 
         total_earned, total_deposits, games_counter, last_daily_bonus)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        user_data.get('last_daily_bonus')
    ))
    db_connection.commit()

def add_balance(user_id, amount, description="", is_deposit=False):
    user = get_user(user_id)
    if user:
        user['balance'] += amount
        user['total_earned'] += amount
        
        if is_deposit:
            user['total_deposits'] += amount
        
        save_user(user)
        
        cursor = db_connection.cursor()
        transaction_type = 'deposit' if is_deposit else 'bonus'
        cursor.execute(
            "INSERT INTO transactions (user_id, type, amount, description) VALUES (?, ?, ?, ?)",
            (user_id, transaction_type, amount, description)
        )
        
        if is_deposit:
            cursor.execute(
                "INSERT INTO deposits (user_id, amount) VALUES (?, ?)",
                (user_id, amount)
            )
        
        db_connection.commit()

def add_referral(referrer_id, referred_id):
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM referrals WHERE referrer_id = ? AND referred_id = ?", 
                  (referrer_id, referred_id))
    if cursor.fetchone():
        return False
    
    cursor.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", 
                  (referrer_id, referred_id))
    cursor.execute("UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?", 
                  (referrer_id,))
    
    # ✅ التصحيح: منع القيم السالبة في المحاولات
    cursor.execute("UPDATE users SET games_played_today = MAX(0, games_played_today - 1) WHERE user_id = ?", 
                  (referrer_id,))
    
    # ✅ التصحيح: منح مكافأة 1.0 USDT للمُحيل
    referrer_user = get_user(referrer_id)
    if referrer_user:
        referrer_user['balance'] += 1.0
        referrer_user['total_earned'] += 1.0
        save_user(referrer_user)
        
        # تسجيل معاملة المكافأة للمُحيل
        cursor.execute(
            "INSERT INTO transactions (user_id, type, amount, description) VALUES (?, ?, ?, ?)",
            (referrer_id, 'referral_bonus', 1.0, f"مكافأة إحالة للمستخدم {referred_id}")
        )
    
    db_connection.commit()
    return True

def get_user_referrals(user_id):
    cursor = db_connection.cursor()
    cursor.execute('''
        SELECT u.user_id, u.first_name, u.username, r.timestamp 
        FROM referrals r 
        JOIN users u ON r.referred_id = u.user_id 
        WHERE r.referrer_id = ?
    ''', (user_id,))
    return cursor.fetchall()

# 🎯 إنشاء الأزرار
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
        InlineKeyboardButton("💎 باقات VIP", callback_data="vip_packages"),
        InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_3")
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

def get_vip_details(level):
    vip_data = {
        "bronze": {
            "name": "🟢 VIP برونزي",
            "price": 5.0,
            "mining_bonus": "+10% أرباح تعدين",
            "daily_bonus": 0.5,
            "features": [
                "+10% أرباح تعدين",
                "دعم سريع", 
                "مهام إضافية",
                "ألعاب حصرية"
            ]
        },
        "silver": {
            "name": "🔵 VIP فضى", 
            "price": 10.0,
            "mining_bonus": "+25% أرباح تعدين",
            "daily_bonus": 1.0,
            "features": [
                "+25% أرباح تعدين",
                "دعم مميز",
                "مهام حصرية", 
                "مكافآت يومية"
            ]
        },
        "gold": {
            "name": "🟡 VIP ذهبي",
            "price": 20.0,
            "mining_bonus": "+50% أرباح تعدين",
            "daily_bonus": 2.0,
            "features": [
                "+50% أرباح تعدين",
                "دعم فوري",
                "مكافآت يومية",
                "خصومات حصرية"
            ]
        }
    }
    return vip_data.get(level)

def create_vip_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("🟢 VIP برونزي - 5.0 USDT", callback_data="vip_bronze"))
    keyboard.add(InlineKeyboardButton("🔵 VIP فضى - 10.0 USDT", callback_data="vip_silver"))
    keyboard.add(InlineKeyboardButton("🟡 VIP ذهبي - 20.0 USDT", callback_data="vip_gold"))
    keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
    return keyboard

def create_withdraw_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("💳 تأكيد استخدام BEP20", callback_data="confirm_bep20"))
    keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
    return keyboard

def create_referral_keyboard(user_id):
    keyboard = InlineKeyboardMarkup()
    # ✅ إصلاح رابط الإحالة باستخدام يوزر البوت الصحيح
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
                        
                        # ✅ التصحيح: إشعار المُحيل بانضمام صديقه
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
            'total_deposits': 0.0
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

        💰 رصيدك: {user['balance']} USDT
        👥 عدد الإحالات: {user['referrals_count']}
        🎯 المحاولات المتبقية: {3 - user['games_played_today']}
        🏆 مستوى VIP: {user['vip_level']}
        """
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_main_menu())

# 🎯 معالجة الأزرار
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    
    if call.data == "main_menu":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🎮 **القائمة الرئيسية**\nاختر ما تريد من الأزرار أدناه:",
            reply_markup=create_main_menu(),
            parse_mode='Markdown'
        )
    
    elif call.data == "games_menu":
        remaining_games = 3 - user['games_played_today']
        games_text = f"""
        🎮 **قائمة الألعاب المتاحة**

        🎯 المحاولات المتبقية: {remaining_games}/3
        💰 الربح: 5 USDT كل 3 محاولات

        🎰 **السلوتس** - اختر الرموز واربح
        🎲 **النرد** - تحدى البوت واربح
        ⚽ **كرة القدم** - سجل الأهداف
        🏀 **السلة** - أحرز النقاط
        🎯 **السهام** - اصب الهدف

        💎 **كل 3 محاولات تربح 5 USDT!**
        """
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=games_text,
            reply_markup=create_games_menu(),
            parse_mode='Markdown'
        )
    
    elif call.data.startswith("game_"):
        if user['games_played_today'] >= 3:
            bot.answer_callback_query(call.id, "❌ استنفدت محاولاتك! ادعُ أصدقاءً لمحاولات إضافية")
            return
        
        game_type = call.data.replace("game_", "")
        game_name = get_game_name(game_type)
        
        if game_type == "slots":
            result = play_slots_game(user_id)
            game_display = " | ".join(result)
            result_text = f"🎰 **السلوتس**:\n{game_display}\n\n"
            
        elif game_type == "dice":
            user_dice, bot_dice, result = play_dice_game(user_id)
            result_text = f"🎲 **النرد**:\nنردك: {user_dice} | نرد البوت: {bot_dice}\nالنتيجة: {result}\n\n"
            
        elif game_type == "football":
            result = play_football_game(user_id)
            result_text = f"⚽ **كرة القدم**:\n" + "\n".join(result) + "\n\n"
            
        elif game_type == "basketball":
            result = play_basketball_game(user_id)
            result_text = f"🏀 **السلة**:\n" + "\n".join(result) + "\n\n"
            
        elif game_type == "darts":
            result = play_darts_game(user_id)
            result_text = f"🎯 **السهام**:\n" + "\n".join(result) + "\n\n"
        
        user['games_played_today'] += 1
        user['total_games_played'] += 1
        user['games_counter'] += 1
        
        win_amount = 0.0
        if user['games_counter'] >= 3:
            win_amount = 5.0
            user['games_counter'] = 0
            result_text += f"🎉 **مبروك! أكملت 3 محاولات وحصلت على 5.0 USDT!**\n\n"
        else:
            remaining = 3 - user['games_counter']
            result_text += f"📊 **تقدمك: {user['games_counter']}/3 محاولات**\n"
            result_text += f"🎯 **محاولاتك القادمة: {remaining} للحصول على 5.0 USDT**\n\n"
        
        if win_amount > 0:
            user['balance'] += win_amount
            user['total_earned'] += win_amount
        
        save_user(user)
        
        result_text += f"💰 **رصيدك الحالي: {user['balance']} USDT**\n"
        result_text += f"🎯 **المحاولات المتبقية: {3 - user['games_played_today']}**"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=result_text,
            reply_markup=create_main_menu(),
            parse_mode='Markdown'
        )

    # 🔧 قسم VIP المصحح - بداية الإصلاح
    elif call.data == "vip_packages":
        try:
            vip_text = """🎖️ *نظام العضويات VIP - ترقى لمستوى أفضل* 🎖️

اختر الباقة المناسبة وارتقِ بتجربتك:

*🟢 VIP برونزي*
💵 السعر: 5.0 USDT
📈 المكافأة: +10% أرباح تعدين  
🎁 المكافأة اليومية: 0.5 USDT

*🔵 VIP فضى*
💵 السعر: 10.0 USDT
📈 المكافأة: +25% أرباح تعدين
🎁 المكافأة اليومية: 1.0 USDT

*🟡 VIP ذهبي*
💵 السعر: 20.0 USDT
📈 المكافأة: +50% أرباح تعدين
🎁 المكافأة اليومية: 2.0 USDT

💎 *للشراء، أرسل USDT إلى عنوان المحفظة التالي على شبكة BEP20:*
`0xfc712c9985507a2eb44df1ddfe7f09ff7613a19b`

📝 *بعد الإيداع:*
1. أرسل screenshot للتحويل إلى @Trust_wallet_Support_3
2. اذكر نوع الباقة المطلوبة  
3. انتظر التفعيل خلال 24 ساعة

⚠️ *تأكد من استخدام شبكة BEP20 فقط!*"""

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=vip_text,
                reply_markup=create_vip_keyboard(),
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"خطأ في زر VIP: {e}")
            bot.answer_callback_query(call.id, "❌ حدث خطأ، حاول مرة أخرى")
    
    elif call.data.startswith("vip_"):
        vip_type = call.data.replace("vip_", "")
        vip_info = get_vip_details(vip_type)
        
        if not vip_info:
            bot.answer_callback_query(call.id, "❌ نوع VIP غير صحيح")
            return
        
        if user['balance'] < vip_info['price']:
            bot.answer_callback_query(call.id, f"❌ رصيدك غير كافٍ! السعر: {vip_info['price']} USDT")
            return
        
        confirmation_text = f"""
        🎖️ **تأكيد شراء {vip_info['name']}**

        💵 **السعر:** {vip_info['price']} USDT
        📈 **المكافأة:** {vip_info['mining_bonus']}
        🎁 **المكافأة اليومية:** {vip_info['daily_bonus']} USDT

        ⭐ **المزايا:**
        {chr(10).join(['   • ' + feature for feature in vip_info['features']])}

        💰 **رصيدك الحالي:** {user['balance']} USDT
        💎 **الرصيد بعد الشراء:** {user['balance'] - vip_info['price']} USDT

        ✅ **هل تريد المتابعة؟**
        """
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("✅ تأكيد الشراء", callback_data=f"confirm_vip_{vip_type}"),
            InlineKeyboardButton("❌ إلغاء", callback_data="vip_packages")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=confirmation_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    elif call.data.startswith("confirm_vip_"):
        vip_type = call.data.replace("confirm_vip_", "")
        vip_info = get_vip_details(vip_type)
        
        if not vip_info:
            bot.answer_callback_query(call.id, "❌ نوع VIP غير صحيح")
            return
        
        # خصم السعر من الرصيد
        user['balance'] -= vip_info['price']
        
        # تعيين مستوى VIP
        vip_levels = {"bronze": 1, "silver": 2, "gold": 3}
        user['vip_level'] = vip_levels.get(vip_type, 1)
        
        # تعيين تاريخ انتهاء VIP (30 يوم)
        user['vip_expiry'] = (datetime.now() + timedelta(days=30)).isoformat()
        user['last_daily_bonus'] = datetime.now().isoformat()
        
        save_user(user)
        
        success_text = f"""
        🎉 **تم تفعيل {vip_info['name']} بنجاح!**

        💎 **المزايا المفعلة:**
        📈 {vip_info['mining_bonus']}
        🎁 مكافأة يومية: {vip_info['daily_bonus']} USDT
        ⭐ {chr(10).join(['• ' + feature for feature in vip_info['features']])}

        💰 **رصيدك الحالي:** {user['balance']} USDT
        🚀 **سيتم إيداع المكافأة اليومية تلقائياً!**

        **استمتع بالمزايا الحصرية! 🏆**
        """
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=success_text,
            reply_markup=create_main_menu(),
            parse_mode='Markdown'
        )
        
        bot.answer_callback_query(call.id, f"✅ تم تفعيل {vip_info['name']} بنجاح!")
    # 🔧 قسم VIP المصحح - نهاية الإصلاح
    
    elif call.data == "withdraw":
        if user['balance'] < 100.0:
            bot.answer_callback_query(
                call.id, 
                f"❌ الحد الأدنى للسحب 100 USDT! رصيدك: {user['balance']} USDT"
            )
            return
        
        if user['total_deposits'] < 10.0:
            bot.answer_callback_query(
                call.id,
                f"❌ يجب أن تكون قد أودعت 10 USDT على الأقل للسحب!\n"
                f"💰 إيداعاتك الحالية: {user['total_deposits']} USDT"
            )
            return
        
        withdraw_text = f"""
        💰 **طلب سحب رصيد**

        ✅ **الشروط المطلوبة:**
        💳 الرصيد المتاح: {user['balance']} USDT ✓
        📋 الحد الأدنى للسحب: 100 USDT ✓
        💎 إجمالي الإيداعات: {user['total_deposits']} USDT ✓

        🔴 **⚠️ تنبيه أمني مهم:**
        **يجب أن يكون الإيداع على شبكة BEP20 فقط!**
        
        • تأكد من اختيار شبكة BEP20 عند الإرسال
        • لا ترسل على شبكة ERC20 أو غيرها
        • الأموال المرسلة على الشبكات الخاطئة **ستضيع ولا يمكن استرجاعها**

        💎 **عنوان المحفظة (BEP20 فقط):**
        `0xfc712c9985507a2eb44df1ddfe7f09ff7613a19b`

        📝 **للسحب يرجى إرسال:**
        1. المبلغ المطلوب (100 USDT minimum)
        2. عنوان محفظتك (للتأكد)
        3. screenshot من التحويل
        4. تأكيد أنك استخدمت شبكة BEP20

        ⏰ **مدة المعالجة:** 24-48 ساعة
        🔒 **عمولة الشبكة:** يتحملها المستخدم
        """

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=withdraw_text,
            reply_markup=create_withdraw_keyboard(),
            parse_mode='Markdown'
        )
    
    elif call.data == "confirm_bep20":
        confirmation_text = """
        ✅ **تم تأكيد فهمك لشروط الأمان**

        🛡️ **لقد فهمت أن:**
        • الإيداع يجب أن يكون على شبكة BEP20 فقط
        • الأموال المرسلة على شبكات أخرى **ستضيع**
        • العمولة على الشبكة تتحملها أنت

        💰 **للإيداع الآمن:**
        1. اختر شبكة BEP20 في محفظتك
        2. تأكد من العنوان بشكل دقيق
        3. أرسل المبلغ المطلوب
        4. احتفظ بـ screenshot للتحويل

        📞 **للطوارئ أو الأسئلة:**
        @Trust_wallet_Support_3
        """

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=confirmation_text,
            parse_mode='Markdown'
        )
    
    elif call.data == "referral":
        keyboard, referral_link = create_referral_keyboard(user_id)
        referral_text = f"""
        👥 **نظام الإحالات**

        🔗 **رابط الدعوة الخاص بك:**
        `{referral_link}`

        💰 **مكافآت الإحالة:**
        • أنت تحصل على 1.0 USDT
        • صديقك يحصل على 1.0 USDT  
        • تحصل على محاولة لعب إضافية

        📊 **إحصائياتك:**
        👥 عدد الإحالات: {user['referrals_count']}
        💰 أرباح الإحالات: {user['referrals_count'] * 1.0} USDT
        🎯 محاولات إضافية: {user['referrals_count']}

        🎯 **كل إحالة = 1 USDT + محاولة لعب إضافية!**
        """
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=referral_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    elif call.data == "copy_link":
        bot.answer_callback_query(call.id, "✅ تم نسخ رابط الدعوة إلى الحافظة")
    
    elif call.data == "my_referrals":
        referrals_list = get_user_referrals(user_id)
        if referrals_list:
            referrals_text = "📊 **قائمة الإحالات الخاصة بك:**\n\n"
            for idx, referral in enumerate(referrals_list, 1):
                referred_id, first_name, username, timestamp = referral
                user_link = f"@{username}" if username else first_name
                referrals_text += f"{idx}. {user_link} - {timestamp[:10]}\n"
        else:
            referrals_text = "❌ لم تقم بدعوة أي أصدقاء بعد.\nاستخدم رابط الدعوة لبدء كسب USDT والمحاولات الإضافية!"
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="referral"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=referrals_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    elif call.data == "profile":
        remaining_games = 3 - user['games_played_today']
        profile_text = f"""
        📊 **الملف الشخصي**

        👤 **المستخدم:** {user['first_name']} {user.get('last_name', '')}
        🆔 **المعرف:** `{user_id}`
        💰 **الرصيد:** {user['balance']} USDT
        👥 **الإحالات:** {user['referrals_count']} مستخدم
        🏆 **مستوى VIP:** {user['vip_level']}
        🎯 **المحاولات المتبقية:** {remaining_games}/3
        💎 **إجمالي الأرباح:** {user['total_earned']} USDT
        💳 **إجمالي الإيداعات:** {user['total_deposits']} USDT
        📅 **تاريخ التسجيل:** {user['registration_date'][:10]}
        """
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=profile_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

def get_game_name(game_type):
    names = {
        "slots": "🎰 السلوتس",
        "dice": "🎲 النرد", 
        "football": "⚽ كرة القدم",
        "basketball": "🏀 السلة",
        "darts": "🎯 السهام"
    }
    return names.get(game_type, "لعبة")

# 👑 أوامر المشرفين
@bot.message_handler(commands=['addbalance'])
def add_balance_admin(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "❌ استخدم: /addbalance [user_id] [amount]")
            return
        
        target_user_id = int(parts[1])
        amount = float(parts[2])
        
        add_balance(target_user_id, amount, f"إضافة إدارية بواسطة {message.from_user.id}", is_deposit=True)
        
        target_user = get_user(target_user_id)
        bot.send_message(
            message.chat.id, 
            f"✅ تم إضافة {amount} USDT للمستخدم {target_user_id}\n"
            f"💰 الرصيد الجديد: {target_user['balance']} USDT\n"
            f"💳 إجمالي الإيداعات: {target_user['total_deposits']} USDT"
        )
        
        try:
            bot.send_message(
                target_user_id,
                f"🎉 تم إضافة {amount} USDT إلى رصيدك!\n"
                f"💰 رصيدك الحالي: {target_user['balance']} USDT\n"
                f"💳 إجمالي إيداعاتك: {target_user['total_deposits']} USDT"
            )
        except:
            pass
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setbalance'])
def set_balance_admin(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "❌ استخدم: /setbalance [user_id] [amount]")
            return
        
        target_user_id = int(parts[1])
        amount = float(parts[2])
        
        user = get_user(target_user_id)
        if user:
            old_balance = user['balance']
            user['balance'] = amount
            save_user(user)
            
            bot.send_message(
                message.chat.id, 
                f"✅ تم تعيين رصيد المستخدم {target_user_id}\n"
                f"📊 الرصيد السابق: {old_balance} USDT\n"
                f"💰 الرصيد الجديد: {amount} USDT"
            )
        else:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['userinfo'])
def userinfo_admin(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ استخدم: /userinfo [user_id]")
            return
        
        target_user_id = int(parts[1])
        user = get_user(target_user_id)
        
        if user:
            remaining_games = 3 - user['games_played_today']
            info_text = f"""
📊 **معلومات المستخدم:**

🆔 **الآيدي:** `{user['user_id']}`
👤 **الاسم:** {user['first_name']} {user.get('last_name', '')}
📛 **اليوزرنيم:** @{user.get('username', 'غير متوفر')}
💰 **الرصيد:** {user['balance']} USDT
👥 **الإحالات:** {user['referrals_count']}
🏆 **مستوى VIP:** {user['vip_level']}
🎯 **المحاولات المتبقية:** {remaining_games}/3
💎 **إجمالي الأرباح:** {user['total_earned']} USDT
💳 **إجمالي الإيداعات:** {user['total_deposits']} USDT
📅 **تاريخ التسجيل:** {user['registration_date'][:10]}
"""
            bot.send_message(message.chat.id, info_text, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['myid'])
def my_id_command(message):
    user_id = message.from_user.id
    is_admin = "✅ (مشرف)" if user_id in ADMIN_IDS else "❌ (ليس مشرف)"
    
    bot.send_message(
        message.chat.id,
        f"🆔 **آيديك الخاص:** `{user_id}`\n"
        f"🎯 **صلاحية المشرف:** {is_admin}",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['admins'])
def show_admins(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    admins_list = "\n".join([f"• `{admin_id}`" for admin_id in ADMIN_IDS])
    bot.send_message(
        message.chat.id,
        f"👑 **قائمة المشرفين:**\n{admins_list}\n\n"
        f"📊 **عدد المشرفين:** {len(ADMIN_IDS)}",
        parse_mode='Markdown'
    )

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
            "timestamp": datetime.now().isoformat(),
            "total_users": total_users,
            "total_referrals": total_referrals,
            "version": "6.0",
            "performance": "excellent"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}, 500

# 🌐 إعداد ويب هوك للتشغيل على Render
@app.route('/')
def index():
    return "🤖 البوت يعمل بشكل صحيح! استخدم /start في التلجرام"

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
    print("🚀 بدأ تشغيل البوت على Render بنظام Webhook...")
    
    try:
        # إعداد ويب هوك
        bot.remove_webhook()
        time.sleep(2)
        
        # ✅ استخدام Webhook مع الرابط الصحيح
        WEBHOOK_URL = f'https://usdt-bot-working.onrender.com/{BOT_TOKEN}'
        bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ Webhook مضبوط على: {WEBHOOK_URL}")
        
        # تشغيل الخادم
        PORT = int(os.environ.get('PORT', 10000))
        print(f"🌐 بدأ تشغيل الخادم على المنفذ {PORT}")
        app.run(host='0.0.0.0', port=PORT, debug=False)
        
    except Exception as e:
        print(f"❌ خطأ في التشغيل: {e}")
