# app.py - مع Webhook جديد
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os, json, time, tempfile, threading, random, requests
from datetime import datetime, timedelta

# ---------------- CONFIG ----------------
BOT_TOKEN = "8385331860:AAHj0uPnpJf_JYtHjALIkmavsBNnpa_Gd2Y"
ADMIN_ID = 8400225549
SUPPORT_USERNAME = "Trust_wallet_Support_3"
DATA_FILE = "database.json"
AUTOSAVE_INTERVAL = 60
WEBHOOK_BASE = "https://usdt-bot-live.onrender.com"
# -------------------------------------------------

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ... (كل الدوال السابقة تبقى نفسها)

# ---------- Flask webhook endpoints ----------
@app.route("/")
def index():
    return "Bot is running", 200

# مسار Webhook جديد وبسيط
@app.route("/webhook", methods=["POST"])
def webhook_endpoint():
    print(f"🔔 Webhook called at {datetime.utcnow().isoformat()}")
    
    if request.headers.get("content-type") == "application/json":
        try:
            json_data = request.get_data().decode('utf-8')
            print(f"📨 RAW DATA: {json_data}")
            
            update = telebot.types.Update.de_json(json_data)
            print(f"🔄 Processing update: {update.update_id}")
            
            bot.process_new_updates([update])
            print("✅ Update processed successfully")
            return "OK", 200
            
        except Exception as e:
            print(f"❌ Webhook processing error: {e}")
            import traceback
            traceback.print_exc()
            return "Error", 500
    
    print("❌ Invalid content-type")
    return "Forbidden", 403

# إعداد Webhook
@app.before_first_request
def setup_webhook():
    try:
        # احذف أي Webhook موجود
        bot.remove_webhook()
        time.sleep(2)
        
        # عيّن الـ Webhook الجديد
        webhook_url = f"{WEBHOOK_BASE}/webhook"
        result = bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook set to: {webhook_url}")
        print(f"✅ SetWebhook result: {result}")
        
    except Exception as e:
        print(f"❌ Webhook setup error: {e}")

# ---------- startup ----------
if __name__ == "__main__":
    print("🚀 Starting bot...")
    load_data()
    
    t1 = threading.Thread(target=autosave_loop, daemon=True)
    t1.start()
    
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Server running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
