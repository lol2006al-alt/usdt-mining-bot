from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os, json, time, tempfile, threading, random, requests
from datetime import datetime, timedelta

# ---------------- CONFIG ----------------
BOT_TOKEN = "7973697789:AAFXfYXTgYaTAF1j7IGhp2kiv-kxrN1uImk"
ADMIN_ID = 8400225549
SUPPORT_USERNAME = "Trust_wallet_Support_4"
DATA_FILE = "database.json"
AUTOSAVE_INTERVAL = 60
WEBHOOK_BASE = "https://usdt-bot-live.onrender.com"

MIN_WITHDRAW_BALANCE = 100.0
MIN_WITHDRAW_REFERRALS = 15
MIN_DEPOSIT_FOR_WITHDRAW = 10.0
ALT_REFERRAL_GOAL = 10
DAILY_TRIES = 3
REFERRAL_BONUS_AMOUNT = 0.75
REFERRAL_BONUS_TRY = 1
# -------------------------------------------------

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# in-memory mirror
data = {
    "users": {},
    "referrals": [],
    "backups": [],
    "transactions": []
}
_lock = threading.Lock()

# ---------- atomic write helpers ----------
def atomic_write(path, content):
    fd, tmp = tempfile.mkstemp(dir=".", prefix=".tmpdb_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise

def load_data():
    global data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
                    print(f"✅ Loaded {DATA_FILE}")
        except Exception as e:
            print("❌ load_data error:", e)
    else:
        save_data()

def save_data():
    with _lock:
        try:
            atomic_write(DATA_FILE, json.dumps(data, ensure_ascii=False, indent=2))
            print(f"✅ Saved {DATA_FILE} at {datetime.utcnow().isoformat()}")
            return True
        except Exception as e:
            print("❌ save_data error:", e)
            return False

def autosave_loop():
    while True:
        time.sleep(AUTOSAVE_INTERVAL)
        save_data()

# ---------- users helpers ----------
def ensure_user(uid):
    uid = str(uid)
    with _lock:
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
                "daily_trie_quota": 0,
                "total_games_played": 0,
                "total_earned": 0.0,
                "total_deposits": 0.0,
                "games_counter": 0,
                "last_daily_reset": None,
                "withdrawal_attempts": 0,
                "new_referrals_count": 0,
                "active_days_streak": 0,
                "last_active_date": None,
                "registration_date": datetime.utcnow().date().isoformat(),
                "banned": False,
                "total_profits": 0.0
            }
            save_data()
        return data["users"][uid]

def save_user(user):
    with _lock:
        data["users"][str(user["user_id"])] = user
        save_data()

def add_balance(uid, amount, desc=""):
    u = ensure_user(uid)
    u["balance"] = round(u.get("balance", 0.0) + float(amount), 8)
    u["total_earned"] = round(u.get("total_earned", 0.0) + max(0.0,float(amount)), 8)
    if float(amount) != 0:
        with _lock:
            data["transactions"].append({
                "user_id": int(uid),
                "amount": float(amount),
                "description": desc,
                "timestamp": datetime.utcnow().isoformat()
            })
            save_data()
    return u

def add_referral(referrer_id, referred_id):
    if int(referrer_id) == int(referred_id):
        return False
    with _lock:
        for r in data["referrals"]:
            if r["referrer_id"] == int(referrer_id) and r["referred_id"] == int(referred_id):
                return False
        data["referrals"].append({
            "referrer_id": int(referrer_id),
            "referred_id": int(referred_id),
            "timestamp": datetime.utcnow().isoformat()
        })
        ref = ensure_user(referrer_id)
        ref["referrals_count"] = ref.get("referrals_count", 0) + 1
        ref["daily_trie_quota"] = ref.get("daily_trie_quota", 0) + REFERRAL_BONUS_TRY
        add_balance(referrer_id, REFERRAL_BONUS_AMOUNT, f"Referral bonus for {referred_id}")
        add_balance(referred_id, 0.75, "Join referral bonus")
        ref["new_referrals_count"] = ref.get("new_referrals_count", 0) + 1
        save_data()
    return True

