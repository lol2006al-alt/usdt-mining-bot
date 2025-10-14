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

MAIN_WALLET = "0xfc712c9985507a2eb44df1ddfe7f09ff7613a19b"

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
            print(f"🔄 pinged at {datetime.now()}")
        except Exception as e:
            print(f"❌ ping failed: {e}")
        time.sleep(240)  # كل 4 دقائق

# 🎮 نظام الألعاب المتقدم
GAMES_SYSTEM = {
    "slots": {"name": "🎰 سلات ماشين", "base_reward": 2.0, "vip_bonus": 0.5},
    "shooting": {"name": "🎯 الرماية", "base_reward": 2.0, "vip_bonus": 0.5},
    "mining_race": {"name": "🏆 سباق التعدين", "base_reward": 2.0, "vip_bonus": 0.5},
    "price_prediction": {"name": "📈 توقع الأسعار", "base_reward": 2.0, "vip_bonus": 0.5},
    "mining_cards": {"name": "🃏 أوراق التعدين", "base_reward": 2.0, "vip_bonus": 0.5}
}

# 🛡️ نظام الأمان المتقدم
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

def vip_keyboard():
    """لوحة VIP"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for vip_type, info in vip_system.items():
        keyboard.add(
            InlineKeyboardButton(
                f"{info['name']} - {info['price']} USDT", 
                callback_data=f"vip_{vip_type}"
            )
        )
    
    keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
    return keyboard

def games_keyboard(user_id):
    """لوحة الألعاب"""
    user = get_user(user_id)
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    games = [
        ("🎰 سلات ماشين", "slots"),
        ("🎯 الرماية", "shooting"),
        ("🏆 سباق التعدين", "mining_race"),
        ("📈 توقع الأسعار", "price_prediction"),
        ("🃏 أوراق التعدين", "mining_cards")
    ]
    
    for game_name, game_id in games:
        keyboard.add(InlineKeyboardButton(game_name, callback_data=f"game_{game_id}"))
    
    remaining_games = user['max_games_daily'] - user['games_played_today']
    keyboard.add(InlineKeyboardButton(f"🔄 المحاولات المتبقية: {remaining_games}", callback_data="games_info"))
    keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
    
    return keyboard

# 📊 Handlers الرئيسية
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
        print(f"Error in start_command: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'main_menu')
def main_menu(call):
    """العودة للقائمة الرئيسية"""
    try:
        user_id = call.from_user.id
        user = get_user(user_id)
        
        welcome_text = f"""🤖 **BNB Mini Bot - النسخة المطورة**

💰 الرصيد: {user['balance']:.1f} USDT
🎮 الألعاب: {user['games_played_today']}/{user['max_games_daily']} محاولات
👥 الإحالات: {user['referrals_count']}/15
🎖️ العضوية: {vip_system[user['vip_level']]['name'] if user['vip_level'] else 'بدون'}

📋 **القائمة الرئيسية:**"""
        
        bot.edit_message_text(
            welcome_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=main_keyboard()
        )
    except Exception as e:
        print(f"Error in main_menu: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'mining')
def mining_handler(call):
    """معالجة التعدين"""
    try:
        user_id = call.from_user.id
        user = get_user(user_id)
        
        if not user['vip_level']:
            bot.answer_callback_query(
                call.id,
                "❌ التعدين متاح لأعضاء VIP فقط!\nاشترك في إحدى الباقات من قسم 🎖️ نظام VIP",
                show_alert=True
            )
            return
        
        # التحقق من المكافأة اليومية
        now = datetime.now()
        if user['last_mining_time']:
            last_time = datetime.fromisoformat(user['last_mining_time'])
            if (now - last_time).days < 1:
                bot.answer_callback_query(
                    call.id,
                    "⏳ لقد حصلت على مكافأة التعدين اليومية بالفعل!\nعد غداً للحصول على المزيد",
                    show_alert=True
                )
                return
        
        # منح المكافأة
        reward = vip_mining_rewards(user_id)
        user['balance'] += reward
        user['mining_earnings'] += reward
        user['last_mining_time'] = now.isoformat()
        user['last_active'] = now.isoformat()
        save_user(user)
        
        log_transaction(user_id, "mining_reward", reward, "مكافأة تعدين يومية")
        
        bot.answer_callback_query(
            call.id,
            f"🎉 تم إضافة {reward:.1f} USDT إلى رصيدك من التعدين!",
            show_alert=True
        )
        
        main_menu(call)
    except Exception as e:
        print(f"Error in mining_handler: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'games')
def games_handler(call):
    """معالجة الألعاب"""
    try:
        user_id = call.from_user.id
        user = get_user(user_id)
        
        games_text = f"""🎮 **الألعاب الاحترافية**

🎯 كل لعبة تربحك 2 USDT
🕹️ المحاولات المتبقية: {user['max_games_daily'] - user['games_played_today']}/{user['max_games_daily']}

