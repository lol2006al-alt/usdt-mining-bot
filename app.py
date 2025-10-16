# app.py
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import random
import json
import time
from datetime import datetime, timedelta
import threading
import tempfile

# -------------------------
# CONFIG
# -------------------------
BOT_TOKEN = "8385331860:AAHj0uPnpJf_JYtHjALIkmavsBNnpa_Gd2Y"
ADMIN_ID = 8400225549  # الايدي تبعك
WALLET_ADDRESS = "0xfc712c9985507a2eb44df1ddfe7f09ff7613a19b"  # مجرد عرض، لا عمليات مالية من الكود
DATA_FILE = "database.json"
AUTOSAVE_INTERVAL = 60  # ثانية: كل كم يحفظ تلقائياً

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# -------------------------
# In-memory mirror to file
# -------------------------
data = {
    "users": {},        # user_id (str) -> user object
    "referrals": [],    # list of referral dicts
    "backups": [],      # metadata backups
    "transactions": []  # operations log (رمزي)
}

lock = threading.Lock()

# -------------------------
# Atomic file write helpers
# -------------------------
def atomic_write(path, content):
    fd, tmp_path = tempfile.mkstemp(dir=".", prefix=".tmpdb_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

def load_data():
    global data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
                    print(f"✅ Loaded data from {DATA_FILE}")
        except Exception as e:
            print(f"❌ Failed to load {DATA_FILE}: {e}")
    else:
        save_data()  # create file

def save_data():
    with lock:
        try:
            atomic_write(DATA_FILE, json.dumps(data, ensure_ascii=False, indent=2))
            # print timestamp for debug
            print(f"✅ Saved data to {DATA_FILE} at {datetime.now().isoformat()}")
            return True
        except Exception as e:
            print(f"❌ Error saving data: {e}")
            return False

def autosave_worker():
    while True:
        time.sleep(AUTOSAVE_INTERVAL)
        save_data()

# -------------------------
# Data helpers
# -------------------------
def get_user(user_id):
    uid = str(user_id)
    with lock:
        if uid not in data["users"]:
            data["users"][uid] = {
                "user_id": int(uid),
                "username": "",
                "first_name": "",
                "last_name": "",
                "balance": 0.0,
                "referrals_count": 0,
                "referrer_id": None,
                "vip_level": 0,
                "vip_expiry": None,
                "games_played_today": 0,
                "total_games_played": 0,
                "total_earned": 0.0,
                "total_deposits": 0.0,
                "games_counter": 0,
                "last_daily_bonus": None,
                "withdrawal_attempts": 0,
                "new_referrals_count": 0,
                "lang": "ar",
                "banned": False,
                "registration_date": datetime.now().isoformat()
            }
            save_data()
        return data["users"][uid]

def save_user(user_obj):
    with lock:
        data["users"][str(user_obj["user_id"])] = user_obj
        save_data()
    return True

def add_balance(user_id, amount, description="", is_deposit=False):
    user = get_user(user_id)
    user["balance"] = round(user.get("balance", 0.0) + float(amount), 8)
    user["total_earned"] = round(user.get("total_earned", 0.0) + float(amount), 8)
    if is_deposit:
        user["total_deposits"] = round(user.get("total_deposits", 0.0) + float(amount), 8)
    with lock:
        data["transactions"].append({
            "user_id": int(user_id),
            "type": "deposit" if is_deposit else "bonus",
            "amount": float(amount),
            "description": description,
            "timestamp": datetime.now().isoformat()
        })
        save_data()
    return True

def add_referral(referrer_id, referred_id):
    if int(referrer_id) == int(referred_id):
        return False
    with lock:
        for r in data["referrals"]:
            if r["referrer_id"] == int(referrer_id) and r["referred_id"] == int(referred_id):
                return False
        data["referrals"].append({
            "referrer_id": int(referrer_id),
            "referred_id": int(referred_id),
            "bonus_given": True,
            "timestamp": datetime.now().isoformat()
        })
        ref = get_user(referrer_id)
        ref["referrals_count"] = ref.get("referrals_count", 0) + 1
        add_balance(referrer_id, 1.0, f"Referral bonus for {referred_id}")
        add_balance(referred_id, 1.0, "Referral join bonus")
        ref["games_played_today"] = max(0, ref.get("games_played_today", 0) - 1)
        save_data()
    return True

# -------------------------
# UI: keyboards (supports Arabic + English toggle)
# -------------------------
def create_main_menu(lang="ar"):
    kb = InlineKeyboardMarkup(row_width=2)
    if lang == "ar":
        kb.add(
            InlineKeyboardButton("🎮 الألعاب (3 محاولات)", callback_data="games_menu"),
            InlineKeyboardButton("📊 الملف الشخصي", callback_data="profile")
        )
        kb.add(
            InlineKeyboardButton("👥 الإحالات (+1 محاولة)", callback_data="referral"),
            InlineKeyboardButton("💰 سحب رصيد", callback_data="withdraw")
        )
        kb.add(
            InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_3"),
            InlineKeyboardButton("💎 باقات VIP", callback_data="vip_packages")
        )
        kb.add(InlineKeyboardButton("🌐 EN", callback_data="lang_toggle"))
    else:
        kb.add(
            InlineKeyboardButton("🎮 Games (3 tries)", callback_data="games_menu"),
            InlineKeyboardButton("📊 Profile", callback_data="profile")
        )
        kb.add(
            InlineKeyboardButton("👥 Referrals (+1 try)", callback_data="referral"),
            InlineKeyboardButton("💰 Withdraw", callback_data="withdraw")
        )
        kb.add(
            InlineKeyboardButton("🆘 Support", url="https://t.me/Trust_wallet_Support_3"),
            InlineKeyboardButton("💎 VIP Packages", callback_data="vip_packages")
        )
        kb.add(InlineKeyboardButton("🌐 AR", callback_data="lang_toggle"))
    return kb

def create_games_menu(lang="ar"):
    kb = InlineKeyboardMarkup(row_width=2)
    if lang == "ar":
        kb.add(
            InlineKeyboardButton("🎰 سلوتس", callback_data="game_slots"),
            InlineKeyboardButton("🎲 النرد", callback_data="game_dice")
        )
        kb.add(
            InlineKeyboardButton("⚽ كرة القدم", callback_data="game_football"),
            InlineKeyboardButton("🏀 السلة", callback_data="game_basketball")
        )
        kb.add(
            InlineKeyboardButton("🎯 السهم", callback_data="game_darts"),
            InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")
        )
    else:
        kb.add(
            InlineKeyboardButton("🎰 Slots", callback_data="game_slots"),
            InlineKeyboardButton("🎲 Dice", callback_data="game_dice")
        )
        kb.add(
            InlineKeyboardButton("⚽ Football", callback_data="game_football"),
            InlineKeyboardButton("🏀 Basketball", callback_data="game_basketball")
        )
        kb.add(
            InlineKeyboardButton("🎯 Darts", callback_data="game_darts"),
            InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
        )
    return kb

def create_vip_keyboard(lang="ar"):
    kb = InlineKeyboardMarkup(row_width=1)
    if lang == "ar":
        kb.add(InlineKeyboardButton("🟢 برونزي - 5 USDT", callback_data="buy_bronze"))
        kb.add(InlineKeyboardButton("🔵 فضى - 10 USDT", callback_data="buy_silver"))
        kb.add(InlineKeyboardButton("🟡 ذهبي - 20 USDT", callback_data="buy_gold"))
        kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
    else:
        kb.add(InlineKeyboardButton("🟢 Bronze - 5 USDT", callback_data="buy_bronze"))
        kb.add(InlineKeyboardButton("🔵 Silver - 10 USDT", callback_data="buy_silver"))
        kb.add(InlineKeyboardButton("🟡 Gold - 20 USDT", callback_data="buy_gold"))
        kb.add(InlineKeyboardButton("🔙 Back", callback_data="main_menu"))
    return kb

def create_withdraw_keyboard(lang="ar"):
    kb = InlineKeyboardMarkup()
    if lang == "ar":
        kb.add(InlineKeyboardButton("💳 تأكيد استخدام BEP20", callback_data="confirm_bep20"))
        kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
    else:
        kb.add(InlineKeyboardButton("💳 Confirm BEP20", callback_data="confirm_bep20"))
        kb.add(InlineKeyboardButton("🔙 Back", callback_data="main_menu"))
    return kb

def create_referral_keyboard(user_id, lang="ar"):
    kb = InlineKeyboardMarkup()
    referral_link = f"https://t.me/BNBMini1Bot?start={user_id}"
    if lang == "ar":
        kb.add(InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={referral_link}&text=انضم إلى هذا البوت واحصل على 1.0 USDT!"))
        kb.add(InlineKeyboardButton("🔗 نسخ الرابط", callback_data="copy_link"))
        kb.add(InlineKeyboardButton("📊 إحالاتي", callback_data="my_referrals"))
        kb.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
    else:
        kb.add(InlineKeyboardButton("📤 Share link", url=f"https://t.me/share/url?url={referral_link}&text=Join this bot and get 1.0 USDT!"))
        kb.add(InlineKeyboardButton("🔗 Copy link", callback_data="copy_link"))
        kb.add(InlineKeyboardButton("📊 My referrals", callback_data="my_referrals"))
        kb.add(InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu"))
    return kb, referral_link

# -------------------------
# Games logic (unchanged behavior)
# -------------------------
def play_slots_game(user_id):
    symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎"]
    result = [random.choice(symbols) for _ in range(3)]
    if result[0] == result[1] == result[2]:
        win_amount = 5.0
    elif result[0] == result[1] or result[1] == result[2]:
        win_amount = 2.0
    else:
        win_amount = 0.0
    return result, win_amount

def play_dice_game(user_id):
    user_dice = random.randint(1,6)
    bot_dice = random.randint(1,6)
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
    win_amount = 2.0 if any("هدف" in s for s in result) else 0.5
    return result, win_amount

def play_basketball_game(user_id):
    shots = []
    goals = 0
    for i in range(3):
        if random.random() > 0.3:
            shots.append("🎯 تسجيل ✅")
            goals += 1
        else:
            shots.append("🎯 أخطأت ❌")
    win_amount = goals * 1.0
    return shots, win_amount

def play_darts_game(user_id):
    scores = []
    total_score = 0
    for i in range(3):
        score = random.randint(10,50)
        scores.append(f"🎯 نقاط: {score}")
        total_score += score
    win_amount = total_score / 50.0
    return scores, win_amount

# -------------------------
# Callback handling (preserve logic, add lang & data save)
# -------------------------
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    if user.get("banned"):
        bot.answer_callback_query(call.id, "❌ محظور", show_alert=True)
        return
    lang = user.get("lang","ar")
    data_changed = False

    try:
        if call.data == "main_menu":
            txt = (f"🎮 أهلاً {call.from_user.first_name}!\n\n"
                   f"💰 رصيدك: {user['balance']:.2f} USDT\n👥 إحالات: {user['referrals_count']}\n"
                   f"🎯 المحاولات: {3 - user['games_played_today']}/3\n💎 VIP: {user['vip_level']}")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=txt, reply_markup=create_main_menu(lang))
        elif call.data == "games_menu":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="🎮 اختر لعبة:", reply_markup=create_games_menu(lang))
        elif call.data == "profile":
            txt = (f"📊 الملف الشخصي:\n\n👤 {call.from_user.first_name}\n🆔 {user_id}\n"
                   f"💰 رصيد: {user['balance']:.2f} USDT\n👥 إحالات: {user['referrals_count']}\n"
                   f"🎯 محاولات متبقية: {3-user['games_played_today']}\n💎 VIP: {user['vip_level']}")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=txt, reply_markup=create_main_menu(lang))
        elif call.data == "referral":
            kb, link = create_referral_keyboard(user_id, lang)
            txt = f"👥 نظام الإحالات:\n\n🔗 رابطك: {link}\n📊 لديك {user['referrals_count']} إحالة"
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=txt, reply_markup=kb)
        elif call.data == "vip_packages":
            txt = "💎 باقات VIP:\n\n🟢 برونزي - 5 USDT\n🔵 فضى - 10 USDT\n🟡 ذهبي - 20 USDT"
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=txt, reply_markup=create_vip_keyboard(lang))
        elif call.data == "withdraw":
            txt = (f"💰 سحب رصيد:\n\n💳 الحد الأدنى: 10 USDT\n📡 الشبكة: BEP20\n💰 رصيدك: {user['balance']:.2f} USDT\n\n"
                   f"العنوان للمراجعة: {WALLET_ADDRESS}")
            if user['balance'] >= 10:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text=txt + "\n\n✅ يمكنك السحب الآن", reply_markup=create_withdraw_keyboard(lang))
            else:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text=txt + f"\n\n❌ تحتاج {10 - user['balance']:.2f} USDT أخرى", reply_markup=create_main_menu(lang))
        elif call.data.startswith("game_"):
            if user['games_played_today'] >= 3:
                bot.answer_callback_query(call.id, "❌ انتهت المحاولات اليوم!", show_alert=True)
                return
            user['games_played_today'] += 1
            user['total_games_played'] += 1
            user['games_counter'] += 1
            data_changed = True
            game_type = call.data.replace("game_", "")
            if game_type == "slots":
                result, win_amount = play_slots_game(user_id)
                game_result = f"🎰 {' '.join(result)}"
            elif game_type == "dice":
                ud, bd, res, win_amount = play_dice_game(user_id)
                game_result = f"🎲 أنت {ud} vs البوت {bd} - {res}"
            elif game_type == "football":
                resu, win_amount = play_football_game(user_id)
                game_result = "⚽ " + " | ".join(resu)
            elif game_type == "basketball":
                resu, win_amount = play_basketball_game(user_id)
                game_result = "🏀 " + " | ".join(resu)
            elif game_type == "darts":
                resu, win_amount = play_darts_game(user_id)
                game_result = "🎯 " + " | ".join(resu)
            else:
                win_amount = 0
                game_result = f"🎮 {game_type}"

            if win_amount > 0:
                add_balance(user_id, win_amount, f"ربح لعبة {game_type}")
                win_text = f"🎉 ربحت {win_amount} USDT!"
            else:
                win_text = "😔 لم تربح هذه المرة"

            if user['games_counter'] >= 3:
                add_balance(user_id, 5.0, "مكافأة كل 3 محاولات")
                user['games_counter'] = 0
                bonus_text = "\n🏆 مبروك! حصلت على مكافأة 5.0 USDT!"
                data_changed = True
            else:
                bonus_text = ""

            remaining = 3 - user['games_played_today']
            result_text = f"{game_result}\n\n{win_text}{bonus_text}\n\n🎯 المحاولات المتبقية: {remaining}/3\n💰 الرصيد: {user['balance']:.2f} USDT"
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=result_text, reply_markup=create_games_menu(lang))
        elif call.data in ["buy_bronze", "buy_silver", "buy_gold"]:
            vip_map = {"buy_bronze": (1,5.0), "buy_silver": (2,10.0), "buy_gold": (3,20.0)}
            lvl, price = vip_map[call.data]
            if user['balance'] >= price:
                user['balance'] = round(user['balance'] - price, 8)
                user['vip_level'] = lvl
                user['vip_expiry'] = (datetime.now() + timedelta(days=30)).isoformat()
                data_changed = True
                bot.answer_callback_query(call.id, "✅ تم شراء باقة VIP", show_alert=True)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text=f"✅ تم تفعيل باقة VIP!\n💰 رصيدك المتبقي: {user['balance']:.2f} USDT", reply_markup=create_main_menu(lang))
            else:
                bot.answer_callback_query(call.id, "❌ رصيدك غير كافٍ", show_alert=True)
        elif call.data == "confirm_bep20":
            if user['balance'] >= 10:
                user['withdrawal_attempts'] += 1
                data_changed = True
                bot.answer_callback_query(call.id, "✅ تم استلام طلب السحب", show_alert=True)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text=f"✅ تم استلام طلب سحب {user['balance']:.2f} USDT\n📧 سيتم التواصل خلال 24 ساعة", reply_markup=create_main_menu(lang))
            else:
                bot.answer_callback_query(call.id, "❌ الرصيد غير كافٍ", show_alert=True)
        elif call.data == "copy_link":
            bot.answer_callback_query(call.id, "✅ تم نسخ رابط الإحالة", show_alert=True)
        elif call.data == "my_referrals":
            bot.answer_callback_query(call.id, f"📊 لديك {user['referrals_count']} إحالة", show_alert=True)
        elif call.data == "lang_toggle":
            user['lang'] = "en" if user.get("lang","ar") == "ar" else "ar"
            data_changed = True
            bot.answer_callback_query(call.id, "🌐 تم تبديل اللغة", show_alert=True)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="✅ تم تبديل اللغة", reply_markup=create_main_menu(user['lang']))
        else:
            bot.answer_callback_query(call.id, "✅", show_alert=False)
    except Exception as e:
        print(f"callback error: {e}")
    finally:
        if data_changed:
            save_data()