# ---------- daily quota & active days ----------
def ensure_daily_quota(user):
    now = datetime.utcnow()
    last = user.get("last_daily_reset")
    assign = False
    if last is None:
        assign = True
    else:
        try:
            last_dt = datetime.fromisoformat(last)
            if now - last_dt >= timedelta(hours=24):
                assign = True
        except:
            assign = True
    if assign:
        user["daily_trie_quota"] = user.get("daily_trie_quota", 0) + DAILY_TRIES
        user["games_played_today"] = 0
        user["last_daily_reset"] = now.isoformat()
        last_active = user.get("last_active_date")
        today = now.date()
        if last_active:
            try:
                last_date = datetime.fromisoformat(last_active).date()
                delta = (today - last_date).days
                if delta == 1:
                    user["active_days_streak"] = user.get("active_days_streak", 0) + 1
                elif delta == 0:
                    pass
                else:
                    user["active_days_streak"] = 1
            except:
                user["active_days_streak"] = 1
        else:
            user["active_days_streak"] = 1
        user["last_active_date"] = now.isoformat()
        save_user(user)

def user_remaining_tries(user):
    return max(0, int(user.get("daily_trie_quota", 0) - user.get("games_played_today", 0)))

# ---------- keyboards ----------
def main_menu_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📊 الملف الشخصي", callback_data="profile"),
        InlineKeyboardButton("🎮 الألعاب", callback_data="games_menu")
    )
    kb.add(
        InlineKeyboardButton("🆘 التواصل مع الدعم", url=f"https://t.me/{SUPPORT_USERNAME}"),
        InlineKeyboardButton("💎 باقات VIP", callback_data="vip_packages")
    )
    kb.add(
        InlineKeyboardButton("👥 الإحالات", callback_data="referral"),
        InlineKeyboardButton("💰 سحب رصيد", callback_data="withdraw")
    )
    return kb

def games_menu_kb():
    kb = InlineKeyboardMarkup(row_width=2)
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
    return kb

def vip_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    support_url = f"https://t.me/{SUPPORT_USERNAME}"
    kb.add(InlineKeyboardButton("🟢 برونزي - 5 USDT\n• مزايا: محاولات إضافية", url=support_url))
    kb.add(InlineKeyboardButton("🔵 فضي - 10 USDT\n• مزايا: إلغاء شرط الإيداع للسحب", url=support_url))
    kb.add(InlineKeyboardButton("🟡 ذهبي - 20 USDT\n• مزايا: مكافآت أعلى وأولوية دعم", url=support_url))
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
    return kb

def withdraw_kb(user):
    kb = InlineKeyboardMarkup(row_width=1)
    eligible = (
        user.get("balance", 0.0) >= MIN_WITHDRAW_BALANCE
        and user.get("referrals_count", 0) >= MIN_WITHDRAW_REFERRALS
        and user.get("active_days_streak", 0) >= 7
        and (user.get("total_deposits", 0.0) >= MIN_DEPOSIT_FOR_WITHDRAW or user.get("vip_level", 0) >= 2)
    )
    alt_ok = (user.get("balance", 0.0) >= MIN_WITHDRAW_BALANCE and user.get("referrals_count", 0) >= ALT_REFERRAL_GOAL)
    if eligible:
        kb.add(InlineKeyboardButton("💳 تأكيد طلب السحب", callback_data="confirm_withdraw"))
    else:
        kb.add(InlineKeyboardButton(f"⚠️ شروط السحب: {MIN_WITHDRAW_BALANCE} USDT + {MIN_WITHDRAW_REFERRALS} إحالات + 7 أيام نشط + (إيداع ≥ {MIN_DEPOSIT_FOR_WITHDRAW} أو باقة فضية)", callback_data="withdraw_info"))
        if alt_ok:
            kb.add(InlineKeyboardButton(f"🔓 خيار بديل: دعوة {ALT_REFERRAL_GOAL} شخص", callback_data="invite_10_option"))
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
    return kb

