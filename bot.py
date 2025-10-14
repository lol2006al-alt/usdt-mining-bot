import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
from datetime import datetime
import time
import threading

BOT_TOKEN = "8385331860:AAFTz51bMqPjtEBM50p_5WY_pbMytnqS0zc"
SUPPORT_USER_ID = "8400225549"  # 🔥 ضع هنا ID حسابك الشخصي
bot = telebot.TeleBot(BOT_TOKEN)

# تخزين البيانات
user_data = {}
user_language = {}
support_messages = {}

# نصوص متعددة اللغات
texts = {
    'ar': {
        'welcome': "🎉 أهلاً بك في محفظة تعدين USDT!",
        'balance': "💰 الرصيد",
        'mining': "⛏️ التعدين", 
        'referrals': "👥 الإحالات",
        'games': "🎮 الألعاب",
        'tasks': "📋 المهام",
        'wallet': "💳 المحفظة",
        'support': "📞 الدعم",
        'back': "🔙 الرئيسية",
        'your_balance': "💰 رصيدك: {:.2f} USDT",
        'mining_status': "⛏️ التعدين: {:.2f}/2.00 USDT\n📊 التقدم: {:.1f}%",
        'referrals_count': "👥 الإحالات: {}",
        'choose_language': "🌍 اختر اللغة",
        'mining_progress': "🔄 جاري التعدين تلقائياً...",
        'support_title': "📞 الدعم الفني",
        'support_desc': "💬 اكتب رسالتك وسيتم إرسالها مباشرة إلى فريق الدعم\n\n⏰ وقت الاستجابة: 24 ساعة",
        'support_success': "✅ تم إرسال رسالتك إلى الدعم!\n\nسيتم الرد عليك قريباً.",
        'support_prompt': "✍️ اكتب رسالتك الآن:",
        'support_error': "⚠️ الرسالة قصيرة جداً. يرجى كتابة تفاصيل أكثر."
    },
    'en': {
        'welcome': "🎉 Welcome to USDT Mining Wallet!",
        'balance': "💰 Balance",
        'mining': "⛏️ Mining",
        'referrals': "👥 Referrals",
        'games': "🎮 Games",
        'tasks': "📋 Tasks",
        'wallet': "💳 Wallet",
        'support': "📞 Support",
        'back': "🔙 Main",
        'your_balance': "💰 Your balance: {:.2f} USDT",
        'mining_status': "⛏️ Mining: {:.2f}/2.00 USDT\n📊 Progress: {:.1f}%",
        'referrals_count': "👥 Referrals: {}",
        'choose_language': "🌍 Choose language",
        'mining_progress': "🔄 Auto mining in progress...",
        'support_title': "📞 Technical Support",
        'support_desc': "💬 Write your message and it will be sent directly to the support team\n\n⏰ Response time: 24 hours",
        'support_success': "✅ Your message has been sent to support!\n\nYou will be replied to soon.",
        'support_prompt': "✍️ Write your message now:",
        'support_error': "⚠️ Message is too short. Please write more details."
    }
}

def get_text(user_id, key, **kwargs):
    lang = user_language.get(str(user_id), 'ar')
    text = texts[lang].get(key, key)
    return text.format(**kwargs) if kwargs else text

def send_support_notification(user_id, message_text, username, first_name):
    """إرسال إشعار الدعم إلى حسابك الشخصي"""
    try:
        notification = f"""
📩 **رسالة دعم جديدة**

👤 **المستخدم:** {first_name} (@{username})
🆔 **ID:** `{user_id}`
📅 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💬 **الرسالة:**
{message_text}
        """.strip()
        
        # إرسال الرسالة إلى حسابك الشخصي
        bot.send_message(SUPPORT_USER_ID, notification, parse_mode='Markdown')
        return True
    except Exception as e:
        print(f"❌ خطأ في إرسال إشعار الدعم: {e}")
        return False

def language_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
        InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
    )
    return keyboard

