from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json
from datetime import datetime
import random

# التوكن من Environment Variable
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8385331860:AAHj0uPnpJf_JYtHjALIkmavsBNnpa_Gd2Y")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# المشرفين
ADMIN_IDS = [8400225549]

# تخزين المستخدمين في الذاكرة (مؤقت)
users_db = {}
backups_db = []

# 🎯 كل الأزرار والوظائف كما في الأصل
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

# 🎮 دوال الألعاب (نفس الكود الأصلي)
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
            'referrals_count': 0,
            'games_played_today': 0,
            'vip_level': 0
        }
    
    user['balance'] += amount
    user['total_earned'] += amount
    if is_deposit:
        user['total_deposits'] += amount
    
    return save_user(user)

# 🎯 معالجة الـ Callbacks (الأزرار)
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    
    if not user:
        user = {
            'user_id': user_id,
            'balance': 0.0,
            'referrals_count': 0,
            'games_played_today': 0,
            'vip_level': 0
        }
        save_user(user)
    
    if call.data == "main_menu":
        welcome_text = f"""
🎮 أهلاً {call.from_user.first_name}!

💰 رصيدك: {user['balance']:.1f} USDT
👥 إحالاتك: {user['referrals_count']}
🎯 محاولاتك: {3 - user.get('games_played_today', 0)}/3
💎 مستوى VIP: {user['vip_level']}"""
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=welcome_text,
            reply_markup=create_main_menu()
        )
    
    elif call.data == "games_menu":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🎮 اختر لعبة من القائمة:",
            reply_markup=create_games_menu()
        )
    
    elif call.data == "profile":
        profile_text = f"""
📊 الملف الشخصي:

👤 الاسم: {call.from_user.first_name}
🆔 الآيدي: {user_id}
💰 الرصيد: {user['balance']:.1f} USDT
👥 الإحالات: {user['referrals_count']}
🎯 المحاولات: {3 - user.get('games_played_today', 0)}/3
💎 VIP: {user['vip_level']}"""
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=profile_text,
            reply_markup=create_main_menu()
        )
    
    elif call.data == "referral":
        keyboard, referral_link = create_referral_keyboard(user_id)
        referral_text = f"""
👥 نظام الإحالات:

💰 احصل على 1.0 USDT لكل صديق
🎯 واحصل على محاولة لعب إضافية

🔗 رابط الإحالة الخاص بك:
{referral_link}"""
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=referral_text,
            reply_markup=keyboard
        )
    
    elif call.data == "vip_packages":
        vip_text = """
💎 باقات VIP:

🟢 برونزي - 5 USDT
• محاولات لعب غير محدودة
• مكافآت مضاعفة

🔵 فضى - 10 USDT  
• كل مزايا البرونزي
• دعم فني متميز

🟡 ذهبي - 20 USDT
• كل المزايا السابقة
• أولوية في السحب"""
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=vip_text,
            reply_markup=create_vip_keyboard()
        )
    
    elif call.data == "withdraw":
        withdraw_text = f"""
💰 سحب رصيد:

💳 الحد الأدنى للسحب: 10 USDT
🔄 استخدام شبكة BEP20

💰 رصيدك الحالي: {user['balance']:.1f} USDT"""
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=withdraw_text,
            reply_markup=create_withdraw_keyboard()
        )
    
    elif call.data.startswith("game_"):
        game_type = call.data.replace("game_", "")
        
        if user.get('games_played_today', 0) >= 3:
            bot.answer_callback_query(call.id, "❌ انتهت محاولاتك اليوم! جددها بالإحالات", show_alert=True)
            return
        
        # زيادة عداد الألعاب
        user['games_played_today'] = user.get('games_played_today', 0) + 1
        save_user(user)
        
        # تشغيل اللعبة
        if game_type == "slots":
            result = play_slots_game(user_id)
            game_result = f"🎰 نتيجة السلوتس: {' '.join(result)}"
        elif game_type == "dice":
            user_dice, bot_dice, result = play_dice_game(user_id)
            game_result = f"🎲 النرد: أنت {user_dice} vs البوت {bot_dice} - {result}"
        else:
            game_result = f"🎮 لعبة {game_type} - تحت التطوير"
        
        remaining = 3 - user['games_played_today']
        result_text = f"""
{game_result}

🎯 المحاولات المتبقية: {remaining}/3
💰 اربح 5 USDT كل 3 محاولات!"""
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=result_text,
            reply_markup=create_games_menu()
        )

# 🛠️ الأوامر الإدارية (نفس الكود السابق)
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
            'total_games_played': referrals * 10,
            'games_played_today': 0
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
📊 معلومات كاملة:

🆔 الآيدي: {user['user_id']}
💰 الرصيد: {user.get('balance', 0):.1f} USDT
💳 الإيداعات: {user.get('total_deposits', 0):.1f} USDT
🏆 الأرباح: {user.get('total_earned', 0):.1f} USDT
👥 الإحالات: {user.get('referrals_count', 0)}
💎 VIP: {user.get('vip_level', 0)}
🎮 الألعاب: {user.get('total_games_played', 0)}
🎯 المحاولات: {3 - user.get('games_played_today', 0)}/3"""
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

# 🎯 الأمر start الأساسي
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
            'vip_level': 0,
            'games_played_today': 0
        }
        save_user(user_data)
        user = user_data
    
    welcome_text = f"""
🎮 أهلاً وسهلاً {message.from_user.first_name}!

💰 رصيدك: {user['balance']:.1f} USDT
👥 إحالاتك: {user['referrals_count']}
🎯 المحاولات: {3 - user['games_played_today']}/3
💎 مستوى VIP: {user['vip_level']}

🏆 اربح 5 USDT كل 3 محاولات!"""
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_main_menu())

@bot.message_handler(commands=['test'])
def test_command(message):
    bot.reply_to(message, "✅ البوت يعمل! جرب الأزرار في القائمة الرئيسية")

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
        "version": "3.0"
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
    print("🚀 بدأ تشغيل البوت مع الأزرار والألعاب...")
    try:
        bot.remove_webhook()
        import time
        time.sleep(2)
        
        WEBHOOK_URL = f'https://usdt-bot-live.onrender.com/{BOT_TOKEN}'
        bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ Webhook مضبوط: {WEBHOOK_URL}")
        print(f"✅ نظام الأزرار جاهز")
        print(f"✅ نظام الألعاب جاهز")
        
        PORT = int(os.environ.get('PORT', 10000))
        app.run(host='0.0.0.0', port=PORT, debug=False)
        
    except Exception as e:
        print(f"❌ خطأ في التشغيل: {e}")