def referral_kb(user_id):
    kb = InlineKeyboardMarkup(row_width=1)
    link = f"https://t.me/Usdt_Mini1Bot?start=ref_{user_id}"
    kb.add(InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={link}&text=انضم واحصل على 0.75 USDT!"))
    kb.add(InlineKeyboardButton("🔗 نسخ الرابط", callback_data="copy_link"))
    kb.add(InlineKeyboardButton("📊 إحالاتي", callback_data="my_referrals"))
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
    return kb, link

# ---------- games ----------
def play_slots_game(user_id):
    symbols = ["🍒","🍋","🍊","🍇","🔔","💎"]
    res = [random.choice(symbols) for _ in range(3)]
    if res[0]==res[1]==res[2]:
        win = 5.0
    elif res[0]==res[1] or res[1]==res[2]:
        win = 2.0
    else:
        win = 0.0
    return res, win

def play_dice_game(user_id):
    ud = random.randint(1,6); bd = random.randint(1,6)
    if ud>bd: return ud, bd, "فوز", 3.0
    if ud<bd: return ud, bd, "خسارة", 0.0
    return ud, bd, "تعادل", 1.0

def play_football_game(user_id):
    outcomes = ["هدف 🥅","إصابة القائم 🚩","حارس يصد ⛔"]
    r = random.choices(outcomes, k=3)
    win = 2.0 if any("هدف" in s for s in r) else 0.5
    return r, win

def play_basketball_game(user_id):
    shots=[]; goals=0
    for _ in range(3):
        if random.random()>0.3: shots.append("🎯 تسجيل ✅"); goals+=1
        else: shots.append("🎯 أخطأت ❌")
    return shots, goals*1.0

def play_darts_game(user_id):
    scores=[]; total=0
    for _ in range(3):
        s=random.randint(10,50); scores.append(f"🎯 نقاط: {s}"); total+=s
    return scores, total/50.0

# ---------- helpers ----------
def next_mining_eta(user):
    last = user.get("last_daily_reset")
    if not last:
        return "جاهز خلال 24س"
    try:
        last_dt = datetime.fromisoformat(last)
        delta = timedelta(hours=24) - (datetime.utcnow() - last_dt)
        seconds = int(delta.total_seconds())
        if seconds <= 0:
            return "جاهز الآن"
        h = seconds // 3600; m = (seconds % 3600) // 60
        return f"{h}س {m}د"
    except:
        return "جاهز خلال 24س"

# ---------- callbacks ----------
@bot.callback_query_handler(func=lambda c: True)
def callbacks(c):
    uid = c.from_user.id
    user = ensure_user(uid)
    try:
        ensure_daily_quota(user)
    except Exception as e:
        print("ensure_daily_quota error:", e)
    changed = False
    try:
        if c.data == "profile" or c.data == "main_menu":
            remaining = user_remaining_tries(user)
            vip_name = {0:"عادي",1:"برونزي",2:"فضي",3:"ذهبي"}.get(user.get("vip_level",0),"عادي")
            txt = (f"📊 الملف الشخصي\n\n👤 المستخدم: {user.get('username') or ('User '+str(uid))}\n"
                   f"🆔 المعرف: {uid}\n💰 الرصيد: {user.get('balance',0.0):.2f} USDT\n"
                   f"👥 الإحالات: {user.get('referrals_count',0)} مستخدم\n"
                   f"📈 الإحالات الجديدة: {user.get('new_referrals_count',0)}/10\n"
                   f"🏆 مستوى VIP: {vip_name}\n"
                   f"🎯 المحاولات المتبقية: {remaining} (3 أساسية + {user.get('referrals_count',0)} إضافية)\n\n"
                   f"⏰ مكافأة التعدين: {next_mining_eta(user)} ⏳\n\n"
                   f"💎 إجمالي الأرباح: {user.get('total_profits',0.0):.2f} USDT\n"
                   f"💳 إجمالي الإيداعات: {user.get('total_deposits',0.0):.2f} USDT\n"
                   f"📅 النشاط المستمر: {user.get('active_days_streak',0)}/7 أيام")
            bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id, text=txt, reply_markup=main_menu_kb())

        elif c.data == "games_menu":
            bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id, text="🎮 اختر لعبة:", reply_markup=games_menu_kb())

        elif c.data == "vip_packages":
            bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id, text="💎 باقات VIP", reply_markup=vip_kb())

        elif c.data == "referral":
            kb, link = referral_kb(uid)
            bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id, text=f"👥 رابط الإحالة الخاص بك:\n{link}", reply_markup=kb)

        elif c.data == "withdraw":
            kb = withdraw_kb(user)
            bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id, text=f"💰 سحب الرصيد\n• الحد الأدنى: {MIN_WITHDRAW_BALANCE} USDT\n• إحالات مطلوبة: {MIN_WITHDRAW_REFERRALS}\n• نشاط 7 أيام متتالية\n• إما إيداع ≥ {MIN_DEPOSIT_FOR_WITHDRAW} أو باقة فضية", reply_markup=kb)

        elif c.data == "withdraw_info":
            bot.answer_callback_query(c.id, f"السحب: لازم {MIN_WITHDRAW_BALANCE} USDT + {MIN_WITHDRAW_REFERRALS} إحالة + 7 أيام نشاط + (إيداع ≥ {MIN_DEPOSIT_FOR_WITHDRAW} أو باقة فضية). بديل: دعوة {ALT_REFERRAL_GOAL} أشخاص إذا رصيدك ≥ {MIN_WITHDRAW_BALANCE}", show_alert=True)

        elif c.data == "invite_10_option":
            kb, link = referral_kb(uid)
            bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id, text=f"الخيار البديل: ادعُ {ALT_REFERRAL_GOAL} شخص عبر:\n{link}\nبمجرد وصول الإحالات إلى {ALT_REFERRAL_GOAL} سيُفتح خيار السحب.", reply_markup=kb)

        elif c.data == "confirm_withdraw":
            eligible = (
                user.get("balance",0.0) >= MIN_WITHDRAW_BALANCE
                and user.get("referrals_count",0) >= MIN_WITHDRAW_REFERRALS
                and user.get("active_days_streak",0) >= 7
                and (user.get("total_deposits",0.0) >= MIN_DEPOSIT_FOR_WITHDRAW or user.get("vip_level",0) >= 2)
            )
            alt_ok = (user.get("balance",0.0) >= MIN_WITHDRAW_BALANCE and user.get("referrals_count",0) >= ALT_REFERRAL_GOAL)
            if eligible or alt_ok:
                user["withdrawal_attempts"] = user.get("withdrawal_attempts",0) + 1
                save_user(user)
                bot.answer_callback_query(c.id, "✅ تم تقديم طلب السحب، جاري إشعار الأدمن", show_alert=True)
                try:
                    bot.send_message(ADMIN_ID, f"📥 طلب سحب جديد:\n• user_id: {uid}\n• balance: {user.get('balance'):.2f} USDT\n• referrals: {user.get('referrals_count')}\n• active_days: {user.get('active_days_streak')}\n• vip_level: {user.get('vip_level')}\n• total_deposits: {user.get('total_deposits'):.2f}")
                except Exception as e:
                    print("notify admin error:", e)
                bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id, text="✅ تم إرسال طلب السحب، سيتواصل الدعم معك", reply_markup=main_menu_kb())
            else:
                bot.answer_callback_query(c.id, "❌ لا تستوفي شروط السحب", show_alert=True)

        elif c.data.startswith("game_"):
            remaining = user_remaining_tries(user)
            if remaining <= 0:
                bot.answer_callback_query(c.id, "❌ لا توجد محاولات متبقية اليوم، اجمع إحالات أو انتظر إعادة المحاولات كل 24 ساعة", show_alert=True)
                return
            user["games_played_today"] = user.get("games_played_today",0) + 1
            user["total_games_played"] = user.get("total_games_played",0) + 1
            user["games_counter"] = user.get("games_counter",0) + 1
            changed = True
            game_type = c.data.replace("game_","")
            if game_type == "slots":
                res, win = play_slots_game(uid); result_text = f"🎰 {' '.join(res)}"
            elif game_type == "dice":
                ud, bd, resu, win = play_dice_game(uid); result_text = f"🎲 أنت {ud} vs البوت {bd} - {resu}"
            elif game_type == "football":
                resu, win = play_football_game(uid); result_text = "⚽ " + " | ".join(resu)
            elif game_type == "basketball":
                resu, win = play_basketball_game(uid); result_text = "🏀 " + " | ".join(resu)
            elif game_type == "darts":
                resu, win = play_darts_game(uid); result_text = "🎯 " + " | ".join(resu)
            else:
                win = 0; result_text = f"🎮 {game_type}"

            if win > 0:
                add_balance(uid, win, f"Game win {game_type}")
                win_text = f"\n🎉 ربحت {win} USDT!"
            else:
                win_text = "\n😔 لم تربح هذه المرة"

            if user.get("games_counter",0) >= 3:
                add_balance(uid, 5.0, "Bonus every 3 plays")
                user["games_counter"] = 0
                win_text += "\n🏆 مبروك! حصلت على مكافأة 5.0 USDT!"
                changed = True

            remaining_after = user_remaining_tries(user)
            bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id,
                                  text=f"{result_text}\n{win_text}\n\n🎯 المحاولات المتبقية: {remaining_after}\n💰 رصيد: {user.get('balance',0.0):.2f} USDT",
                                  reply_markup=games_menu_kb())

        elif c.data == "copy_link":
            bot.answer_callback_query(c.id, "✅ استخدم زر المشاركة لنسخ الرابط", show_alert=True)

        elif c.data == "my_referrals":
            bot.answer_callback_query(c.id, f"📊 لديك {user.get('referrals_count',0)} إحالات", show_alert=True)

        else:
            bot.answer_callback_query(c.id, "✅", show_alert=False)

    except Exception as e:
        print("callback error:", e)
    finally:
        if changed:
            save_user(user)

