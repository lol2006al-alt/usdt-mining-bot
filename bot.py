import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
from datetime import datetime, timedelta
import time
import hashlib
import json
import os
from flask import Flask, request

# 🔧 إعدادات Render - ضرورية للعمل على السحابة
app = Flask(__name__)
PORT = int(os.environ.get('PORT', 10000))

# 🔧 إعدادات البوت
BOT_TOKEN = "8385331860:AAFTz51bMqPjtEBM50p_5WY_pbMytnqS0zc"
SUPPORT_USER_ID = "YOUR_USER_ID_HERE"  # 8400225549

bot = telebot.TeleBot(BOT_TOKEN)
WEBHOOK_URL = f"https://usdt-mining-bot-wmvf.onrender.com/{BOT_TOKEN}"

# أنظمة التخزين
user_data = {}
deposit_requests = {}
vip_users = {}

# نظام VIP
vip_system = {
    "BRONZE": {
        "name": "🟢 VIP برونزي",
        "price": 5.0,
        "bonus": 0.10,
        "features": ["+10% أرباح تعدين", "دعم سريع", "مهام إضافية"],
        "duration": 30,
        "color": "🟢"
    },
    "SILVER": {
        "name": "🔵 VIP فضى", 
        "price": 10.0,
        "bonus": 0.25,
        "features": ["+25% أرباح تعدين", "دعم مميز", "مهام حصرية"],
        "duration": 30,
        "color": "🔵"
    },
    "GOLD": {
        "name": "🟡 VIP ذهبي",
        "price": 20.0, 
        "bonus": 0.50,
        "features": ["+50% أرباح تعدين", "دعم فوري", "مكافآت يومية"],
        "duration": 30,
        "color": "🟡"
    }
}

# عنوان محفظتك الرئيسي
MAIN_WALLET = "0xfc712c9985507a2eb44df1ddfe7f09ff7613a19b"

def init_user(user_id):
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
            'balance': 0.0,
            'mining_earnings': 0.0,
            'referrals_count': 0,
            'total_deposited': 0.0,
            'vip_level': None,
            'vip_expiry': None,
            'deposit_codes': [],
            'user_id': str(user_id)
        }

def generate_deposit_code(user_id, vip_type):
    """إنشاء كود إيداع فريد"""
    price = vip_system[vip_type]['price']
    code = f"DEP{user_id}{int(time.time())}{random.randint(1000,9999)}"
    
    deposit_requests[code] = {
        'user_id': user_id,
        'vip_type': vip_type,
        'amount': price,
        'status': 'pending',
        'created_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(hours=24)
    }
    
    return code, price

def verify_deposit_manual(code):
    """التحقق اليدوي من الإيداع (ستقوم به أنت)"""
    if code in deposit_requests:
        request = deposit_requests[code]
        if request['status'] == 'pending':
            return True
    return False

def activate_vip(user_id, vip_type):
    """تفعيل VIP للمستخدم"""
    user_data[str(user_id)]['vip_level'] = vip_type
    user_data[str(user_id)]['vip_expiry'] = datetime.now() + timedelta(days=30)
    vip_users[str(user_id)] = {
        'level': vip_type,
        'activated_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(days=30)
    }

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

def get_vip_benefits(user_id):
    """الحصول على مزايا VIP للمستخدم"""
    if str(user_id) in vip_users:
        vip_info = vip_users[str(user_id)]
        if vip_info['expires_at'] > datetime.now():
            return vip_system[vip_info['level']]['bonus']
    return 0.0

@bot.message_handler(commands=['start'])
def start_command(message):
    """بدء البوت"""
    user_id = message.from_user.id
    init_user(user_id)
    
    welcome_text = """
🎉 أهلاً بك في بوت التعدين!

استخدم /vip لعرض باقات العضويات
    """
    bot.send_message(user_id, welcome_text)

@bot.message_handler(commands=['vip'])
def vip_command(message):
    """عرض باقات VIP"""
    user_id = message.from_user.id
    init_user(user_id)
    
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
    
    bot.send_message(user_id, vip_text, reply_markup=vip_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == 'vip_menu')
def vip_menu(call):
    """عرض قائمة VIP"""
    vip_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == 'main_menu')
def main_menu(call):
    """القائمة الرئيسية"""
    user_id = call.from_user.id
    start_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith('vip_'))
def handle_vip_selection(call):
    """معالجة اختيار باقة VIP"""
    user_id = call.from_user.id
    vip_type = call.data.split('_')[1]
    
    if vip_type in vip_system:
        vip_info = vip_system[vip_type]
        
        # إنشاء كود إيداع
        deposit_code, amount = generate_deposit_code(user_id, vip_type)
        
        deposit_text = f"""🎯 **طلب شراء {vip_info['name']}**

💵 المبلغ المطلوب: {amount} USDT
🆔 كود الإيداع: `{deposit_code}`

💎 **عنوان المحفظة:**
`{MAIN_WALLET}`

📋 **خطوات الشراء:**
1. أرسل {amount} USDT إلى العنوان أعلاه
2. استخدم الشبكة: **BEP20**
3. في وصف التحويل اكتب: **{deposit_code}**

⏰ سيتم التحقق من الإيداع خلال 24 ساعة
✅ بعد التحقق سيتم تفعيل VIP تلقائياً"""

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔍 تحقق من الإيداع", callback_data=f"check_deposit_{deposit_code}"))
        keyboard.add(InlineKeyboardButton("🔙 عودة للباقات", callback_data="vip_menu"))
        
        bot.edit_message_text(
            deposit_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('check_deposit_'))
