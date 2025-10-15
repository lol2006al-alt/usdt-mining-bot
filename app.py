from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import random
import json
from datetime import datetime

# التوكن الجديد
BOT_TOKEN = "8385331860:AAHj0uPnpJf_JYtHjALIkmavsBNnpa_Gd2Y"
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# المشرفين
ADMIN_IDS = [8400225549]

# تخزين البيانات في الذاكرة (مؤقت)
users_db = {}
referrals_db = []
backups_db = []
transactions_db = []

# 🔧 دوال مساعدة
def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {
            'user_id': user_id,
            'username': "",
            'first_name': "",
            'last_name': "",
            'balance': 0.0,
            'referrals_count': 0,
            'referrer_id': None,
            'vip_level': 0,
            'vip_expiry': None,
            'games_played_today': 0,
            'total_games_played': 0,
            'total_earned': 0.0,
            'total_deposits': 0.0,
            'games_counter': 0,
            'last_daily_bonus': None,
            'withdrawal_attempts': 0,
            'new_referrals_count': 0,
            'registration_date': datetime.now().isoformat()
        }
    return users_db[user_id]

def save_user(user_data):
    users_db[user_data['user_id']] = user_data
    return True

def add_balance(user_id, amount, description="", is_deposit=False):
    user = get_user(user_id)
    user['balance'] += amount
    user['total_earned'] += amount
    
    if is_deposit:
        user['total_deposits'] += amount
    
    # تسجيل المعاملة
    transactions_db.append({
        'user_id': user_id,
        'type': 'deposit' if is_deposit else 'bonus',
        'amount': amount,
        'description': description,
        'timestamp': datetime.now().isoformat()
    })
    
    return True

def add_referral(referrer_id, referred_id):
    if referrer_id == referred_id:
        return False
    
    # التحقق من عدم تكرار الإحالة
    for ref in referrals_db:
        if ref['referrer_id'] == referrer_id and ref['referred_id'] == referred_id:
            return False
    
    # إضافة الإحالة
    referrals_db.append({
        'referrer_id': referrer_id,
        'referred_id': referred_id,
        'bonus_given': True,
        'timestamp': datetime.now().isoformat()
    })
    
    # تحديث إحالات المُحيل
    referrer = get_user(referrer_id)
    referrer['referrals_count'] += 1
    
    # منح مكافآت الإحالة
    add_balance(referrer_id, 1.0, f"مكافأة إحالة للمستخدم {referred_id}")
    add_balance(referred_id, 1.0, "مكافأة انضمام بالإحالة")
    
    # إعادة تعيين محاولات الألعاب للمُحيل
    referrer['games_played_today'] = max(0, referrer['games_played_today'] - 1)
    
    return True