# ---------- message handlers ----------
@bot.message_handler(commands=['start'])
def cmd_start(m):
    uid = m.from_user.id
    parts = m.text.split()
    ref_bonus = 0
    if len(parts) > 1:
        try:
            ref_param = parts[1]
            if ref_param.startswith("ref_"):
                ref = int(ref_param.replace("ref_", ""))
                if ref != uid and add_referral(ref, uid):
                    ref_bonus = 0.75
        except Exception as e:
            print("Referral error:", e)
    user = ensure_user(uid)
    if not user.get("username"):
        user["username"] = m.from_user.username or ""
    if ref_bonus:
        add_balance(uid, ref_bonus, "Referral join bonus")
    ensure_daily_quota(user)
    save_user(user)
    bot.send_message(m.chat.id, f"🎮 أهلاً {m.from_user.first_name}!\nاستخدم الأزرار لبدء اللعب.", reply_markup=main_menu_kb())

@bot.message_handler(commands=['test'])
def cmd_test(m):
    bot.reply_to(m, "✅ البوت يعمل")

@bot.message_handler(commands=['myid'])
def cmd_myid(m):
    bot.reply_to(m, f"🆔 {m.from_user.id}")

# ---------- Admin commands (Arabic) ----------
def is_admin(uid):
    return int(uid) == int(ADMIN_ID)

