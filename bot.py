import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import json
import time
import random
from datetime import datetime, timedelta

# 🔐 التوكن والمعلومات
BOT_TOKEN = "8385331860:AAEs9uHNcuhYRHsO3Q3wC2DBhNp-znFc1H"
SUPPORT_USER_ID = "8400225549"
DEPOSIT_ADDRESS = "0xfc712c9985507a2eb44df1ddfe7f09ff7613a19b"

bot = telebot.TeleBot(BOT_TOKEN)

# 📊 تخزين البيانات
user_data = {}

# 🎯 إنشاء لوحات المفاتيح
def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("💰 الرصيد"),
        KeyboardButton("⛏️ التعدين"),
        KeyboardButton("👥 الإحالات"),
        KeyboardButton("🎮 الألعاب"),
        KeyboardButton("📋 المهام"),
        KeyboardButton("💳 المحفظة"),
        KeyboardButton("📞 الدعم")
    ]
    keyboard.add(*buttons)
    return keyboard

def referrals_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📋 نسخ رابط الدعوة", callback_data="copy_referral"),
        InlineKeyboardButton("👥 إحالاتي", callback_data="my_referrals")
    )
    return keyboard

def wallet_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💳 الإيداع", callback_data="deposit"),
        InlineKeyboardButton("🔄 السحب", callback_data="withdraw"),
        InlineKeyboardButton("📋 نسخ العنوان", callback_data="copy_deposit")
    )
    return keyboard

def games_inline_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎰 لعب السلوت", callback_data="slot_game"))
    return keyboard

# 📊 تهيئة بيانات المستخدم
def init_user_data(user_id):
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
            'wallet_balance': 0.00,
            'mining_earnings': 0.00,
            'referrals_count': 0,
            'completed_tasks': 0,
            'mining_progress': 0.00,
            'max_mining': 2.00,
            'attempts_left': 10,
            'consecutive_days': 1,
            'last_login': datetime.now().date().isoformat(),
            'total_games_played': 0,
            'referral_earnings': 0.00,
            'today_referrals': 0,
            'user_code': str(random.randint(10000000, 99999999)),
            'total_deposited': 0.00,
            'username': '',
            'first_name': ''
        }

# 🏁 أمر البدء
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    init_user_data(user_id)
    
    user_data[str(user_id)]['username'] = message.from_user.username or ''
    user_data[str(user_id)]['first_name'] = message.from_user.first_name or ''
    
    # معالجة الإحالة
    if len(message.text.split()) > 1:
        referral_code = message.text.split()[1]
        if referral_code.isdigit() and len(referral_code) == 8:
            user_data[str(user_id)]['referred_by'] = referral_code
            for uid, data in user_data.items():
                if data['user_code'] == referral_code:
                    data['referrals_count'] += 1
                    data['today_referrals'] += 1
                    data['referral_earnings'] += 1.00
                    break
    
    welcome_message = f"""🎉 أهلاً بك في محفظة تعدين USDT!

💰 رصيدك: {user_data[str(user_id)]['wallet_balance']:.2f} USDT
⛏️ جاري التعدين: {user_data[str(user_id)]['mining_progress']:.2f}/2.00 USDT
👥 الإحالات: {user_data[str(user_id)]['referrals_count']}

🎯 اختر من الأوامر أدناه لبدء رحلتك نحو الأرباح! 🚀"""
    
    bot.send_message(user_id, welcome_message, reply_markup=main_keyboard())

# 📨 معالجة الرسائل النصية
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id
    init_user_data(user_id)
    
    if message.text == "💰 الرصيد":
        show_balance(message)
    elif message.text == "⛏️ التعدين":
        show_mining(message)
    elif message.text == "👥 الإحالات":
        show_referrals(message)
    elif message.text == "🎮 الألعاب":
        show_games(message)
    elif message.text == "📋 المهام":
        show_tasks(message)
    elif message.text == "💳 المحفظة":
        show_wallet(message)
    elif message.text == "📞 الدعم":
        show_support(message)
    else:
        bot.send_message(user_id, "⚠️ استخدم الأزرار أدناه للتنقل", reply_markup=main_keyboard())

# 💰 عرض الرصيد
def show_balance(message):
    user_id = message.from_user.id
    data = user_data[str(user_id)]
    total_balance = data['wallet_balance'] + data['mining_earnings'] + data['referral_earnings']
    
    balance_msg = f"""💰 **رصيدك الكامل**

💼 الرصيد الرئيسي: {data['wallet_balance']:.2f} USDT
⛏️ أرباح التعدين: {data['mining_earnings']:.2f} USDT
👥 أرباح الإحالات: {data['referral_earnings']:.2f} USDT

💵 **الإجمالي: {total_balance:.2f} USDT**

📈 استمر في التعدين ودعوة الأصدقاء لزيادة أرباحك!"""
    
    bot.send_message(user_id, balance_msg, reply_markup=main_keyboard())

# ⛏️ عرض التعدين
def show_mining(message):
    user_id = message.from_user.id
    data = user_data[str(user_id)]
    
    progress_percent = (data['mining_progress'] / data['max_mining']) * 100
    progress_bar = "🟢" * int(progress_percent / 10) + "⚪" * (10 - int(progress_percent / 10))
    
    mining_msg = f"""⛏️ **حالة التعدين**

{progress_bar}
{data['mining_progress']:.2f} / {data['max_mining']:.2f} USDT

📊 التقدم: {progress_percent:.1f}%
⏰ الحالة: {'جاري التعدين...' if data['mining_progress'] < data['max_mining'] else 'مكتمل ✅'}

💡 التعدين يعمل تلقائياً! عد لاحقاً لتحصيل أرباحك."""
    
    bot.send_message(user_id, mining_msg, reply_markup=main_keyboard())

