import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
from datetime import datetime
import json
import os

BOT_TOKEN = "8385331860:AAFTz51bMqPjtEBM50p_5WY_pbMytnqS0zc"
bot = telebot.TeleBot(BOT_TOKEN)

# تخزين البيانات
user_data = {}

def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💰 الرصيد", callback_data="balance"),
        InlineKeyboardButton("⛏️ التعدين", callback_data="mining")
    )
    keyboard.add(
        InlineKeyboardButton("👥 الإحالات", callback_data="referrals"),
        InlineKeyboardButton("🎮 الألعاب", callback_data="games")
    )
    keyboard.add(
        InlineKeyboardButton("📋 المهام", callback_data="tasks"),
        InlineKeyboardButton("💳 المحفظة", callback_data="wallet")
    )
    keyboard.add(InlineKeyboardButton("📞 الدعم", callback_data="support"))
    return keyboard

def referrals_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📋 نسخ رابط الدعوة", callback_data="copy_referral"),
        InlineKeyboardButton("👥 إحالاتي", callback_data="my_referrals")
    )
    keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
    return keyboard

def wallet_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💳 الإيداع", callback_data="deposit"),
        InlineKeyboardButton("🔄 السحب", callback_data="withdraw")
    )
    keyboard.add(InlineKeyboardButton("📋 نسخ العنوان", callback_data="copy_deposit"))
    keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
    return keyboard

def games_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎰 لعب السلوت", callback_data="slot_game"))
    keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
    return keyboard

def back_to_main_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
    return keyboard

def init_user(user_id):
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
            'wallet_balance': 0.0,
            'mining_earnings': 0.0,
            'referrals_count': 0,
            'completed_tasks': 0,
            'mining_progress': 0.0,
            'max_mining': 2.0,
            'attempts_left': 10,
            'consecutive_days': 1,
            'last_login': datetime.now().date().isoformat(),
            'total_games_played': 0,
            'referral_earnings': 0.0,
            'today_referrals': 0,
            'user_id': str(user_id),  # استخدام الـ ID كرمز للإحالة
            'total_deposited': 0.0,
            'referred_by': None,
            'referral_list': []  # قائمة بمن دعاهم
        }

def get_referral_link(user_id):
    return f"https://t.me/BNBMini1Bot?start={user_id}"