@bot.message_handler(commands=['رصيد'])
def cmd_رصيد(m):
    if not is_admin(m.from_user.id): return bot.reply_to(m, "❌ ليس لديك صلاحية")
    parts = m.text.split()
    if len(parts) != 3: return bot.reply_to(m, "❌ استخدم: /رصيد user_id amount")
    uid, amt = parts[1], float(parts[2])
    u = ensure_user(uid)
    old = u.get("balance",0.0); u["balance"]=round(float(amt),8); save_user(u)
    bot.reply_to(m, f"✅ تم تعديل الرصيد من {old:.2f} → {amt:.2f} USDT")

@bot.message_handler(commands=['باقة'])
def cmd_باقة(m):
    if not is_admin(m.from_user.id): return bot.reply_to(m, "❌ ليس لديك صلاحية")
    parts = m.text.split()
    if len(parts) < 3: return bot.reply_to(m, "❌ استخدم: /باقة user_id level [days]\nlevels: 0=عادي 1=برونزي 2=فضي 3=ذهبي")
    uid=int(parts[1]); level=int(parts[2]); days=int(parts[3]) if len(parts)>3 else 30
    u=ensure_user(uid); u["vip_level"]=level; u["vip_expiry"]=(datetime.utcnow()+timedelta(days=days)).isoformat(); save_user(u)
    bot.reply_to(m, f"✅ تم تعيين باقة VIP مستوى {level} للمستخدم {uid}")