def main_menu_keyboard(user_id):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(get_text(user_id, 'balance'), callback_data="balance"),
        InlineKeyboardButton(get_text(user_id, 'mining'), callback_data="mining")
    )
    keyboard.add(
        InlineKeyboardButton(get_text(user_id, 'referrals'), callback_data="referrals"),
        InlineKeyboardButton(get_text(user_id, 'games'), callback_data="games")
    )
    keyboard.add(
        InlineKeyboardButton(get_text(user_id, 'tasks'), callback_data="tasks"),
        InlineKeyboardButton(get_text(user_id, 'wallet'), callback_data="wallet")
    )
    keyboard.add(InlineKeyboardButton(get_text(user_id, 'support'), callback_data="support"))
    keyboard.add(InlineKeyboardButton("🌍 تغيير اللغة", callback_data="change_language"))
    return keyboard

def back_keyboard(user_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(get_text(user_id, 'back'), callback_data="main_menu"))
    return keyboard

def support_keyboard(user_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📩 إرسال رسالة", callback_data="send_support_message"))
    keyboard.add(InlineKeyboardButton(get_text(user_id, 'back'), callback_data="main_menu"))
    return keyboard

def init_user(user_id):
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
            'wallet_balance': 0.0,
            'mining_earnings': 0.0,
            'referrals_count': 0,
            'mining_progress': 0.0,
            'max_mining': 2.0,
            'attempts_left': 10,
            'user_id': str(user_id),
            'referral_earnings': 0.0,
            'last_update': datetime.now()
        }

def auto_mining():
    """التعدين التلقائي في الخلفية"""
    while True:
        try:
            current_time = datetime.now()
            for user_id, data in user_data.items():
                # تحديث التعدين كل دقيقة
                time_diff = (current_time - data['last_update']).total_seconds()
                if time_diff >= 60:  # كل دقيقة
                    if data['mining_progress'] < data['max_mining']:
                        data['mining_progress'] += 0.01
                        if data['mining_progress'] > data['max_mining']:
                            data['mining_progress'] = data['max_mining']
                        data['last_update'] = current_time
            
            time.sleep(60)  # انتظر دقيقة بين كل تحديث
        except Exception as e:
            print(f"⚠️ خطأ في التعدين التلقائي: {e}")
            time.sleep(30)

# بدء التعدين التلقائي في thread منفصل
mining_thread = threading.Thread(target=auto_mining, daemon=True)
mining_thread.start()