# -------------------------
# Message handlers / commands
# -------------------------
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if user.get("banned"):
        bot.send_message(message.chat.id, "❌ حسابك محظور.")
        return
    ref_bonus = 0.0
    # check referral code in /start <ref>
    parts = message.text.split()
    if len(parts) > 1:
        try:
            ref = int(parts[1])
            if ref != user_id and add_referral(ref, user_id):
                ref_bonus = 1.0
        except:
            pass
    # update names
    if not user.get("first_name"):
        user["first_name"] = message.from_user.first_name or ""
    if not user.get("username"):
        user["username"] = message.from_user.username or ""
    if ref_bonus > 0:
        user["balance"] = round(user.get("balance",0.0) + ref_bonus, 8)
    save_user(user)
    lang = user.get("lang","ar")
    if lang == "ar":
        txt = f"🎮 أهلاً {message.from_user.first_name}!\n🎯 لديك 3 محاولات مجانية\n💰 مكافأة الإحالة: 1.0 USDT\n🏆 اربح 5 USDT كل 3 محاولات!"
    else:
        txt = f"🎮 Welcome {message.from_user.first_name}!\n🎯 You have 3 free tries\n💰 Referral bonus: 1.0 USDT\n🏆 Win 5 USDT every 3 tries!"
    bot.send_message(message.chat.id, txt, reply_markup=create_main_menu(lang))