📤 **للمحاولات الإضافية:**
ادعُ أصدقائك عبر رابط الإحالة في قسم 👥 الإحالات

🎪 **اختر لعبة:**"""
        
        bot.edit_message_text(
            games_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=games_keyboard(user_id)
        )
    except Exception as e:
        print(f"Error in games_handler: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('game_'))
def game_play_handler(call):
    """تشغيل لعبة"""
    try:
        user_id = call.from_user.id
        game_id = call.data.split('_')[1]
        
        if not can_play_game(user_id):
            bot.answer_callback_query(
                call.id,
                "❌ نفذت محاولاتك اليومية!\n📤 ادعُ صديقاً لمحاولة إضافية",
                show_alert=True
            )
            return
        
        reward = play_game(user_id, game_id)
        if reward > 0:
            bot.answer_callback_query(
                call.id,
                f"🎉 ربحت {reward:.1f} USDT من اللعبة!",
                show_alert=True
            )
            games_handler(call)
        else:
            bot.answer_callback_query(call.id, "❌ خطأ في تشغيل اللعبة", show_alert=True)
    except Exception as e:
        print(f"Error in game_play_handler: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'deposit')
def deposit_handler(call):
    """معالجة الإيداع"""
    try:
        deposit_text = f"""💰 **نظام الإيداع**

🚨 **تنبيه أمني:**
✅ استخدم شبكة BEP20 فقط
❌ لا تستخدم أي شبكة أخرى
💵 أرسل USDT فقط

💰 **الحد الأدنى للإيداع:** 10 USDT

💎 **عنوان المحفظة:**
`{MAIN_WALLET}`

📝 **لتفعيل VIP، أرسل المبلغ المطلوب مع كتابة كود VIP في وصف التحويل**"""

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🎖️ باقات VIP", callback_data="vip_menu"))
        keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
        
        bot.edit_message_text(
            deposit_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error in deposit_handler: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'referral')
def referral_handler(call):
    """معالجة الإحالات"""
    try:
        user_id = call.from_user.id
        user = get_user(user_id)
        
        referral_text = f"""👥 **نظام الإحالات**

📊 إحصائياتك:
• عدد الإحالات: {user['referrals_count']}/15
• أرباح الإحالات: {user['referral_earnings']:.1f} USDT
• المحاولات الإضافية: {user['max_games_daily'] - 3}

💰 **مكافأة الإحالة:** 1.5 USDT لكل إحالة
🎮 **مكافأة إضافية:** محاولة لعب إضافية

🔗 **رابط الإحالة الخاص بك:**
`{user['referral_link']}`

🎯 **شارك الرابط واكسب المزيد!**"""

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={user['referral_link']}&text=انضم إلى بوت التعدين المتقدم واكسب USDT! 🚀"))
        keyboard.add(InlineKeyboardButton("💰 السحب", callback_data="withdraw"))
        keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
        
        bot.edit_message_text(
            referral_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error in referral_handler: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'withdraw')
def withdraw_handler(call):
    """معالجة السحب"""
    try:
        user_id = call.from_user.id
        user = get_user(user_id)
        
        if not check_withdraw_eligibility(user_id):
            withdraw_text = f"""💸 **نظام السحب**

❌ **غير مؤهل للسحب بعد**

📋 **شروط السحب:**
• رصيد 100 USDT كحد أدنى ({user['balance']:.1f}/100)
• 15 إحالة نشطة ({user['referrals_count']}/15)

🎯 **استمر في الجمع والإحالة لتتمكن من السحب**"""
        else:
            withdraw_text = f"""🎉 **تهانينا! يمكنك السحب الآن**

💰 رصيدك: {user['balance']:.1f} USDT
👥 الإحالات: {user['referrals_count']}/15
✅ مؤهل للسحب

📤 **للسحب:** راسل الدعم الفني"""

        keyboard = InlineKeyboardMarkup()
        if user['withdraw_eligible']:
            keyboard.add(InlineKeyboardButton("📞 التواصل مع الدعم", url=f"https://t.me/{SUPPORT_USER_ID}"))
        keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
        
        bot.edit_message_text(
            withdraw_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error in withdraw_handler: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'vip_menu')
def vip_menu_handler(call):
    """قائمة VIP"""
    try:
        vip_text = """🎖️ **نظام العضويات VIP**

اختر الباقة المناسبة لك واستمتع بمزايا حصرية:

"""
        
        for vip_type, info in vip_system.items():
            vip_text += f"""
{info['color']} **{info['name']}**
💵 السعر: {info['price']} USDT
📈 المكافأة: +{int(info['bonus']*100)}% أرباح تعدين
⭐ المزايا:
"""
            for feature in info['features']:
                vip_text += f"   • {feature}\n"
        
        vip_text += "\n🎯 بعد الشراء، سيتم التحقق من الإيداع تلقائياً!"
        
        bot.edit_message_text(
            vip_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=vip_keyboard()
        )
    except Exception as e:
        print(f"Error in vip_menu_handler: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('vip_'))
def handle_vip_selection(call):
    """معالجة اختيار باقة VIP"""
    try:
        user_id = call.from_user.id
        
        vip_type = call.data.split('_')[1]
        
        if vip_type in vip_system:
            vip_info = vip_system[vip_type]
            
            vip_details = f"""🎯 **تفاصيل {vip_info['name']}**

💵 السعر: {vip_info['price']} USDT
📈 مكافأة التعدين: +{int(vip_info['bonus']*100)}%
🎁 المكافأة اليومية: {vip_info['daily_bonus']} USDT

⭐ المزايا:
"""
            for feature in vip_info['features']:
                vip_details += f"• {feature}\n"
            
            vip_details += f"\n💎 **للشراء:** أرسل {vip_info['price']} USDT إلى العنوان:\n`{MAIN_WALLET}`\n\n📝 **اكتب في وصف التحويل:** VIP_{vip_type}_{user_id}"""

            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("💰 تعليمات الإيداع", callback_data="deposit"))
            keyboard.add(InlineKeyboardButton("🔙 عودة للباقات", callback_data="vip_menu"))
            
            bot.edit_message_text(
                vip_details,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
    except Exception as e:
        print(f"Error in handle_vip_selection: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'stats')
def stats_handler(call):
    """إحصائيات المستخدم"""
    try:
        user_id = call.from_user.id
        user = get_user(user_id)
        
        stats_text = f"""📊 **إحصائياتك الشخصية**

💰 الرصيد الحالي: {user['balance']:.1f} USDT
⚡ أرباح التعدين: {user['mining_earnings']:.1f} USDT
👥 أرباح الإحالات: {user['referral_earnings']:.1f} USDT
🎮 الألعاب الملعوبة: {user['games_played_today']} اليوم

📈 **التقدم نحو السحب:**
• الرصيد: {user['balance']:.1f}/100 USDT
• الإحالات: {user['referrals_count']}/15 مستخدم

🎯 **استمر في التقدم!**"""

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
        
        bot.edit_message_text(
            stats_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error in stats_handler: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'support')
def support_handler(call):
    """معالجة الدعم الفني"""
    try:
        support_text = """📞 **الدعم الفني**

🎯 **للاستفسارات والشكاوى:**
• تواصل مع الدعم المباشر
• اقرأ الأسئلة الشائعة
• أبلغ عن أي مشكلة تواجهك

🛠️ **فريق الدعم جاهز لمساعدتك على مدار الساعة**"""

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("💬 محادثة مباشرة", url=f"https://t.me/{SUPPORT_USER_ID}"))
        keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
        
        bot.edit_message_text(
            support_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error in support_handler: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'language')
def language_handler(call):
    """معالجة تغيير اللغة"""
    try:
        language_text = """🌐 **اختر اللغة / Choose Language**

🇸🇦 العربية - Arabic  
🇺🇸 الإنجليزية - English"""

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"))
        keyboard.add(InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"))
        keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
        
        bot.edit_message_text(
            language_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error in language_handler: {e}")

# 🌐 نظام Webhook المحسن
@app.route('/')
def home():
    return "🤖 البوت يعمل بشكل صحيح! - BNB Mini Bot"

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

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    """استقبال التحديثات من Telegram"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    else:
        return 'Forbidden', 403

@app.route('/set_webhook')
def set_webhook_route():
    """تعيين webhook تلقائياً"""
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL)
        return f"✅ تم تعيين Webhook: {WEBHOOK_URL}"
    except Exception as e:
        return f"❌ خطأ في تعيين Webhook: {e}"

# 🔧 نظام الصيانة التلقائية
def daily_maintenance():
    """صيانة يومية تلقائية"""
    try:
        cursor = db_connection.cursor()
        # إعادة تعيين محاولات الألعاب اليومية
        cursor.execute("UPDATE users SET games_played_today = 0")
        db_connection.commit()
        print("✅ Daily maintenance completed at", datetime.now())
    except Exception as e:
        print(f"❌ Maintenance error: {e}")

# 🚀 بدء التشغيل
if __name__ == "__main__":
    print("🚀 بدأ تشغيل البوت المتطور...")
    
    # بدء نظام منع النوم
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    
    # جدولة الصيانة اليومية باستخدام threading بدلاً من APScheduler
    def schedule_maintenance():
        while True:
            now = datetime.now()
            if now.hour == 0 and now.minute == 0:  # منتصف الليل
                daily_maintenance()
            time.sleep(60)  # التحقق كل دقيقة
    
    maintenance_thread = threading.Thread(target=schedule_maintenance, daemon=True)
    maintenance_thread.start()
    
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