@bot.message_handler(commands=['start', 'test', 'language'])
def start_cmd(message):
    try:
        user_id = message.from_user.id
        
        if str(user_id) not in user_language:
            # إذا لم يختر لغة بعد
            bot.send_message(
                user_id, 
                get_text(user_id, 'choose_language'),
                reply_markup=language_keyboard()
            )
            return
        
        init_user(user_id)
        
        # معالجة الإحالة
        if len(message.text.split()) > 1:
            referrer_id = message.text.split()[1]
            if referrer_id.isdigit() and referrer_id != str(user_id):
                user_data[str(user_id)]['referred_by'] = referrer_id
                if referrer_id in user_data:
                    user_data[referrer_id]['referrals_count'] += 1
                    user_data[referrer_id]['referral_earnings'] += 1.0
        
        welcome = f"""{get_text(user_id, 'welcome')}

{get_text(user_id, 'your_balance', balance=user_data[str(user_id)]['wallet_balance'])}
{get_text(user_id, 'mining_status', 
          progress=user_data[str(user_id)]['mining_progress'],
          percent=(user_data[str(user_id)]['mining_progress'] / 2.0) * 100)}
{get_text(user_id, 'referrals_count', count=user_data[str(user_id)]['referrals_count'])}

🚀 اختر من الأزرار أدناه:"""
        
        bot.send_message(user_id, welcome, reply_markup=main_menu_keyboard(user_id))
        
    except Exception as e:
        print(f"❌ خطأ في /start: {e}")
        try:
            bot.send_message(user_id, "⚠️ حدث خطأ، يرجى المحاولة مرة أخرى")
        except:
            pass

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    try:
        user_id = call.from_user.id
        init_user(user_id)
        data = user_data[str(user_id)]
        
        if call.data.startswith('lang_'):
            # اختيار اللغة
            lang = call.data.split('_')[1]
            user_language[str(user_id)] = lang
            bot.answer_callback_query(call.id, f"✅ تم اختيار اللغة / Language selected")
            
            # إرسال القائمة الرئيسية بعد اختيار اللغة
            welcome = f"""{get_text(user_id, 'welcome')}

{get_text(user_id, 'your_balance', balance=data['wallet_balance'])}
{get_text(user_id, 'mining_status', 
          progress=data['mining_progress'],
          percent=(data['mining_progress'] / 2.0) * 100)}
{get_text(user_id, 'referrals_count', count=data['referrals_count'])}

🚀 اختر من الأزرار:"""
            
            bot.edit_message_text(
                welcome,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=main_menu_keyboard(user_id)
            )
            return
        
        elif call.data == "change_language":
            bot.edit_message_text(
                get_text(user_id, 'choose_language'),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=language_keyboard()
            )
            return
        
        elif call.data == "main_menu":
            welcome = f"""{get_text(user_id, 'welcome')}

{get_text(user_id, 'your_balance', balance=data['wallet_balance'])}
{get_text(user_id, 'mining_status', 
          progress=data['mining_progress'],
          percent=(data['mining_progress'] / 2.0) * 100)}
{get_text(user_id, 'referrals_count', count=data['referrals_count'])}

🚀 اختر من الأزرار:"""
            
            bot.edit_message_text(
                welcome,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=main_menu_keyboard(user_id)
            )
        
        elif call.data == "balance":
            total = data['wallet_balance'] + data['mining_earnings'] + data['referral_earnings']
            balance_text = f"""{get_text(user_id, 'your_balance', balance=total)}

💼 الرصيد الرئيسي: {data['wallet_balance']:.2f} USDT
⛏️ أرباح التعدين: {data['mining_earnings']:.2f} USDT  
👥 أرباح الإحالات: {data['referral_earnings']:.2f} USDT"""
            
            bot.edit_message_text(
                balance_text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=back_keyboard(user_id)
            )
        
        elif call.data == "mining":
            progress_percent = (data['mining_progress'] / data['max_mining']) * 100
            progress_bar = "🟢" * int(progress_percent / 10) + "⚪" * (10 - int(progress_percent / 10))
            
            mining_text = f"""⛏️ **التعدين التلقائي**

{progress_bar}
{data['mining_progress']:.2f} / {data['max_mining']:.2f} USDT

📊 التقدم: {progress_percent:.1f}%
⏰ الحالة: {'🟢 جاري التعدين...' if data['mining_progress'] < data['max_mining'] else '✅ اكتمل اليوم'}

{get_text(user_id, 'mining_progress')}"""
            
            bot.edit_message_text(
                mining_text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=back_keyboard(user_id)
            )
        
        elif call.data == "referrals":
            link = f"https://t.me/BNBMini1Bot?start={user_id}"
            referrals_text = f"""👥 **نظام الإحالات**

🎯 **رابط الدعوة:**
`{link}`

📊 **إحصائياتك:**
• 👥 الإحالات: {data['referrals_count']}
• 💰 الأرباح: {data['referral_earnings']:.2f} USDT

🎁 **المكافآت:**
• 1.00 USDT لكل صديق
• 5.00 USDT مكافأة إضافية لكل 5 إحالات"""
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("📋 نسخ رابط الدعوة", callback_data="copy_referral"))
            keyboard.add(InlineKeyboardButton(get_text(user_id, 'back'), callback_data="main_menu"))
            
            bot.edit_message_text(
                referrals_text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
        
        elif call.data == "copy_referral":
            link = f"https://t.me/BNBMini1Bot?start={user_id}"
            bot.answer_callback_query(call.id, f"✅ تم نسخ رابط الدعوة!\n{link}", show_alert=True)
        
        elif call.data == "support":
            support_text = f"""{get_text(user_id, 'support_title')}

{get_text(user_id, 'support_desc')}"""
            
            bot.edit_message_text(
                support_text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=support_keyboard(user_id)
            )
        
        elif call.data == "send_support_message":
            # طلب إدخال رسالة الدعم
            bot.send_message(
                user_id, 
                get_text(user_id, 'support_prompt')
            )
            # حفظ حالة المستخدم لاستقبال الرسالة التالية
            support_messages[str(user_id)] = True
        
        elif call.data in ["games", "tasks", "wallet"]:
            messages = {
                "games": "🎮 **الألعاب قريباً**\n\nسيتم إضافة الألعاب قريباً بمكافآت USDT!",
                "tasks": "📋 **المهام قريباً**\n\nسيتم إضافة المهام اليومية قريباً!",
                "wallet": "💳 **المحفظة قريباً**\n\nسيتم تفعيل الإيداع والسحب قريباً!"
            }
            
            bot.edit_message_text(
                messages[call.data],
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=back_keyboard(user_id)
            )
            
    except Exception as e:
        print(f"❌ خطأ في callback: {e}")
        try:
            bot.answer_callback_query(call.id, "⚠️ حدث خطأ، يرجى المحاولة مرة أخرى")
        except:
            pass

# معالجة رسائل الدعم من المستخدمين
@bot.message_handler(func=lambda message: True)
def handle_support_messages(message):
    try:
        user_id = message.from_user.id
        
        # إذا كان المستخدم في وضع إرسال رسالة دعم
        if str(user_id) in support_messages and support_messages[str(user_id)]:
            message_text = message.text.strip()
            
            if len(message_text) < 5:
                bot.send_message(user_id, get_text(user_id, 'support_error'))
                return
            
            # إرسال الرسالة إلى حسابك الشخصي
            success = send_support_notification(
                user_id, 
                message_text,
                message.from_user.username or "بدون معرف",
                message.from_user.first_name or "بدون اسم"
            )
            
            if success:
                bot.send_message(user_id, get_text(user_id, 'support_success'))
                print(f"✅ تم إرسال رسالة دعم من user_id: {user_id}")
            else:
                bot.send_message(user_id, "❌ فشل في إرسال الرسالة، يرجى المحاولة لاحقاً")
            
            # إعادة تعيين حالة الدعم
            support_messages[str(user_id)] = False
            
            # العودة للقائمة الرئيسية
            welcome = f"""{get_text(user_id, 'welcome')}

{get_text(user_id, 'your_balance', balance=user_data[str(user_id)]['wallet_balance'])}
{get_text(user_id, 'mining_status', 
          progress=user_data[str(user_id)]['mining_progress'],
          percent=(user_data[str(user_id)]['mining_progress'] / 2.0) * 100)}
{get_text(user_id, 'referrals_count', count=user_data[str(user_id)]['referrals_count'])}

🚀 اختر من الأزرار:"""
            
            bot.send_message(user_id, welcome, reply_markup=main_menu_keyboard(user_id))
            
        else:
            # إذا لم يكن في وضع دعم، إرسال القائمة الرئيسية
            if str(user_id) not in user_language:
                bot.send_message(user_id, get_text(user_id, 'choose_language'), reply_markup=language_keyboard())
            else:
                bot.send_message(user_id, "🔍 استخدم الأزرار من خلال /start", reply_markup=main_menu_keyboard(user_id))
                
    except Exception as e:
        print(f"❌ خطأ في معالجة رسالة الدعم: {e}")

@bot.message_handler(commands=['status'])
def status_cmd(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "✅ البوت يعمل بشكل طبيعي! 🟢")

def start_bot():
    while True:
        try:
            print("🔄 جاري تشغيل البوت...")
            bot_info = bot.get_me()
            print(f"✅ البوت يعمل: @{bot_info.username}")
            print(f"🎯 ID حساب الدعم: {SUPPORT_USER_ID}")
            
            # بدء الاستماع للرسائل
            bot.polling(none_stop=True, timeout=30)
            
        except Exception as e:
            print(f"❌ خطأ في البوت: {e}")
            print("🔄 إعادة المحاولة خلال 10 ثوان...")
            time.sleep(10)

if __name__ == "__main__":
    print("🚀 بدء تشغيل بوت التعدين مع نظام الدعم...")
    start_bot()