@bot.message_handler(commands=['test'])
def cmd_test(message):
    bot.reply_to(message, "✅ البوت يعمل")

@bot.message_handler(commands=['myid'])
def cmd_myid(message):
    bot.reply_to(message, f"🆔 {message.from_user.id}")

# -------------------------
# Admin utilities
# -------------------------
def is_admin(uid):
    return int(uid) == int(ADMIN_ID)

@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "📝 استخدم: /broadcast نص الرسالة")
        return
    text = parts[1]
    sent = 0
    with lock:
        for uid in list(data["users"].keys()):
            try:
                u = data["users"][uid]
                if u.get("banned"):
                    continue
                bot.send_message(int(uid), text)
                sent += 1
            except:
                pass
    bot.reply_to(message, f"📤 تم الإرسال لـ {sent} مستخدم")

@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية")
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "❌ استخدم: /ban user_id")
        return
    uid = parts[1]
    with lock:
        u = data["users"].get(str(uid))
        if u:
            u["banned"] = True
            save_data()
            bot.reply_to(message, f"✅ تم حظر {uid}")
        else:
            bot.reply_to(message, "❌ المستخدم غير موجود")

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية")
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "❌ استخدم: /unban user_id")
        return
    uid = parts[1]
    with lock:
        u = data["users"].get(str(uid))
        if u:
            u["banned"] = False
            save_data()
            bot.reply_to(message, f"✅ تم فك الحظر عن {uid}")
        else:
            bot.reply_to(message, "❌ المستخدم غير موجود")

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية")
        return
    with lock:
        total_users = len(data["users"])
        total_referrals = len(data["referrals"])
        total_balance = sum(u.get("balance",0.0) for u in data["users"].values())
    bot.reply_to(message, f"📊 إحصائيات:\n• المستخدمين: {total_users}\n• الإحالات: {total_referrals}\n• مجموع الأرصدة: {total_balance:.2f} USDT")