def update_referrer_stats(referrer_id):
    if str(referrer_id) in user_data:
        user_data[str(referrer_id)]['referrals_count'] += 1
        user_data[str(referrer_id)]['today_referrals'] += 1
        user_data[str(referrer_id)]['referral_earnings'] += 1.0
        user_data[str(referrer_id)]['referral_list'].append(datetime.now().isoformat())

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    init_user(user_id)
    
    # معالجة الإحالة
    if len(message.text.split()) > 1:
        referrer_id = message.text.split()[1]
        if referrer_id.isdigit() and referrer_id != str(user_id):
            user_data[str(user_id)]['referred_by'] = referrer_id
            update_referrer_stats(referrer_id)
    
    welcome = f"""🎉 **أهلاً بك في محفظة تعدين USDT!**

💰 **رصيدك:** {user_data[str(user_id)]['wallet_balance']:.2f} USDT
⛏️ **جاري التعدين:** {user_data[str(user_id)]['mining_progress']:.2f}/2.00 USDT
👥 **الإحالات:** {user_data[str(user_id)]['referrals_count']}

🚀 **اختر من الأزرار أدناه للبدء:**"""
    
    bot.send_message(user_id, welcome, reply_markup=main_menu_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    init_user(user_id)
    data = user_data[str(user_id)]
    
    try:
        if call.data == "main_menu":
            show_main_menu(call)
        
        elif call.data == "balance":
            show_balance(call)
        
        elif call.data == "mining":
            show_mining(call)
        
        elif call.data == "referrals":
            show_referrals(call)
        
        elif call.data == "games":
            show_games(call)
        
        elif call.data == "tasks":
            show_tasks(call)
        
        elif call.data == "wallet":
            show_wallet(call)
        
        elif call.data == "support":
            show_support(call)
        
        elif call.data == "copy_referral":
            copy_referral_link(call)
        
        elif call.data == "my_referrals":
            show_my_referrals(call)
        
        elif call.data == "deposit":
            show_deposit(call)
        
        elif call.data == "withdraw":
            show_withdraw(call)
        
        elif call.data == "copy_deposit":
            copy_deposit_address(call)
        
        elif call.data == "slot_game":
            play_slot_game(call)
            
    except Exception as e:
        bot.answer_callback_query(call.id, "⚠️ حدث خطأ، يرجى المحاولة مرة أخرى")

def show_main_menu(call):
    user_id = call.from_user.id
    data = user_data[str(user_id)]
    
    menu_text = f"""🏠 **القائمة الرئيسية**

💰 الرصيد: {data['wallet_balance']:.2f} USDT
⛏️ التعدين: {data['mining_progress']:.2f}/2.00 USDT
👥 الإحالات: {data['referrals_count']}

🎯 اختر الخدمة التي تريدها:"""
    
    bot.edit_message_text(
        menu_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=main_menu_keyboard()
    )

def show_balance(call):
    user_id = call.from_user.id
    data = user_data[str(user_id)]
    total_balance = data['wallet_balance'] + data['mining_earnings'] + data['referral_earnings']
    
    balance_text = f"""💰 **رصيدك الشامل**

💼 الرصيد الرئيسي: {data['wallet_balance']:.2f} USDT
⛏️ أرباح التعدين: {data['mining_earnings']:.2f} USDT
👥 أرباح الإحالات: {data['referral_earnings']:.2f} USDT

💵 **الإجمالي: {total_balance:.2f} USDT**

📈 استمر في التعدين ودعوة الأصدقاء لزيادة أرباحك!"""
    
    bot.edit_message_text(
        balance_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=back_to_main_keyboard()
    )

def show_mining(call):
    user_id = call.from_user.id
    data = user_data[str(user_id)]
    
    progress_percent = (data['mining_progress'] / data['max_mining']) * 100
    progress_bar = "🟢" * int(progress_percent / 10) + "⚪" * (10 - int(progress_percent / 10))
    
    mining_text = f"""⛏️ **التعدين التلقائي**

{progress_bar}
{data['mining_progress']:.2f} / {data['max_mining']:.2f} USDT

📊 التقدم: {progress_percent:.1f}%
⏰ الحالة: {'🟢 جاري التعدين...' if data['mining_progress'] < data['max_mining'] else '✅ اكتمل اليوم'}

💡 التعدين يعمل تلقائياً! عد لاحقاً لتحصيل أرباحك."""
    
    bot.edit_message_text(
        mining_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_mup=back_to_main_keyboard()
    )

def show_referrals(call):
    user_id = call.from_user.id
    data = user_data[str(user_id)]
    
    referrals_text = f"""👥 **نظام الإحالات المربح**

🎯 **الرابط الشخصي:**
`{get_referral_link(user_id)}`

📊 **إحصائياتك:**
• 👥 الإحالات: {data['referrals_count']}
• 💰 الأرباح: {data['referral_earnings']:.2f} USDT
• 📅 إحالات اليوم: {data['today_referrals']}

🎁 **المكافآت:**
• 🎊 1.00 USDT لكل صديق
• 💰 5.00 USDT مكافأة إضافية لكل 5 إحالات"""
    
    bot.edit_message_text(
        referrals_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=referrals_keyboard()
    )

def copy_referral_link(call):
    user_id = call.from_user.id
    referral_link = get_referral_link(user_id)
    
    bot.answer_callback_query(
        call.id,
        f"✅ تم نسخ رابط الدعوة!\n\n{referral_link}",
        show_alert=True
    )

def show_my_referrals(call):
    user_id = call.from_user.id
    data = user_data[str(user_id)]
    
    referrals_list = "👥 **قائمة الإحالات**\n\n"
    
    if data['referrals_count'] > 0:
        referrals_list += f"📊 إجمالي الإحالات: {data['referrals_count']}\n"
        referrals_list += f"💰 أرباح الإحالات: {data['referral_earnings']:.2f} USDT\n"
        referrals_list += f"📅 إحالات اليوم: {data['today_referrals']}\n\n"
        referrals_list += "🆔 **تم تسجيل الإحالات بواسطة:**\n"
        referrals_list += f"• نظام تتبع برقم المستخدم"
    else:
        referrals_list += "❌ لم تقم بدعوة أي أصدقاء بعد.\n\n"
        referrals_list += "🎯 استخدم رابط الدعوة الخاص بك لبدء جني الأرباح!"
    
    bot.edit_message_text(
        referrals_list,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=referrals_keyboard()
    )

def show_games(call):
    user_id = call.from_user.id
    data = user_data[str(user_id)]
    
    games_text = f"""🎮 **الألعاب والجوائز**

🎰 **لعبة السلوت**
• المحاولات: {data['attempts_left']}
• الجولات: {data['total_games_played']}

🏆 **الجوائز:**
• 3 رموز متطابقة: 🎉 1.00 USDT
• رمزين متطابقين: 🎊 0.25 USDT

💡 كل إحالة = +2 محاولات جديدة"""
    
    bot.edit_message_text(
        games_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=games_keyboard()
    )

def show_wallet(call):
    user_id = call.from_user.id
    data = user_data[str(user_id)]
    total_balance = data['wallet_balance'] + data['mining_earnings'] + data['referral_earnings']
    
    wallet_text = f"""💳 **المحفظة والشروط**

💰 **الرصيد المتاح:** {total_balance:.2f} USDT

💎 **عنوان الإيداع (BEP20):**
`0xfc712c9985507a2eb44df1ddfe7f09ff7613a19b`

📋 **متطلبات السحب:**
✅ 7 أيام تسجيل متتالي
✅ إيداع 10 USDT كحد أدنى  
✅ إكمال 5 مهام
✅ 3 إحالات على الأقل
✅ الحد الأدنى للسحب: 100 USDT"""
    
    bot.edit_message_text(
        wallet_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=wallet_keyboard()
    )

def copy_deposit_address(call):
    address = "0xfc712c9985507a2eb44df1ddfe7f09ff7613a19b"
    bot.answer_callback_query(
        call.id,
        f"✅ تم نسخ عنوان الإيداع!\n\n{address}",
        show_alert=True
    )

def play_slot_game(call):
    user_id = call.from_user.id
    data = user_data[str(user_id)]
    
    if data['attempts_left'] <= 0:
        bot.answer_callback_query(call.id, "❌ انتهت المحاولات! ادعُ أصدقاء للحصول على المزيد", show_alert=True)
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
    
    game_result = f"""🎰 **نتيجة اللعبة**

{' | '.join(result)}

{win_msg}

🔄 المحاولات المتبقية: {data['attempts_left']}"""
    
    bot.edit_message_text(
        game_result,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=games_keyboard()
    )

def show_tasks(call):
    user_id = call.from_user.id
    data = user_data[str(user_id)]
    
    tasks_text = f"""📋 **المهام اليومية**

🔥 تسجيل متتالي: {data['consecutive_days']}/7 أيام

✅ **المهام المتاحة:**
• تسجيل الدخول اليومي - 0.10 USDT
• اكتمال التعدين - 0.20 USDT  
• لعب 3 جولات - 0.15 USDT
• دعوة صديق - 1.00 USDT
• 7 أيام متتالية - 5.00 USDT

📊 المكتمل: {data['completed_tasks']}/5"""
    
    bot.edit_message_text(
        tasks_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=back_to_main_keyboard()
    )

def show_support(call):
    support_text = """📞 **الدعم الفني**

💬 لطلب المساعدة، اكتب رسالتك مباشرة في هذه الدردشة وسيتم إرسالها لفريق الدعم.

⏰ وقت الاستجابة: 24 ساعة

📝 **نصيحة:** اشرح مشكلتك بوضوح مع تقديم أي تفاصيل تساعد في حلها."""
    
    bot.edit_message_text(
        support_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=back_to_main_keyboard()
    )

def show_deposit(call):
    deposit_text = """💳 **طريقة الإيداع**

💎 **عنوان المحفظة (BEP20):**
`0xfc712c9985507a2eb44df1ddfe7f09ff7613a19b`

⚠️ **تنبيه مهم:**
• استخدم شبكة BEP20 فقط
• تأكد من العنوان قبل الإرسال
• الحد الأدنى للإيداع: 10 USDT

💰 بعد الإيداع، سيتم تحديث رصيدك تلقائياً."""
    
    bot.edit_message_text(
        deposit_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=wallet_keyboard()
    )

def show_withdraw(call):
    user_id = call.from_user.id
    data = user_data[str(user_id)]
    total_balance = data['wallet_balance'] + data['mining_earnings'] + data['referral_earnings']
    
    withdraw_text = f"""🔄 **طلب السحب**

💰 الرصيد المتاح: {total_balance:.2f} USDT

📋 **الشروط المطلوبة:**
{'✅' if data['consecutive_days'] >= 7 else '❌'} 7 أيام تسجيل متتالي
{'✅' if data['total_deposited'] >= 10 else '❌'} إيداع 10 USDT  
{'✅' if data['completed_tasks'] >= 5 else '❌'} إكمال 5 مهام
{'✅' if data['referrals_count'] >= 3 else '❌'} 3 إحالات على الأقل
{'✅' if total_balance >= 100 else '❌'} الحد الأدنى 100 USDT

💳 لطلب السحب، راسل الدعم الفني."""
    
    bot.edit_message_text(
        withdraw_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=wallet_keyboard()
    )

if __name__ == "__main__":
    print("🤖 بوت التعدين يعمل بنجاح...")
    bot.polling(none_stop=True)