@bot.message_handler(commands=['احالات'])
def cmd_احالات(m):
    if not is_admin(m.from_user.id): return bot.reply_to(m, "❌ ليس لديك صلاحية")
    parts = m.text.split()
    if len(parts)!=3: return bot.reply_to(m, "❌ استخدم: /احالات user_id count")
    uid, cnt = parts[1], int(parts[2]); u=ensure_user(uid); u["referrals_count"]=cnt; save_user(u)
    bot.reply_to(m, f"✅ تم ضبط الإحالات لـ {uid} إلى {cnt}")

@bot.message_handler(commands=['محاولات'])
def cmd_محاولات(m):
    if not is_admin(m.from_user.id): return bot.reply_to(m, "❌ ليس لديك صلاحية")
    parts = m.text.split()
    if len(parts)!=3: return bot.reply_to(m, "❌ استخدم: /محاولات user_id count")
    uid, cnt = parts[1], int(parts[2]); u=ensure_user(uid); u["games_played_today"]=cnt; save_user(u)
    bot.reply_to(m, f"✅ تم ضبط محاولات اليوم للمستخدم {uid} إلى {cnt}")

@bot.message_handler(commands=['مستخدم'])
def cmd_مستخدم(m):
    if not is_admin(m.from_user.id): return bot.reply_to(m, "❌ ليس لديك صلاحية")
    parts = m.text.split()
    if len(parts)!=2: return bot.reply_to(m, "❌ استخدم: /مستخدم user_id")
    uid=parts[1]; u=data["users"].get(str(uid))
    if not u: return bot.reply_to(m, "❌ المستخدم غير موجود")
    bot.reply_to(m, f"📋 بيانات المستخدم:\n<pre>{json.dumps(u, ensure_ascii=False, indent=2)}</pre>")

@bot.message_handler(commands=['تصدير'])
def cmd_تصدير(m):
    if not is_admin(m.from_user.id): return bot.reply_to(m, "❌ ليس لديك صلاحية")
    try:
        save_data()
        with open(DATA_FILE, "rb") as f:
            bot.send_document(m.from_user.id, f, caption=f"Backup {datetime.utcnow().isoformat()}")
        bot.reply_to(m, "✅ تم إرسال النسخة الاحتياطية")
    except Exception as e:
        bot.reply_to(m, f"❌ فشل: {e}")