@bot.message_handler(commands=['userinfo'])
def cmd_userinfo(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية")
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "❌ استخدم: /userinfo user_id")
        return
    uid = parts[1]
    u = data["users"].get(str(uid))
    if not u:
        bot.reply_to(message, "❌ المستخدم غير موجود")
        return
    txt = json.dumps(u, ensure_ascii=False, indent=2)
    bot.reply_to(message, f"📋 بيانات المستخدم:\n<pre>{txt}</pre>")

@bot.message_handler(commands=['setbalance'])
def cmd_setbalance(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية")
        return
    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "❌ استخدم: /setbalance user_id amount")
        return
    uid, amt = parts[1], float(parts[2])
    with lock:
        u = data["users"].get(str(uid))
        if not u:
            bot.reply_to(message, "❌ المستخدم غير موجود")
            return
        old = u.get("balance",0.0)
        u["balance"] = round(float(amt),8)
        save_data()
    bot.reply_to(message, f"✅ تم تعديل الرصيد من {old:.2f} → {amt:.2f} USDT")

@bot.message_handler(commands=['adduser'])
def cmd_adduser(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية")
        return
    parts = message.text.split()
    # /adduser user_id balance [referrals] [vip_level]
    if len(parts) < 3:
        bot.reply_to(message, "📝 استخدم: /adduser user_id balance [referrals] [vip_level]")
        return
    uid = parts[1]
    balance = float(parts[2])
    referrals = int(parts[3]) if len(parts) > 3 else 0
    vip = int(parts[4]) if len(parts) > 4 else 0
    with lock:
        data["users"][str(uid)] = {
            "user_id": int(uid),
            "username": "",
            "first_name": "مستخدم",
            "last_name": "",
            "balance": round(balance,8),
            "referrals_count": referrals,
            "referrer_id": None,
            "vip_level": vip,
            "vip_expiry": None,
            "games_played_today": 0,
            "total_games_played": 0,
            "total_earned": 0.0,
            "total_deposits": balance,
            "games_counter": 0,
            "last_daily_bonus": None,
            "withdrawal_attempts": 0,
            "new_referrals_count": 0,
            "lang": "ar",
            "banned": False,
            "registration_date": datetime.now().isoformat()
        }
        save_data()
    bot.reply_to(message, f"✅ تم إضافة/تحديث المستخدم {uid}")

@bot.message_handler(commands=['exportdata'])
def cmd_exportdata(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية")
        return
    try:
        save_data()
        with open(DATA_FILE, "rb") as f:
            bot.send_document(message.from_user.id, f, caption=f"Backup at {datetime.now().isoformat()}")
        bot.reply_to(message, "✅ تم إرسال النسخة الاحتياطية إليك")
    except Exception as e:
        bot.reply_to(message, f"❌ فشل إرسال النسخة: {e}")

@bot.message_handler(commands=['importdata'])
def cmd_importdata(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية")
        return
    if message.reply_to_message and message.reply_to_message.document:
        try:
            file_info = bot.get_file(message.reply_to_message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            with open(DATA_FILE, "wb") as f:
                f.write(downloaded)
            load_data()
            bot.reply_to(message, "✅ تم استيراد البيانات بنجاح")
        except Exception as e:
            bot.reply_to(message, f"❌ فشل الاستيراد: {e}")
    else:
        bot.reply_to(message, "📝 رد على ملف JSON ثم استخدم /importdata")

@bot.message_handler(commands=['backupnow'])
def cmd_backupnow(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية")
        return
    try:
        save_data()
        with lock:
            bk = {"timestamp": datetime.now().isoformat(), "users_count": len(data["users"])}
            data["backups"].append(bk)
            save_data()
        with open(DATA_FILE, "rb") as f:
            bot.send_document(message.from_user.id, f, caption="Manual backup")
        bot.reply_to(message, "✅ Backup created and sent")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# catch-all simple reply handler
@bot.message_handler(func=lambda m: True)
def echo_all(message):
    if message.from_user and str(message.from_user.id) in data["users"] and data["users"][str(message.from_user.id)].get("banned"):
        bot.reply_to(message, "❌ محظور")
        return
    bot.reply_to(message, f"📝 تم الاستلام: {message.text}")

# -------------------------
# Flask routes (webhook + health)
# -------------------------
@app.route('/')
def index_page():
    return "🤖 البوت شغال — استخدم /start في التليجرام."

@app.route('/health')
def health():
    return {"status": "healthy", "users": len(data["users"]), "timestamp": datetime.now().isoformat()}

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook_endpoint():
    if request.headers.get('content-type') == 'application/json':
        try:
            update = telebot.types.Update.de_json(request.data.decode('utf-8'))
            bot.process_new_updates([update])
            return "OK", 200
        except Exception as e:
            print(f"Webhook processing error: {e}")
            return "Error", 500
    return "Forbidden", 403

# set webhook when app is ready
@app.before_first_request
def setup_webhook():
    try:
        bot.remove_webhook()
        time.sleep(1)
        webhook_url = f"https://usdt-bot-live.onrender.com/{BOT_TOKEN}"
        bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook set to: {webhook_url}")
    except Exception as e:
        print(f"❌ Failed to set webhook: {e}")

# -------------------------
# STARTUP
# -------------------------
load_data()
# start autosave thread
t = threading.Thread(target=autosave_worker, daemon=True)
t.start()

# gunicorn will use `app` WSGI object in production
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting local Flask on port {port}")
    app.run(host="0.0.0.0", port=port)
