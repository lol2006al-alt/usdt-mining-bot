from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import threading
import time
from datetime import datetime, timedelta
import os
import random

# 🔧 فقط قم بتغيير التوكن هنا 👇
BOT_TOKEN = "8385331860:AAEcFqGY4vXORINuGUHGXpmSN9-Ft1uEMj8"  # 🔄 ضع توكنك الجديد هنا
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
    
    # ✅ تحديث الإحالات الجديدة إذا كان لديه محاولات سحب
    cursor.execute("SELECT withdrawal_attempts FROM users WHERE user_id = ?", (referrer_id,))
    result = cursor.fetchone()
    if result and result[0] > 0:
        cursor.execute("UPDATE users SET new_referrals_count = new_referrals_count + 1 WHERE user_id = ?", 
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

# 🔧 دوال المساعدة - الدوال الجديدة
def get_vip_bonus_info(vip_level):
    """معلومات مكافآت VIP"""
    bonuses = {
        1: {"daily_bonus": 0.5, "extra_games": 2, "name": "برونزي"},
        2: {"daily_bonus": 1.0, "extra_games": 4, "name": "فضى"},
        3: {"daily_bonus": 2.0, "extra_games": 6, "name": "ذهبي"}
    }
    return bonuses.get(vip_level, {"daily_bonus": 0, "extra_games": 0, "name": "لا يوجد"})

def get_next_bonus_time(last_bonus_time):
    """حساب وقت المكافأة التالية"""
    if not last_bonus_time:
        return "الآن!"
    
    last_time = datetime.fromisoformat(last_bonus_time)
    next_time = last_time + timedelta(hours=24)
    now = datetime.now()
    
    if now >= next_time:
        return "الآن!"
    else:
        remaining = next_time - now
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        return f"{hours}س {minutes}د"

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
    # ✅ رابط الإحالة الخاص بكل مستخدم
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
        vip_info = get_vip_bonus_info(user['vip_level'])
        extra_games = vip_info['extra_games'] if user['vip_level'] > 0 else 0
        total_remaining = remaining_games + extra_games
        
        games_text = f"""
        🎮 **قائمة الألعاب المتاحة**

        🎯 المحاولات المتبقية: {total_remaining} ({remaining_games} أساسية + {extra_games} إضافية)
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
        
        result_text += f"💰 **رصيدك الحالي: {user['balance']:.1f} USDT**\n"
        result_text += f"🎯 **المحاولات المتبقية: {3 - user['games_played_today']}**"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=result_text,
            reply_markup=create_main_menu(),
            parse_mode='Markdown'
        )

    # 🎖️ نظام VIP المبسط والفعّال
    elif call.data == "vip_packages":
        try:
            vip_text = """
🎖️ *باقات VIP المتاحة*

🟢 *برونزي* - 5 USDT
• مكافأة يومية: 0.5 USDT
• +10% أرباح تعدين
• +2 محاولات لعب إضافية يومياً
• مؤتمر المكافآت المباشر

🔵 *فضى* - 10 USDT  
• مكافأة يومية: 1.0 USDT
• +25% أرباح تعدين
• +4 محاولات لعب إضافية يومياً
• مؤتمر المكافآت المباشر

🟡 *ذهبي* - 20 USDT
• مكافأة يومية: 2.0 USDT  
• +50% أرباح تعدين
• +6 محاولات لعب إضافية يومياً
• مؤتمر المكافآت المباشر

⏰ *المكافآت تصل تلقائياً كل 24 ساعة*

اختر الباقة المناسبة:"""
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=vip_text,
                reply_markup=create_vip_keyboard(),
                parse_mode='Markdown'
            )
            bot.answer_callback_query(call.id, "🎖️")
        except Exception as e:
            print(f"خطأ في VIP: {e}")
            bot.answer_callback_query(call.id, "❌ حدث خطأ")

    elif call.data.startswith("buy_"):
        vip_type = call.data.replace("buy_", "")
        prices = {"bronze": 5.0, "silver": 10.0, "gold": 20.0}
        names = {"bronze": "🟢 برونزي", "silver": "🔵 فضى", "gold": "🟡 ذهبي"}
        extra_games = {"bronze": 2, "silver": 4, "gold": 6}  # 🆕 محاولات إضافية
        
        price = prices.get(vip_type)
        name = names.get(vip_type)
        games_bonus = extra_games.get(vip_type, 0)
        
        if not price:
            bot.answer_callback_query(call.id, "❌ نوع VIP غير صحيح")
            return
        
        if user['balance'] >= price:
            user['balance'] -= price
            user['vip_level'] = {"bronze": 1, "silver": 2, "gold": 3}[vip_type]
            user['vip_expiry'] = (datetime.now() + timedelta(days=30)).isoformat()
            # 🆕 إضافة المحاولات الإضافية
            user['games_played_today'] = max(0, user['games_played_today'] - games_bonus)
            user['last_daily_bonus'] = datetime.now().isoformat()
            
            save_user(user)
            
            success_msg = f"""
🎉 *تم تفعيل {name} بنجاح!*

💰 تم خصم {price} USDT
💎 رصيدك الجديد: {user['balance']:.1f} USDT
🎯 *تم إضافة {games_bonus} محاولات لعب إضافية!*

⭐ **المزايا المشغلة:**
• مكافأة يومية: {get_vip_bonus_info(user['vip_level'])['daily_bonus']} USDT
• محاولات إضافية: {games_bonus}
• أرباح مضاعفة في الألعاب

⏰ المكافأة القادمة: بعد 24 ساعة
استمتع! 🏆"""
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=success_msg,
                reply_markup=create_main_menu(),
                parse_mode='Markdown'
            )
        else:
            bot.answer_callback_query(call.id, f"❌ رصيدك غير كافٍ! تحتاج {price} USDT")

    # 💰 نظام السحب مع الشروط الجديدة
    elif call.data == "withdraw":
        # ✅ تسجيل محاولة السحب الأولى
        if user['withdrawal_attempts'] == 0:
            user['withdrawal_attempts'] = 1
            save_user(user)
            
            # تسجيل محاولة السحب في جدول منفصل
            cursor = db_connection.cursor()
            cursor.execute(
                "INSERT INTO withdrawal_attempts (user_id, referrals_before) VALUES (?, ?)",
                (user_id, user['referrals_count'])
            )
            db_connection.commit()

        # ✅ التحقق من الشروط
        error_messages = []
        
        if user['balance'] < 100.0:
            error_messages.append(f"❌ الرصيد: {user['balance']:.1f}/100 USDT")
        
        if user['total_deposits'] < 10.0:
            error_messages.append(f"❌ الإيداعات: {user['total_deposits']:.1f}/10 USDT")
        
        # ✅ حساب الإحالات المطلوبة بعد أول محاولة سحب
        required_new_referrals = 10
        if user['withdrawal_attempts'] > 0:
            cursor = db_connection.cursor()
            cursor.execute("SELECT referrals_before FROM withdrawal_attempts WHERE user_id = ? ORDER BY attempt_date LIMIT 1", (user_id,))
            result = cursor.fetchone()
            if result:
                referrals_before = result[0]
                current_referrals = user['referrals_count']
                new_referrals = current_referrals - referrals_before
                
                if new_referrals < required_new_referrals:
                    error_messages.append(f"❌ الإحالات الجديدة: {new_referrals}/10")
            else:
                error_messages.append(f"❌ الإحالات الجديدة: 0/10")
        
        # ✅ إذا كان هناك أخطاء، عرضها
        if error_messages:
            error_text = "💳 *شروط السحب غير مكتملة:*\n\n" + "\n".join(error_messages)
            error_text += f"\n\n📊 *إحصائياتك:*\n💰 الرصيد: {user['balance']:.1f} USDT\n💳 الإيداعات: {user['total_deposits']:.1f} USDT\n👥 الإحالات: {user['referrals_count']}"
            
            bot.answer_callback_query(call.id, "❌ شروط السحب غير مكتملة")
            bot.send_message(
                call.message.chat.id,
                error_text,
                parse_mode='Markdown'
            )
            return
        
        # ✅ إذا اجتاز جميع الشروط، عرض صفحة السحب
        withdraw_text = f"""
💰 **طلب سحب رصيد**

✅ **تم استيفاء جميع الشروط:**
💳 الرصيد: {user['balance']:.1f} USDT ✓
💰 الإيداعات: {user['total_deposits']:.1f} USDT ✓  
👥 الإحالات الجديدة: 10/10 ✓

🔴 **⚠️ تنبيه أمني مهم:**
**يجب أن يكون الإيداع على شبكة BEP20 فقط!**

💎 **عنوان المحفظة (BEP20 فقط):**
`0xfc712c9985507a2eb44df1ddfe7f09ff7613a19b`

📝 **للسحب يرجى إرسال:**
1. المبلغ المطلوب (100 USDT حد أدنى)
2. عنوان محفظتك
3. screenshot من التحويل
4. تأكيد استخدام شبكة BEP20

⏰ **مدة المعالجة:** 24-48 ساعة"""

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
        vip_info = get_vip_bonus_info(user['vip_level'])
        
        # 🆕 حساب المؤقتات
        bonus_timer = get_next_bonus_time(user.get('last_daily_bonus'))
        
        # 🆕 حساب المحاولات الإضافية لـ VIP
        extra_games = vip_info['extra_games'] if user['vip_level'] > 0 else 0
        total_remaining = remaining_games + extra_games
        
        # ✅ حساب الإحالات الجديدة المطلوبة للسحب
        new_referrals_info = ""
        if user['withdrawal_attempts'] > 0:
            cursor = db_connection.cursor()
            cursor.execute("SELECT referrals_before FROM withdrawal_attempts WHERE user_id = ? ORDER BY attempt_date LIMIT 1", (user_id,))
            result = cursor.fetchone()
            if result:
                referrals_before = result[0]
                current_referrals = user['referrals_count']
                new_referrals = current_referrals - referrals_before
                new_referrals_info = f"📈 **الإحالات الجديدة:** {new_referrals}/10\n"
        
        profile_text = f"""
📊 **الملف الشخصي**

👤 **المستخدم:** {user['first_name']} {user.get('last_name', '')}
🆔 **المعرف:** `{user_id}`
💰 **الرصيد:** {user['balance']:.1f} USDT
👥 **الإحالات:** {user['referrals_count']} مستخدم
{new_referrals_info}🏆 **مستوى VIP:** {vip_info['name']}
🎯 **المحاولات المتبقية:** {total_remaining} ({remaining_games} أساسية + {extra_games} إضافية)

{'⏰ **مكافأة التعدين:** ' + bonus_timer + ' ⏳' if user['vip_level'] > 0 else '💡 **انضم لـ VIP للحصول على مكافآت يومية!**'}

💎 **إجمالي الأرباح:** {user['total_earned']:.1f} USDT
💳 **إجمالي الإيداعات:** {user['total_deposits']:.1f} USDT
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

# 👑 أوامر المشرفين - الإصدار المحسن
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
        
        # التحقق من وجود المستخدم
        target_user = get_user(target_user_id)
        if not target_user:
            bot.send_message(message.chat.id, f"❌ المستخدم {target_user_id} غير موجود!")
            return
        
        add_balance(target_user_id, amount, f"إضافة إدارية بواسطة {message.from_user.id}", is_deposit=True)
        
        # الحصول على بيانات المستخدم المحدثة
        target_user = get_user(target_user_id)
        bot.send_message(
            message.chat.id, 
            f"✅ تم إضافة {amount} USDT للمستخدم {target_user_id}\n"
            f"💰 الرصيد الجديد: {target_user['balance']:.1f} USDT\n"
            f"💳 إجمالي الإيداعات: {target_user['total_deposits']:.1f} USDT"
        )
        
        # إرسال إشعار للمستخدم
        try:
            bot.send_message(
                target_user_id,
                f"🎉 تم إضافة {amount} USDT إلى رصيدك!\n"
                f"💰 رصيدك الحالي: {target_user['balance']:.1f} USDT\n"
                f"💳 إجمالي إيداعاتك: {target_user['total_deposits']:.1f} USDT"
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
                f"📊 الرصيد السابق: {old_balance:.1f} USDT\n"
                f"💰 الرصيد الجديد: {amount:.1f} USDT"
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
            vip_info = get_vip_bonus_info(user['vip_level'])
            extra_games = vip_info['extra_games'] if user['vip_level'] > 0 else 0
            total_remaining = remaining_games + extra_games
            bonus_timer = get_next_bonus_time(user.get('last_daily_bonus'))
            
            info_text = f"""
📊 **معلومات المستخدم:**

🆔 **الآيدي:** `{user['user_id']}`
👤 **الاسم:** {user['first_name']} {user.get('last_name', '')}
📛 **اليوزرنيم:** @{user.get('username', 'غير متوفر')}
💰 **الرصيد:** {user['balance']:.1f} USDT
👥 **الإحالات:** {user['referrals_count']}
🏆 **مستوى VIP:** {vip_info['name']}
🎯 **المحاولات المتبقية:** {total_remaining} ({remaining_games} أساسية + {extra_games} إضافية)
⏰ **مكافأة التعدين:** {bonus_timer}
💎 **إجمالي الأرباح:** {user['total_earned']:.1f} USDT
💳 **إجمالي الإيداعات:** {user['total_deposits']:.1f} USDT
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

# 🆕 أمر المكافآت اليومية
@bot.message_handler(commands=['dailybonus'])
def daily_bonus_command(message):
    """منح المكافآت اليومية للمستخدمين"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ حسابك غير مسجل في النظام!")
        return
    
    vip_info = get_vip_bonus_info(user['vip_level'])
    
    # التحقق إذا حان وقت المكافأة
    can_claim = True
    if user.get('last_daily_bonus'):
        last_time = datetime.fromisoformat(user['last_daily_bonus'])
        next_time = last_time + timedelta(hours=24)
        can_claim = datetime.now() >= next_time
    
    if user['vip_level'] == 0:
        bot.send_message(message.chat.id, "❌ هذه الميزة متاحة لأعضاء VIP فقط!")
        return
    
    if not can_claim:
        next_time = get_next_bonus_time(user.get('last_daily_bonus'))
        bot.send_message(message.chat.id, f"⏳ لم يحن وقت المكافأة بعد!\n⏰ عود بعد: {next_time}")
        return
    
    # منح المكافأة
    bonus_amount = vip_info['daily_bonus']
    add_balance(user_id, bonus_amount, f"مكافأة تعدين VIP {vip_info['name']}")
    
    # تحديث وقت المكافأة
    user['last_daily_bonus'] = datetime.now().isoformat()
    save_user(user)
    
    bot.send_message(
        message.chat.id,
        f"🎉 **تم استلام مكافأة التعدين!**\n\n"
        f"💰 المبلغ: {bonus_amount} USDT\n"
        f"💎 الرصيد الجديد: {user['balance'] + bonus_amount:.1f} USDT\n"
        f"⏰ المكافأة القادمة: بعد 24 ساعة\n\n"
        f"استمر في اللعب لكسب المزيد! 🎮"
    )

# 🆕 الأوامر الجديدة المطلوبة
@bot.message_handler(commands=['debug'])
def debug_bot(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        # التحقق من اتصال البوت
        bot_info = bot.get_me()
        
        # التحقق من قاعدة البيانات
        db_status = "✅ متصلة" if db_connection else "❌ غير متصلة"
        
        debug_text = f"""
🐛 **معلومات التصحيح:**

🤖 البوت: {bot_info.first_name} (@{bot_info.username})
🗃️ قاعدة البيانات: {db_status}
🆔 آيديك: {message.from_user.id}
📊 الإصدار: 8.0
"""
        bot.send_message(message.chat.id, debug_text)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ في التصحيح: {e}")

@bot.message_handler(commands=['checkdb'])
def check_database(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        cursor = db_connection.cursor()
        
        # التحقق من اتصال قاعدة البيانات
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        status_text = f"""
📊 **حالة قاعدة البيانات:**

✅ متصلة: نعم
👥 عدد المستخدمين: {user_count}
🗃️ الجداول: {', '.join([table[0] for table in tables])}
"""
        bot.send_message(message.chat.id, status_text)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ في قاعدة البيانات: {e}")

@bot.message_handler(commands=['createaccount'])
def create_account(message):
    try:
        user_id = message.from_user.id
        
        # إنشاء المستخدم مباشرة
        cursor = db_connection.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_name, balance, games_played_today)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name or '',
            0.0,  # رصيد ابتدائي
            3     # محاولات لعب
        ))
        
        db_connection.commit()
        
        bot.send_message(
            message.chat.id,
            f"✅ **تم إنشاء حسابك بنجاح!**\n\n"
            f"🆔 الآيدي: `{user_id}`\n"
            f"👤 الاسم: {message.from_user.first_name}\n"
            f"💰 الرصيد: 0.0 USDT\n"
            f"🎯 المحاولات: 3\n\n"
            f"يمكنك الآن استخدام `/addbalance {user_id} 20.0`",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ في إنشاء الحساب: {e}")

@bot.message_handler(commands=['allusers'])
def all_users_admin(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    cursor = db_connection.cursor()
    cursor.execute("SELECT user_id, first_name, username, balance FROM users LIMIT 50")
    users = cursor.fetchall()
    
    if users:
        users_text = "📊 **آخر 50 مستخدم:**\n\n"
        for user in users:
            user_id, first_name, username, balance = user
            user_link = f"@{username}" if username else first_name
            users_text += f"🆔 `{user_id}` - {user_link} - 💰 {balance} USDT\n"
    else:
        users_text = "❌ لا يوجد مستخدمين!"
    
    bot.send_message(message.chat.id, users_text, parse_mode='Markdown')

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
            "version": "8.0",
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