def check_deposit_status(call):
    """التحقق من حالة الإيداع"""
    user_id = call.from_user.id
    deposit_code = call.data.split('_')[2]
    
    if deposit_code in deposit_requests:
        request = deposit_requests[deposit_code]
        
        if request['status'] == 'completed':
            bot.answer_callback_query(call.id, "✅ تم تفعيل VIP بنجاح!", show_alert=True)
            
            # تحديث واجهة المستخدم
            vip_info = vip_system[request['vip_type']]
            success_text = f"""🎉 **تم تفعيل {vip_info['name']} بنجاح!**

⭐ الآن يمكنك الاستمتاع بالمزايا:
"""
            for feature in vip_info['features']:
                success_text += f"• {feature}\n"
            
            success_text += f"\n⏰ تنتهي العضوية: {request['created_at'] + timedelta(days=30):%Y-%m-%d}"
            
            bot.edit_message_text(
                success_text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")
                )
            )
            
        else:
            bot.answer_callback_query(
                call.id, 
                "⏳ جاري التحقق من الإيداع...\nسيتم التفويح تلقائياً عند اكتماله", 
                show_alert=True
            )
    else:
        bot.answer_callback_query(call.id, "❌ كود الإيداع غير صحيح", show_alert=True)

# 🔧 أوامر التحكم للمسؤول (أنت)
@bot.message_handler(commands=['verify_deposit'])
def verify_deposit_admin(message):
    """أمر للمسؤول للتحقق من الإيداع"""
    user_id = message.from_user.id
    
    # ⚠️ غير قيمة SUPPORT_USER_ID إلى ID حسابك
    if str(user_id) != SUPPORT_USER_ID:
        bot.send_message(user_id, "❌ ليس لديك صلاحية لهذا الأمر")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(user_id, "⚙️ استخدام: /verify_deposit [كود_الإيداع]")
        return
    
    deposit_code = parts[1]
    
    if deposit_code in deposit_requests:
        request = deposit_requests[deposit_code]
        
        if request['status'] == 'pending':
            # تفعيل VIP
            activate_vip(request['user_id'], request['vip_type'])
            deposit_requests[deposit_code]['status'] = 'completed'
            
            # إشعار المستخدم
            try:
                vip_info = vip_system[request['vip_type']]
                bot.send_message(
                    request['user_id'],
                    f"🎉 **تم تفعيل {vip_info['name']} بنجاح!**\n\n"
                    f"شكراً لثقتك! يمكنك الآن الاستمتاع بجميع مزايا العضوية."
                )
            except:
                pass
            
            bot.send_message(user_id, f"✅ تم تفعيل VIP للمستخدم {request['user_id']}")
        else:
            bot.send_message(user_id, "⚠️ هذا الإيداع تم التحقق منه مسبقاً")
    else:
        bot.send_message(user_id, "❌ كود الإيداع غير موجود")

@bot.message_handler(commands=['pending_deposits'])
def pending_deposits_admin(message):
    """عرض الإيداعات المنتظرة التحقق"""
    user_id = message.from_user.id
    
    if str(user_id) != SUPPORT_USER_ID:
        return
    
    pending = []
    for code, request in deposit_requests.items():
        if request['status'] == 'pending':
            pending.append(f"كود: {code} | مستخدم: {request['user_id']} | مبلغ: {request['amount']} USDT")
    
    if pending:
        bot.send_message(user_id, "📋 الإيداعات المنتظرة:\n" + "\n".join(pending))
    else:
        bot.send_message(user_id, "✅ لا توجد إيداعات منتظرة")

# 🌐 Webhook Routes for Render
@app.route('/')
def home():
    return "🤖 البوت يعمل بشكل صحيح! - VIP Mining Bot"

@app.route('/health')
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

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

@app.route('/remove_webhook')
def remove_webhook_route():
    """إزالة webhook"""
    try:
        bot.remove_webhook()
        return "✅ تم إزالة Webhook"
    except Exception as e:
        return f"❌ خطأ في إزالة Webhook: {e}"

if __name__ == "__main__":
    print("🚀 بدأ تشغيل البوت مع Webhook...")
    
    # تعيين Webhook تلقائياً عند التشغيل
    try:
        bot.remove_webhook()
        time.sleep(2)
        bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ Webhook مضبوط على: {WEBHOOK_URL}")
    except Exception as e:
        print(f"⚠️ تحذير في تعيين Webhook: {e}")
    
    # تشغيل الخادم
    print(f"🌐 بدأ تشغيل الخادم على المنفذ {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