# 👥 عرض الإحالات
def show_referrals(message):
    user_id = message.from_user.id
    data = user_data[str(user_id)]
    
    referrals_msg = f"""👥 **نظام الإحالات**

🎯 كود الإحالة: `{data['user_code']}`
👥 الإحالات: {data['referrals_count']}
💰 الأرباح: {data['referral_earnings']:.2f} USDT

🎁 **المكافآت:**
• 1.00 USDT لكل إحالة جديدة
• 5.00 USDT مكافأة إضافية لكل 5 إحالات

🔗 رابط الدعوة:
`https://t.me/BNBMini1Bot?start={data['user_code']}`"""
    
    bot.send_message(user_id, referrals_msg, reply_markup=referrals_inline_keyboard())

# 🎮 عرض الألعاب
def show_games(message):
    user_id = message.from_user.id
    data = user_data[str(user_id)]
    
    games_msg = f"""🎮 **الألعاب المتاحة**

🎰 **لعبة السلوت**
• المحاولات: {data['attempts_left']}
• الجولات: {data['total_games_played']}

🏆 **الجوائز:**
• 3 رموز متطابقة: 🎉 1.00 USDT
• رمزين متطابقين: 🎊 0.25 USDT

💡 كل إحالة = +2 محاولات جديدة"""
    
    bot.send_message(user_id, games_msg, reply_markup=games_inline_keyboard())

# 📋 عرض المهام
def show_tasks(message):
    user_id = message.from_user.id
    data = user_data[str(user_id)]
    
    tasks_msg = f"""📋 **المهام اليومية**

🔥 تسجيل متتالي: {data['consecutive_days']}/7 أيام

✅ **المهام:**
• تسجيل الدخول اليومي - 0.10 USDT
• اكتمال التعدين - 0.20 USDT  
• لعب 3 جولات - 0.15 USDT
• دعوة صديق - 1.00 USDT
• 7 أيام متتالية - 5.00 USDT

📊 المكتمل: {data['completed_tasks']}/5"""
    
    bot.send_message(user_id, tasks_msg, reply_markup=main_keyboard())

# 💳 عرض المحفظة
def show_wallet(message):
    user_id = message.from_user.id
    data = user_data[str(user_id)]
    total_balance = data['wallet_balance'] + data['mining_earnings'] + data['referral_earnings']
    
    wallet_msg = f"""💳 **المحفظة**

💰 الرصيد المتاح: {total_balance:.2f} USDT

💎 **عنوان الإيداع:**
`{DEPOSIT_ADDRESS}`
(شبكة BEP20 فقط)

📋 **متطلبات السحب:**
• 7 أيام تسجيل متتالي
• إيداع 10 USDT كحد أدنى
• إكمال 5 مهام
• 3 إحالات على الأقل
• الحد الأدنى للسحب: 100 USDT"""
    
    bot.send_message(user_id, wallet_msg, reply_markup=wallet_inline_keyboard())

# 📞 عرض الدعم
def show_support(message):
    support_msg = """📞 **الدعم الفني**

💬 لطلب المساعدة، اكتب رسالتك مباشرة وسيتم إرسالها لفريق الدعم.

⏰ وقت الاستجابة: 24 ساعة

📝 **نصيحة:** اشرح مشكلتك بوضوح مع تقديم أي تفاصيل تساعد في حلها."""
    
    bot.send_message(message.from_user.id, support_msg, reply_markup=main_keyboard())
    bot.send_message(message.from_user.id, "✍️ اكتب رسالتك الآن:")

# 🎰 معالجة الأزرار
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    init_user_data(str(user_id))
    
    if call.data == "copy_referral":
        referral_link = f"https://t.me/BNBMini1Bot?start={user_data[str(user_id)]['user_code']}"
        bot.answer_callback_query(call.id, f"تم النسخ: {referral_link}", show_alert=True)
    
    elif call.data == "copy_deposit":
        bot.answer_callback_query(call.id, f"تم نسخ العنوان: {DEPOSIT_ADDRESS}", show_alert=True)
    
    elif call.data == "slot_game":
        play_slot_game(call)

# 🎮 لعبة السلوت
def play_slot_game(call):
    user_id = call.from_user.id
    data = user_data[str(user_id)]
    
    if data['attempts_left'] <= 0:
        bot.answer_callback_query(call.id, "انتهت المحاولات! ادعُ أصدقاء للحصول على المزيد", show_alert=True)
        return
    
    data['attempts_left'] -= 1
    data['total_games_played'] += 1
    
    symbols = ['🍒', '🍋', '🍊', '⭐', '🔔', '7️⃣']
    result = [random.choice(symbols) for _ in range(3)]
    
    prize = 0
    if result[0] == result[1] == result[2]:
        prize = 1.00
        win_msg = "🎉 فوز كبير! +1.00 USDT"
    elif result[0] == result[1] or result[1] == result[2]:
        prize = 0.25
        win_msg = "🎊 فوز! +0.25 USDT"
    else:
        win_msg = "💔 حظ أوفر في المرة القادمة!"
    
    if prize > 0:
        data['mining_earnings'] += prize
    
    game_result = f"""🎰 **النتيجة**

{' | '.join(result)}

{win_msg}

المحاولات المتبقية: {data['attempts_left']}"""
    
    bot.send_message(user_id, game_result, reply_markup=games_inline_keyboard())

# 🚀 تشغيل البوت
if __name__ == "__main__":
    print("🤖 بوت الأزرار يعمل بنجاح...")
    bot.polling(none_stop=True)