@bot.message_handler(commands=['استيراد'])
def cmd_استيراد(m):
    if not is_admin(m.from_user.id): return bot.reply_to(m, "❌ ليس لديك صلاحية")
    if m.reply_to_message and m.reply_to_message.document:
        try:
            file_info = bot.get_file(m.reply_to_message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            with open(DATA_FILE, "wb") as f:
                f.write(downloaded)
            load_data()
            bot.reply_to(m, "✅ تم استيراد البيانات")
        except Exception as e:
            bot.reply_to(m, f"❌ فشل الاستيراد: {e}")
    else:
        bot.reply_to(m, "📝 رد على ملف JSON ثم استخدم /استيراد")

@bot.message_handler(commands=['نسخاحتياطي'])
def cmd_نسخاحتياطي(m):
    if not is_admin(m.from_user.id): return bot.reply_to(m, "❌ ليس لديك صلاحية")
    try:
        save_data()
        with _lock:
            bk = {"timestamp": datetime.utcnow().isoformat(), "users_count": len(data["users"])}
            data["backups"].append(bk); save_data()
        with open(DATA_FILE, "rb") as f:
            bot.send_document(m.from_user.id, f, caption="Manual backup")
        bot.reply_to(m, "✅ تم إنشاء النسخة وإرسالها")
    except Exception as e:
        bot.reply_to(m, f"❌ Error: {e}")

@bot.message_handler(commands=['حظر'])
def cmd_حظر(m):
    if not is_admin(m.from_user.id): return bot.reply_to(m, "❌ ليس لديك صلاحية")
    parts=m.text.split()
    if len(parts)!=2: return bot.reply_to(m, "❌ استخدم: /حظر user_id")
    uid=parts[1]; u=data["users"].get(str(uid))
    if not u: return bot.reply_to(m, "❌ المستخدم غير موجود")
    u["banned"]=True; save_data(); bot.reply_to(m, f"✅ تم حظر {uid}")

@bot.message_handler(commands=['الغاءحظر'])
def cmd_الغاءحظر(m):
    if not is_admin(m.from_user.id): return bot.reply_to(m, "❌ ليس لديك صلاحية")
    parts=m.text.split()
    if len(parts)!=2: return bot.reply_to(m, "❌ استخدم: /الغاءحظر user_id")
    uid=parts[1]; u=data["users"].get(str(uid))
    if not u: return bot.reply_to(m, "❌ المستخدم غير موجود")
    u["banned"]=False; save_data(); bot.reply_to(m, f"✅ تم فك الحظر عن {uid}")

@bot.message_handler(commands=['بث'])
def cmd_بث(m):
    if not is_admin(m.from_user.id): return bot.reply_to(m, "❌ ليس لديك صلاحية")
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2: return bot.reply_to(m, "📝 استخدم: /بث نص الرسالة")
    text = parts[1]; sent = 0
    with _lock:
        for uid,u in data["users"].items():
            if u.get("banned"): continue
            try:
                bot.send_message(int(uid), text)
                sent += 1
            except: pass
    bot.reply_to(m, f"📤 تم الإرسال لـ {sent} مستخدم")

# fallback
@bot.message_handler(func=lambda m: True)
def catch_all(m):
    u = ensure_user(m.from_user.id)
    if u.get("banned"):
        bot.reply_to(m, "❌ محظور"); return
    bot.reply_to(m, "📝 استلمت: " + (m.text or ""))

# ---------- Flask webhook endpoints ----------
@app.route("/")
def index():
    return "Bot is running", 200

# ⚠️ المسار الجديد البسيط
@app.route("/webhook", methods=["POST"])
def webhook_endpoint():
    print(f"🔔 Webhook received at {datetime.utcnow()}")
    
    if request.headers.get("content-type") == "application/json":
        try:
            json_data = request.get_data().decode("utf-8")
            print(f"📨 Raw data received")
            
            update = telebot.types.Update.de_json(json_data)
            bot.process_new_updates([update])
            print("✅ Update processed successfully")
            return "OK", 200
        except Exception as e:
            print(f"❌ Webhook processing error: {e}")
            return "Error", 500
    return "Forbidden", 403

# ⚠️ إعداد Webhook جديد
webhook_is_set = False

@app.before_request
def before_first_request():
    global webhook_is_set
    if not webhook_is_set:
        try:
            bot.remove_webhook()
            time.sleep(2)
            # ⚠️ مسار بسيط بدون التوكن
            webhook_url = f"{WEBHOOK_BASE}/webhook"
            bot.set_webhook(url=webhook_url)
            print(f"✅ Webhook set to: {webhook_url}")
            webhook_is_set = True
        except Exception as e:
            print(f"❌ Webhook setup error: {e}")

# ---------- startup ----------
if __name__ == "__main__":
    load_data()
    t = threading.Thread(target=autosave_loop, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Starting on port {port}")
    app.run(host="0.0.0.0", port=port)