# 🛠️ نظام النسخ الاحتياطي
def create_sql_backup():
    try:
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'users': users_db,
            'referrals': referrals_db,
            'total_users': len(users_db),
            'total_referrals': len(referrals_db)
        }
        
        backups_db.append({
            'backup_data': backup_data,
            'created_at': datetime.now().isoformat(),
            'description': f"Backup {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        })
        
        print(f"✅ تم إنشاء نسخة احتياطية: {len(users_db)} مستخدم")
        return True
        
    except Exception as e:
        print(f"❌ فشل النسخ الاحتياطي: {e}")
        return False

def list_sql_backups():
    return backups_db[-10:] if backups_db else []

# 🎯 الأزرار بنفس التصميم الأصلي
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
    
    # حساب المكافأة
    if result[0] == result[1] == result[2]:
        win_amount = 5.0
    elif result[0] == result[1] or result[1] == result[2]:
        win_amount = 2.0
    else:
        win_amount = 0.0
    
    return result, win_amount

def play_dice_game(user_id):
    user_dice = random.randint(1, 6)
    bot_dice = random.randint(1, 6)
    
    if user_dice > bot_dice:
        result = "فوز"
        win_amount = 3.0
    elif user_dice < bot_dice:
        result = "خسارة" 
        win_amount = 0.0
    else:
        result = "تعادل"
        win_amount = 1.0
    
    return user_dice, bot_dice, result, win_amount

def play_football_game(user_id):
    outcomes = ["هدف 🥅", "إصابة القائم 🚩", "حارس يصد ⛔"]
    result = random.choices(outcomes, k=3)
    win_amount = 2.0 if "هدف" in result else 0.5
    return result, win_amount

def play_basketball_game(user_id):
    shots = []
    goals = 0
    for i in range(3):
        if random.random() > 0.3:
            shot_type = "🎯 تسجيل ✅"
            goals += 1
        else:
            shot_type = "🎯 أخطأت ❌"
        shots.append(shot_type)
    
    win_amount = goals * 1.0
    return shots, win_amount

def play_darts_game(user_id):
    scores = []
    total_score = 0
    for i in range(3):
        score = random.randint(10, 50)
        scores.append(f"🎯 نقاط: {score}")
        total_score += score
    
    win_amount = total_score / 50.0  # 0.2 إلى 1.0 USDT
    return scores, win_amount

# 🎯 معالجة الـ Callbacks (الأزرار)
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    
    if call.data == "main_menu":
        welcome_text = f"""
🎮 أهلاً {call.from_user.first_name}!

💰 رصيدك: {user['balance']:.1f} USDT
👥 إحالاتك: {user['referrals_count']}
🎯 المحاولات: {3 - user['games_played_today']}/3
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
🎯 المحاولات: {3 - user['games_played_today']}/3
💎 VIP: {user['vip_level']}
🏆 الألعاب: {user['total_games_played']}
💳 الإيداعات: {user['total_deposits']:.1f} USDT"""
        
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
{referral_link}

📊 لديك {user['referrals_count']} إحالة"""
        
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
        
        if user['balance'] >= 10:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=withdraw_text + "\n\n✅ يمكنك سحب رصيدك الآن!",
                reply_markup=create_withdraw_keyboard()
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=withdraw_text + f"\n\n❌ تحتاج {10 - user['balance']:.1f} USDT أخرى للسحب",
                reply_markup=create_main_menu()
            )
    
    elif call.data.startswith("game_"):
        game_type = call.data.replace("game_", "")
        
        # التحقق من المحاولات
        if user['games_played_today'] >= 3:
            bot.answer_callback_query(call.id, "❌ انتهت محاولاتك اليوم! جددها بالإحالات", show_alert=True)
            return
        
        # زيادة عداد الألعاب
        user['games_played_today'] += 1
        user['total_games_played'] += 1
        user['games_counter'] += 1
        
        # تشغيل اللعبة
        if game_type == "slots":
            result, win_amount = play_slots_game(user_id)
            game_result = f"🎰 نتيجة السلوتس: {' '.join(result)}"
        elif game_type == "dice":
            user_dice, bot_dice, result, win_amount = play_dice_game(user_id)
            game_result = f"🎲 النرد: أنت {user_dice} vs البوت {bot_dice} - {result}"
        elif game_type == "football":
            result, win_amount = play_football_game(user_id)
            game_result = f"⚽ كرة القدم: {' | '.join(result)}"
        elif game_type == "basketball":
            result, win_amount = play_basketball_game(user_id)
            game_result = f"🏀 السلة: {' | '.join(result)}"
        elif game_type == "darts":
            result, win_amount = play_darts_game(user_id)
            game_result = f"🎯 السهم: {' | '.join(result)}"
        else:
            game_result = f"🎮 لعبة {game_type}"
            win_amount = 0
        
        # منح المكافأة
        if win_amount > 0:
            add_balance(user_id, win_amount, f"ربح لعبة {game_type}")
            win_text = f"🎉 ربحت {win_amount} USDT!"
        else:
            win_text = "😔 لم تربح هذه المرة"
        
        # مكافأة كل 3 محاولات
        if user['games_counter'] >= 3:
            bonus_amount = 5.0
            add_balance(user_id, bonus_amount, "مكافأة كل 3 محاولات")
            user['games_counter'] = 0
            bonus_text = f"\n🏆 مبروك! حصلت على مكافأة {bonus_amount} USDT لكل 3 محاولات!"
        else:
            bonus_text = ""
        
        remaining = 3 - user['games_played_today']
        result_text = f"""
{game_result}

{win_text}
{bonus_text}

🎯 المحاولات المتبقية: {remaining}/3
💰 الرصيد: {user['balance']:.1f} USDT"""
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=result_text,
            reply_markup=create_games_menu()
        )
    
    elif call.data in ["buy_bronze", "buy_silver", "buy_gold"]:
        vip_data = {
            "buy_bronze": {"name": "برونزي", "price": 5.0, "level": 1},
            "buy_silver": {"name": "فضى", "price": 10.0, "level": 2},
            "buy_gold": {"name": "ذهبي", "price": 20.0, "level": 3}
        }
        
        vip_info = vip_data[call.data]
        
        if user['balance'] >= vip_info['price']:
            # خصم السعر
            user['balance'] -= vip_info['price']
            user['vip_level'] = vip_info['level']
            user['vip_expiry'] = (datetime.now() + timedelta(days=30)).isoformat()
            
            bot.answer_callback_query(call.id, f"✅ تم شراء باقة {vip_info['name']} بنجاح!", show_alert=True)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ تم تفعيل باقة {vip_info['name']} VIP!\n\n💰 الرصيد المتبقي: {user['balance']:.1f} USDT",
                reply_markup=create_main_menu()
            )
        else:
            bot.answer_callback_query(call.id, f"❌ رصيدك غير كافٍ! تحتاج {vip_info['price']} USDT", show_alert=True)
    
    elif call.data == "confirm_bep20":
        if user['balance'] >= 10:
            # محاكاة عملية السحب
            user['withdrawal_attempts'] += 1
            bot.answer_callback_query(call.id, "✅ تم استلام طلب السحب بنجاح!", show_alert=True)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ تم استلام طلب سحب {user['balance']:.1f} USDT\n\n📧 سيتم التواصل معك خلال 24 ساعة",
                reply_markup=create_main_menu()
            )
        else:
            bot.answer_callback_query(call.id, "❌ الرصيد غير كافٍ للسحب!", show_alert=True)
    
    elif call.data == "copy_link":
        bot.answer_callback_query(call.id, "✅ تم نسخ رابط الإحالة إلى الحافظة", show_alert=True)
    
    elif call.data == "my_referrals":
        bot.answer_callback_query(call.id, f"📊 لديك {user['referrals_count']} إحالة", show_alert=True)

# 🛠️ الأوامر الإدارية (نفس التي عملناها)
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
        
        if add_balance(target_user_id, amount, f"إضافة إدارية بواسطة {message.from_user.id}", is_deposit=True):
            user = get_user(target_user_id)
            response = f"✅ تم إضافة {amount} USDT للمستخدم {target_user_id}\n💰 الرصيد الجديد: {user['balance']:.1f} USDT"
            
            # إشعار المستخدم
            try:
                bot.send_message(target_user_id, f"🎉 تم إضافة {amount} USDT إلى رصيدك!\n💰 رصيدك الحالي: {user['balance']:.1f} USDT")
            except:
                pass
        else:
            response = "❌ فشل في إضافة الرصيد"
        
        bot.reply_to(message, response)
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['quickremove'])
def quick_remove_balance(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /quickremove [user_id] [amount]")
            return
        
        target_user_id = int(parts[1])
        amount = float(parts[2])
        
        user = get_user(target_user_id)
        if user:
            if user['balance'] >= amount:
                old_balance = user['balance']
                user['balance'] -= amount
                save_user(user)
                bot.reply_to(message, f"✅ تم سحب {amount} USDT من المستخدم {target_user_id}\n📊 الرصيد السابق: {old_balance:.1f} USDT\n💰 الرصيد الجديد: {user['balance']:.1f} USDT")
            else:
                bot.reply_to(message, f"❌ رصيد المستخدم غير كافٍ! الرصيد الحالي: {user['balance']:.1f}")
        else:
            bot.reply_to(message, "❌ المستخدم غير موجود!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['adduser'])
def add_user_complete(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "📝 استخدم: /adduser user_id balance [referrals] [vip_level] [total_deposits] [total_earned] [games_played]")
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
            'new_referrals_count': 0,
            'registration_date': datetime.now().isoformat()
        }
        
        if save_user(user_data):
            response = f"""✅ تم إضافة المستخدم بنجاح:

🆔 الآيدي: {user_id}
💰 الرصيد: {balance} USDT
👥 الإحالات: {referrals}
💎 مستوى VIP: {vip_level}
💳 إجمالي الإيداعات: {total_deposits} USDT
🎯 إجمالي الألعاب: {total_games}
🏆 إجمالي الأرباح: {total_earned} USDT

💾 التخزين: الذاكرة (مؤقت)"""
        else:
            response = "❌ فشل في إضافة المستخدم"
        
        bot.reply_to(message, response)
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['userfullinfo'])
def user_full_info(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ استخدم: /userfullinfo [user_id]")
            return
        
        user_id = int(parts[1])
        user = get_user(user_id)
        
        if user:
            remaining_games = 3 - user['games_played_today']
            vip_expiry = user['vip_expiry'][:10] if user['vip_expiry'] else "غير محدد"
            reg_date = user['registration_date'][:10] if 'registration_date' in user else "غير معروف"
            
            info_text = f"""
📊 معلومات كاملة عن المستخدم:

🆔 الآيدي: {user['user_id']}
👤 الاسم: {user['first_name']} {user.get('last_name', '')}

💰 الحساب المالي:
• الرصيد: {user['balance']:.1f} USDT
• إجمالي الإيداعات: {user['total_deposits']:.1f} USDT
• إجمالي الأرباح: {user['total_earned']:.1f} USDT

🎮 إحصائيات الألعاب:
• المحاولات المتبقية: {remaining_games}/3
• إجمالي الألعاب: {user['total_games_played']}
• عداد المكافآت: {user['games_counter']}/3

👥 نظام الإحالات:
• عدد الإحالات: {user['referrals_count']}
• محاولات السحب: {user['withdrawal_attempts']}

💎 معلومات VIP:
• المستوى: {user['vip_level']}
• انتهاء الصلاحية: {vip_expiry}

📅 معلومات عامة:
• تاريخ التسجيل: {reg_date}"""
        else:
            info_text = "❌ المستخدم غير موجود!"
        
        bot.reply_to(message, info_text)
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['manualbackup'])
def manual_backup(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        bot.reply_to(message, "🔄 جاري إنشاء نسخة احتياطية...")
        
        if create_sql_backup():
            backups = list_sql_backups()
            latest = backups[-1] if backups else None
            
            if latest:
                response = f"""✅ تم إنشاء نسخة احتياطية بنجاح!

📊 تفاصيل النسخة:
📅 التاريخ: {latest['created_at']}
📝 الوصف: {latest['description']}
👥 المستخدمين: {latest['backup_data']['total_users']}

💾 التخزين: الذاكرة (مؤقت)"""
            else:
                response = "✅ تم إنشاء النسخة ولكن لم يتم العثور على تفاصيلها"
        else:
            response = "❌ فشل إنشاء النسخة الاحتياطية"
        
        bot.reply_to(message, response)
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {str(e)}")

@bot.message_handler(commands=['listbackups'])
def list_backups(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        backups = list_sql_backups()
        
        if backups:
            backups_list = "📂 النسخ الاحتياطية:\n\n"
            for i, backup in enumerate(reversed(backups[-5:]), 1):
                backups_list += f"{i}. {backup['created_at']} - {backup['backup_data']['total_users']} مستخدم\n"
            
            backups_list += f"\n💾 إجمالي النسخ: {len(backups)}"
        else:
            backups_list = "❌ لا توجد نسخ احتياطية حالياً\nاستخدم /manualbackup لإنشاء أول نسخة"
        
        bot.reply_to(message, backups_list)
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {str(e)}")

# 🎯 الأمر start الأساسي
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        referrer_id = None
        referral_bonus = 0
        
        # نظام الإحالات
        if len(message.text.split()) > 1:
            try:
                referrer_id = int(message.text.split()[1])
                if referrer_id != user_id:
                    if add_referral(referrer_id, user_id):
                        referral_bonus = 1.0
            except:
                referrer_id = None
        
        user_data = {
            'user_id': user_id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name or "",
            'referrer_id': referrer_id,
            'balance': 0.0 + referral_bonus,
            'games_played_today': 0,
            'total_deposits': 0.0,
            'withdrawal_attempts': 0,
            'new_referrals_count': 0,
            'registration_date': datetime.now().isoformat()
        }
        save_user(user_data)
        user = user_data
        
        welcome_text = f"""
🎮 أهلاً وسهلاً {message.from_user.first_name}!

🎯 لديك 3 محاولات لعب مجانية
💰 مكافأة الإحالة: 1.0 USDT لكل صديق
👥 كل إحالة تمنحك محاولة إضافية

🏆 اربح 5 USDT كل 3 محاولات!"""
        
        if referral_bonus > 0:
            welcome_text += f"\n\n🎉 حصلت على {referral_bonus} USDT مكافأة انضمام!"
    
    else:
        welcome_text = f"""
🎮 مرحباً بعودتك {message.from_user.first_name}!

💰 رصيدك: {user['balance']:.1f} USDT
👥 عدد الإحالات: {user['referrals_count']}
🎯 المحاولات المتبقية: {3 - user['games_played_today']}
🏆 مستوى VIP: {user['vip_level']}"""
    
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
        "database": "Memory",
        "timestamp": datetime.now().isoformat(),
        "total_users": len(users_db),
        "total_referrals": len(referrals_db),
        "version": "1.0",
        "performance": "excellent"
    }

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

# 🚀 بدء التشغيل
if __name__ == "__main__":
    print("🚀 بدأ تشغيل البوت مع جميع الميزات...")
    
    try:
        # إعداد ويب هوك
        bot.remove_webhook()
        time.sleep(2)
        
        WEBHOOK_URL = f'https://usdt-bot-live.onrender.com/{BOT_TOKEN}'
        bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ Webhook مضبوط: {WEBHOOK_URL}")
        print(f"✅ نظام الأزرار جاهز")
        print(f"✅ نظام الألعاب جاهز")
        print(f"✅ نظام الإحالات جاهز")
        print(f"✅ الأوامر الإدارية جاهزة")
        
        # تشغيل الخادم
        PORT = int(os.environ.get('PORT', 10000))
        print(f"🌐 الخادم يعمل على المنفذ {PORT}")
        app.run(host='0.0.0.0', port=PORT, debug=False)
        
    except Exception as e:
        print(f"❌ خطأ في التشغيل: {e}")
