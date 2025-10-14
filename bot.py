import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
from datetime import datetime
import time
import threading
import requests
import logging

# 🔧 إعداد التسجيل للأخطاء
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

BOT_TOKEN = "8385331860:AAFTz51bMqPjtEBM50p_5WY_pbMytnqS0zc"
SUPPORT_USER_ID = "8400225549"
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# تخزين البيانات
user_data = {}
user_language = {}
support_messages = {}

# 🔄 إعدادات إعادة المحاولة
MAX_RETRIES = 10
RETRY_DELAY = 30

def keep_alive():
    """إرسال طلبات دورية للحفاظ على التشغيل"""
    while True:
        try:
            # إرسال ping لمنع النوم
            bot.get_me()
            logging.info("✅ البوت نشط - ping successful")
        except Exception as e:
            logging.warning(f"⚠️ فشل ping: {e}")
        
        # انتظر 5 دقائق بين كل ping
        time.sleep(300)

def auto_mining():
    """التعدين التلقائي في الخلفية"""
    while True:
        try:
            current_time = datetime.now()
            for user_id, data in user_data.items():
                time_diff = (current_time - data.get('last_update', current_time)).total_seconds()
                if time_diff >= 60:
                    if data['mining_progress'] < data['max_mining']:
                        data['mining_progress'] += 0.01
                        if data['mining_progress'] > data['max_mining']:
                            data['mining_progress'] = data['max_mining']
                        data['last_update'] = current_time
            
            time.sleep(60)
        except Exception as e:
            logging.error(f"❌ خطأ في التعدين: {e}")
            time.sleep(30)

def start_bot_with_retry():
    """تشغيل البوت مع إعادة محاولة ذكية"""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            logging.info(f"🔄 محاولة تشغيل البوت ({retries + 1}/{MAX_RETRIES})")
            
            # فحص اتصال البوت
            bot_info = bot.get_me()
            logging.info(f"✅ البوت يعمل: @{bot_info.username}")
            
            # بدء الخدمات الخلفية
            threading.Thread(target=keep_alive, daemon=True).start()
            threading.Thread(target=auto_mining, daemon=True).start()
            
            # بدء الاستماع للرسائل
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
            
        except Exception as e:
            retries += 1
            logging.error(f"❌ فشل التشغيل ({retries}/{MAX_RETRIES}): {e}")
            
            if retries < MAX_RETRIES:
                logging.info(f"⏳ انتظار {RETRY_DELAY} ثانية للمحاولة التالية...")
                time.sleep(RETRY_DELAY)
            else:
                logging.error("❌ تم تجاوز الحد الأقصى للمحاولات")
                break

# ... (بقية الكود كما هو مع إضافة logging في جميع الدوال) ...

if __name__ == "__main__":
    logging.info("🚀 بدء تشغيل البوت مع نظام 24/7...")
    start_bot_with_retry()
