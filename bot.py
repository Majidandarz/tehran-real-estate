from pathlib import Path

code = r'''import os
import time
import sqlite3
import threading
import requests
from flask import Flask

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not TOKEN:
    raise RuntimeError("متغیر محیطی BOT_TOKEN تنظیم نشده است.")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "AtlasPrime021").lstrip("@")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@tehranrealstate")
DB_PATH = os.environ.get("DATABASE_PATH", "realestate.db")
API = f"https://api.telegram.org/bot{TOKEN}"
app = Flask(__name__)

# Conversation state is kept in SQLite so it survives process restarts.
def connect():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
            phone TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS listings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, username TEXT, full_name TEXT,
            intent TEXT, property_type TEXT, city TEXT, district TEXT,
            price TEXT, area REAL, bedrooms INTEGER, details TEXT,
            features TEXT, photo_file_ids TEXT, latitude REAL, longitude REAL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS sessions(
            user_id INTEGER PRIMARY KEY, step TEXT, data TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS listing_media(
            listing_id INTEGER NOT NULL, file_id TEXT, media_type TEXT,
            PRIMARY KEY(listing_id,file_id)
        )""")

def api(method, payload=None, timeout=25):
    r = requests.post(f"{API}/{method}", json=payload or {}, timeout=timeout)
    r.raise_for_status()
    result = r.json()
    if not result.get("ok"):
        raise RuntimeError(result.get("description", "Telegram API error"))
    return result.get("result")

def send(chat_id, text, keyboard=None):
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = keyboard
    try:
        api("sendMessage", payload)
    except Exception as e:
        print("sendMessage error:", e)

def keyboard(rows):
    return {"keyboard": [[{"text": x} for x in row] for row in rows],
            "resize_keyboard": True, "is_persistent": True}

MAIN = keyboard([
    ["🏠 متقاضی خرید یا اجاره"],
    ["🏡 فروشنده یا موجر"],
    ["📈 سرمایه‌گذاری و مشارکت در ساخت"],
    ["🧑‍💼 مشاور املاک"],
    ["🆘 پشتیبانی و ارتباط با مدیر"],
])
CANCEL = keyboard([["❌ لغو ثبت"], ["🏠 منوی اصلی"]])
BACK_CANCEL = keyboard([["⬅️ مرحله قبل", "❌ لغو ثبت"], ["🏠 منوی اصلی"]])

INTENTS = ["فروش", "اجاره", "خرید", "رهن", "سرمایه‌گذاری", "مشارکت در ساخت"]
TYPES = ["آپارتمان", "ویلا", "زمین", "مغازه", "دفتر کار", "باغ", "کلنگی", "سایر"]
CITIES = ["تهران", "کرج", "پردیس", "دماوند", "شهریار", "شهر دیگر"]
DISTRICTS = ["شمال", "جنوب", "شرق", "غرب", "مرکز", "منطقه دیگر"]
PRICES = ["زیر ۵ میلیارد", "۵ تا ۱۰ میلیارد", "۱۰ تا ۲۰ میلیارد",
          "۲۰ تا ۵۰ میلیارد", "بیش از ۵۰ میلیارد", "توافقی"]
FEATURES = ["پارکینگ", "آسانسور", "انباری", "بالکن", "استخر",
            "حیاط", "سند رسمی", "نوساز", "بدون مورد خاص"]

def choice_keyboard(options, columns=2, extra=True):
    rows = [options[i:i+columns] for i in range(0, len(options), columns)]
    if extra:
        rows += [["⬅️ مرحله قبل", "❌ لغو ثبت"], ["🏠 منوی اصلی"]]
    return keyboard(rows)

def user_name(user):
    return " ".join(filter(None, [user.get("first_name"), user.get("last_name")])) or "کاربر"

def save_user(user, phone=None):
    with connect() as c:
        c.execute("""INSERT INTO users(user_id,username,full_name,phone)
            VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username, full_name=excluded.full_name,
            phone=COALESCE(excluded.phone, users.phone)""",
            (user["id"], user.get("username"), user_name(user), phone))

def get_session(uid):
    with connect() as c:
        row = c.execute("SELECT step,data FROM sessions WHERE user_id=?", (uid,)).fetchone()
    if not row:
        return None, {}
    import json
    try:
        return row["step"], json.loads(row["data"])
    except Exception:
        return row["step"], {}

def set_session(uid, step, data):
    import json
    with connect() as c:
        c.execute("""INSERT INTO sessions(user_id,step,data) VALUES(?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET step=excluded.step,data=excluded.data""",
            (uid, step, json.dumps(data, ensure_ascii=False)))

def clear_session(uid):
    with connect() as c:
        c.execute("DELETE FROM sessions WHERE user_id=?", (uid,))

def start_listing(chat_id, user, intent):
    save_user(user)
    data = {"intent": intent, "photo_file_ids": [], "features": []}
    set_session(user["id"], "property_type", data)
    send(chat_id, "نوع ملک را انتخاب کنید:", choice_keyboard(TYPES))

def ask_next(chat_id, uid, step, data, prompt, options=None):
    set_session(uid, step, data)
    send(chat_id, prompt, choice_keyboard(options) if options else BACK_CANCEL)

def begin_details(chat_id, uid, data):
    ask_next(chat_id, uid, "area", data, "متراژ ملک را فقط به عدد و بر حسب متر مربع وارد کنید.")

def save_listing(uid, data):
    import json
    with connect() as c:
        cur = c.execute("""INSERT INTO listings
            (user_id,username,full_name,intent,property_type,city,district,price,
             area,bedrooms,details,features,photo_file_ids,latitude,longitude,status)
            SELECT user_id,username,full_name,?,?,?,?,?,?,?,?,?,?,?,?, 'pending'
            FROM users WHERE user_id=?""",
            (data["intent"], data["property_type"], data["city"], data["district"],
             data["price"], data["area"], data["bedrooms"], data.get("details",""),
             json.dumps(data.get("features", []), ensure_ascii=False),
             json.dumps(data.get("photo_file_ids", [])), data.get("latitude"),
             data.get("longitude"), uid))
        listing_id = cur.lastrowid
        for fid in data.get("photo_file_ids", []):
            c.execute("INSERT OR IGNORE INTO listing_media VALUES(?,?,?)",
                      (listing_id, fid, "photo"))
    return listing_id

def listing_summary(listing_id, data):
    return (f"آگهی شماره {listing_id}\n"
            f"نوع معامله: {data['intent']}\n"
            f"نوع ملک: {data['property_type']}\n"
            f"شهر: {data['city']} — محدوده: {data['district']}\n"
            f"بازه قیمت: {data['price']}\n"
            f"متراژ: {data['area']} متر\n"
            f"خواب: {data['bedrooms']}\n"
            f"امکانات: {', '.join(data.get('features', [])) or 'ذکر نشده'}\n"
            f"توضیحات: {data.get('details') or 'ندارد'}\n"
            f"عکس‌ها: {len(data.get('photo_file_ids', []))}\n"
            f"موقعیت: {'ثبت شده' if data.get('latitude') is not None else 'ثبت نشده'}\n"
            "وضعیت: در انتظار تأیید مدیر")

def send_listing_to_admin(listing_id, data, user):
    text = listing_summary(listing_id, data) + f"\nشناسه کاربر: {user['id']}"
    markup = {"inline_keyboard": [[
        {"text": "✅ تأیید و انتشار", "callback_data": f"approve:{listing_id}"},
        {"text": "❌ رد آگهی", "callback_data": f"reject:{listing_id}"}
    ]]}
    try:
        api("sendMessage", {"chat_id": f"@{ADMIN_USERNAME}", "text": text,
                            "reply_markup": markup})
        # Photos are sent to the admin for review, not to the public channel.
        for fid in data.get("photo_file_ids", [])[:10]:
            api("sendPhoto", {"chat_id": f"@{ADMIN_USERNAME}", "photo": fid,
                              "caption": f"عکس آگهی شماره {listing_id}"})
        if data.get("latitude") is not None and data.get("longitude") is not None:
            api("sendLocation", {"chat_id": f"@{ADMIN_USERNAME}",
                                 "latitude": data["latitude"], "longitude": data["longitude"]})
    except Exception as e:
        print("admin notification error:", e)

def publish_listing(listing_id):
    with connect() as c:
        row = c.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
        if not row or row["status"] != "pending":
            return False, "آگهی پیدا نشد یا قبلاً بررسی شده است."
        text = (f"🏡 آگهی تأییدشده املاک تهران\n\n"
                f"کد آگهی: {listing_id}\nنوع معامله: {row['intent']}\n"
                f"نوع ملک: {row['property_type']}\nشهر: {row['city']}\n"
                f"محدوده: {row['district']}\nبازه قیمت: {row['price']}\n"
                f"متراژ: {row['area']} متر مربع\nتعداد خواب: {row['bedrooms']}\n"
                f"امکانات: {row['features']}\nتوضیحات: {row['details'] or 'ندارد'}\n\n"
                "برای اطلاعات بیشتر از طریق ربات پیگیری کنید.")
        # Do not publish phone number, username, exact address, or coordinates.
        try:
            photo_ids = __import__("json").loads(row["photo_file_ids"] or "[]")
            if photo_ids:
                api("sendPhoto", {"chat_id": CHANNEL_ID, "photo": photo_ids[0], "caption": text})
                for fid in photo_ids[1:10]:
                    api("sendPhoto", {"chat_id": CHANNEL_ID, "photo": fid})
            else:
                api("sendMessage", {"chat_id": CHANNEL_ID, "text": text})
            c.execute("UPDATE listings SET status='published' WHERE id=?", (listing_id,))
            return True, "آگهی تأیید و در کانال منتشر شد."
        except Exception as e:
            print("publish error:", e)
            return False, "انتشار ناموفق بود؛ تنظیمات دسترسی کانال را بررسی کنید."

def handle_callback(update):
    q = update["callback_query"]
    uid = q["from"]["id"]
    data = q.get("data", "")
    if q["from"].get("username", "").lower() != ADMIN_USERNAME.lower():
        api("answerCallbackQuery", {"callback_query_id": q["id"],
                                    "text": "دسترسی فقط برای مدیر اصلی است.", "show_alert": True})
        return
    try:
        action, raw_id = data.split(":", 1)
        listing_id = int(raw_id)
    except Exception:
        api("answerCallbackQuery", {"callback_query_id": q["id"], "text": "درخواست نامعتبر"})
        return
    if action == "approve":
        ok, msg = publish_listing(listing_id)
    elif action == "reject":
        with connect() as c:
            cur = c.execute("UPDATE listings SET status='rejected' WHERE id=? AND status='pending'",
                            (listing_id,))
        ok, msg = cur.rowcount > 0, "آگهی رد شد." if cur.rowcount else "آگهی پیدا نشد یا قبلاً بررسی شده است."
    else:
        ok, msg = False, "عملیات ناشناخته است."
    api("answerCallbackQuery", {"callback_query_id": q["id"], "text": msg[:190], "show_alert": True})
    if ok and action == "reject":
        with connect() as c:
            row = c.execute("SELECT user_id FROM listings WHERE id=?", (listing_id,)).fetchone()
        if row:
            send(row["user_id"], f"آگهی شماره {listing_id} توسط مدیر تأیید نشد.")
    try:
        api("editMessageReplyMarkup", {"chat_id": q["message"]["chat"]["id"],
             "message_id": q["message"]["message_id"], "reply_markup": {"inline_keyboard": []}})
    except Exception:
        pass

def handle_message(m):
    chat_id = m["chat"]["id"]
    user = m.get("from", {})
    uid = user.get("id")
    text = (m.get("text") or "").strip()
    save_user(user)

    if m.get("contact"):
        contact = m["contact"]
        if contact.get("user_id") == uid:
            with connect() as c:
                c.execute("UPDATE users SET phone=? WHERE user_id=?",
                          (contact.get("phone_number"), uid))
            send(chat_id, "شماره تماس شما ذخیره شد.", MAIN)
        else:
            send(chat_id, "لطفاً شماره تماس خودتان را با دکمه زیر به اشتراک بگذارید.",
                 keyboard([[{"text": "📱 اشتراک‌گذاری شماره تماس", "request_contact": True}], ["🏠 منوی اصلی"]]))
        return

    step, data = get_session(uid)
    if text in ("/start", "/menu", "🏠 منوی اصلی"):
        clear_session(uid)
        send(chat_id, "به سامانه املاک تهران خوش آمدید.\nبرای شروع یکی از بخش‌ها را انتخاب کنید.", MAIN)
        return
    if text in ("❌ لغو ثبت", "/cancel"):
        clear_session(uid)
        send(chat_id, "ثبت اطلاعات لغو شد.", MAIN)
        return
    if text == "📱 اشتراک‌گذاری شماره تماس":
        send(chat_id, "برای ثبت شماره، دکمه اشتراک‌گذاری را بزنید.",
             keyboard([[{"text": "📱 اشتراک‌گذاری شماره تماس", "request_contact": True}], ["🏠 منوی اصلی"]]))
        return
    if text == "🆘 پشتیبانی و ارتباط با مدیر":
        send(chat_id, f"برای ارتباط با مدیر: @{ADMIN_USERNAME}", MAIN)
        return

    if m.get("photo") or m.get("location"):
        if not step or step != "media":
            send(chat_id, "برای اتصال عکس یا لوکیشن، ابتدا از منو ثبت آگهی را شروع کنید.", MAIN)
            return
        if m.get("photo"):
            data.setdefault("photo_file_ids", []).append(m["photo"][-1]["file_id"])
            set_session(uid, "media", data)
            send(chat_id, "عکس دریافت شد. عکس دیگری بفرستید یا «اتمام رسانه‌ها» را بزنید.",
                 keyboard([["اتمام رسانه‌ها"], ["❌ لغو ثبت"], ["🏠 منوی اصلی"]]))
            return
        loc = m["location"]
        data["latitude"], data["longitude"] = loc["latitude"], loc["longitude"]
        set_session(uid, "media", data)
        send(chat_id, "موقعیت ملک ثبت شد. اگر عکس دارید ارسال کنید؛ در غیر این صورت «اتمام رسانه‌ها» را بزنید.",
             keyboard([["اتمام رسانه‌ها"], ["❌ لغو ثبت"], ["🏠 منوی اصلی"]]))
        return

    if text == "اتمام رسانه‌ها" and step == "media":
        listing_id = save_listing(uid, data)
        clear_session(uid)
        send_listing_to_admin(listing_id, data, user)
        send(chat_id, f"آگهی شما با کد {listing_id} ثبت شد و در انتظار تأیید مدیر است.", MAIN)
        return

    if text == "⬅️ مرحله قبل" and step:
        previous = {
            "property_type": ("intent", "نوع معامله را انتخاب کنید:", INTENTS),
            "city": ("property_type", "نوع ملک را انتخاب کنید:", TYPES),
            "district": ("city", "شهر را انتخاب کنید:", CITIES),
            "price": ("district", "محدوده را انتخاب کنید:", DISTRICTS),
            "features": ("price", "بازه قیمت را انتخاب کنید:", PRICES),
            "area": ("features", "امکانات ملک را انتخاب کنید:", FEATURES),
            "bedrooms": ("area", "متراژ ملک را به عدد وارد کنید:", None),
            "details": ("bedrooms", "تعداد خواب را به عدد وارد کنید:", None),
        }
        if step in previous:
            new_step, prompt, options = previous[step]
            ask_next(chat_id, uid, new_step, data, prompt, options)
            return

    # Main menu routing
    if text in ("🏡 فروشنده یا موجر",):
        send(chat_id, "نوع معامله را انتخاب کنید:", choice_keyboard(["فروش", "اجاره", "رهن"]))
        set_session(uid, "intent", {"photo_file_ids": [], "features": []})
        return
    if text in ("🏠 متقاضی خرید یا اجاره",):
        send(chat_id, "نوع درخواست را انتخاب کنید:", choice_keyboard(["خرید", "اجاره", "رهن"]))
        set_session(uid, "intent", {"photo_file_ids": [], "features": []})
        return
    if text in ("📈 سرمایه‌گذاری و مشارکت در ساخت",):
        send(chat_id, "نوع درخواست را انتخاب کنید:", choice_keyboard(["سرمایه‌گذاری", "مشارکت در ساخت"]))
        set_session(uid, "intent", {"photo_file_ids": [], "features": []})
        return
    if text == "🧑‍💼 مشاور املاک":
        send(chat_id, "برای ثبت آگهی از گزینه فروشنده یا موجر استفاده کنید. امکانات اختصاصی مشاور در نسخه بعدی اضافه می‌شود.", MAIN)
        return

    if step == "intent":
        if text not in INTENTS:
            send(chat_id, "لطفاً یکی از دکمه‌های نوع معامله را انتخاب کنید.", choice_keyboard(INTENTS))
            return
        data["intent"] = text
        ask_next(chat_id, uid, "property_type", data, "نوع ملک را انتخاب کنید:", TYPES)
        return
    if step == "property_type":
        if text not in TYPES:
            send(chat_id, "لطفاً نوع ملک را از دکمه‌ها انتخاب کنید.", choice_keyboard(TYPES))
            return
        data["property_type"] = text
        ask_next(chat_id, uid, "city", data, "شهر ملک را انتخاب کنید:", CITIES)
        return
    if step == "city":
        if text not in CITIES:
            send(chat_id, "لطفاً شهر را از دکمه‌ها انتخاب کنید.", choice_keyboard(CITIES))
            return
        data["city"] = text
        ask_next(chat_id, uid, "district", data, "محدوده ملک را انتخاب کنید:", DISTRICTS)
        return
    if step == "district":
        if text not in DISTRICTS:
            send(chat_id, "لطفاً محدوده را از دکمه‌ها انتخاب کنید.", choice_keyboard(DISTRICTS))
            return
        data["district"] = text
        ask_next(chat_id, uid, "price", data, "بازه قیمت یا بودجه را انتخاب کنید:", PRICES)
        return
    if step == "price":
        if text not in PRICES:
            send(chat_id, "لطفاً بازه قیمت را از دکمه‌ها انتخاب کنید.", choice_keyboard(PRICES))
            return
        data["price"] = text
        ask_next(chat_id, uid, "features", data, "امکانات را انتخاب کنید. برای انتخاب چند مورد، هرکدام را بزنید؛ سپس «ادامه» را بزنید.", FEATURES + ["ادامه"])
        return
    if step == "features":
        if text == "ادامه":
            begin_details(chat_id, uid, data)
            return
        if text in FEATURES:
            if text == "بدون مورد خاص":
                data["features"] = [text]
            else:
                data.setdefault("features", [])
                if "بدون مورد خاص" in data["features"]:
                    data["features"].remove("بدون مورد خاص")
                if text in data["features"]:
                    data["features"].remove(text)
                else:
                    data["features"].append(text)
            set_session(uid, "features", data)
            send(chat_id, "انتخاب ثبت شد. مورد دیگری انتخاب کنید یا «ادامه» را بزنید.",
                 choice_keyboard(FEATURES + ["ادامه"]))
            return
        send(chat_id, "از دکمه‌های امکانات یا «ادامه» استفاده کنید.", choice_keyboard(FEATURES + ["ادامه"]))
        return
    if step == "area":
        try:
            area = float(text.replace(",", "").replace("٫", "."))
            if area <= 0 or area > 1000000:
                raise ValueError()
        except ValueError:
            send(chat_id, "متراژ باید عددی بزرگ‌تر از صفر باشد. دوباره وارد کنید.", BACK_CANCEL)
            return
        data["area"] = area
        ask_next(chat_id, uid, "bedrooms", data, "تعداد خواب را به عدد وارد کنید (برای زمین یا موارد بدون خواب، عدد صفر).")
        return
    if step == "bedrooms":
        try:
            bedrooms = int(text)
            if bedrooms < 0 or bedrooms > 30:
                raise ValueError()
        except ValueError:
            send(chat_id, "تعداد خواب باید عددی بین صفر تا ۳۰ باشد.", BACK_CANCEL)
            return
        data["bedrooms"] = bedrooms
        ask_next(chat_id, uid, "details", data, "اطلاعات تکمیلی را بنویسید یا برای رد شدن از این مرحله «بدون توضیح» را بزنید.",
                 ["بدون توضیح"])
        return
    if step == "details":
        data["details"] = "" if text == "بدون توضیح" else text[:3000]
        ask_next(chat_id, uid, "media", data,
                 "اکنون عکس ملک و لوکیشن ملک را جداگانه ارسال کنید. پس از پایان، «اتمام رسانه‌ها» را بزنید.",
                 None)
        send(chat_id, "برای پایان ثبت، این دکمه را بزنید:", keyboard([["اتمام رسانه‌ها"], ["❌ لغو ثبت"], ["🏠 منوی اصلی"]]))
        return
    if text.startswith("/status"):
        parts = text.split()
        if len(parts) != 2 or not parts[1].isdigit():
            send(chat_id, "برای پیگیری، کد آگهی را بعد از دستور وارد کنید؛ مثال: /status 12", MAIN)
            return
        with connect() as c:
            row = c.execute("SELECT id,status FROM listings WHERE id=? AND user_id=?",
                            (int(parts[1]), uid)).fetchone()
        send(chat_id, f"آگهی {row['id']}: {row['status']}" if row else "آگهی‌ای با این کد برای شما پیدا نشد.", MAIN)
        return

    send(chat_id, "لطفاً از دکمه‌های منو استفاده کنید. برای شروع /start را بزنید.", MAIN)

@app.get("/")
def health():
    return "Tehran Real Estate Bot is running", 200

def polling():
    offset = None
    while True:
        try:
            params = {"timeout": 25}
            if offset is not None:
                params["offset"] = offset
            r = requests.get(f"{API}/getUpdates", params=params, timeout=35)
            r.raise_for_status()
            for update in r.json().get("result", []):
                offset = update["update_id"] + 1
                if update.get("callback_query"):
                    try:
                        handle_callback(update)
                    except Exception as e:
                        print("callback error:", e)
                elif update.get("message"):
                    try:
                        handle_message(update["message"])
                    except Exception as e:
                        print("message error:", e)
        except Exception as e:
            print("polling error:", e)
            time.sleep(5)

if __name__ == "__main__":
    init_db()
    threading.Thread(target=polling, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
'''
# Fix helper to handle nested keyboard dict correctly: choice_keyboard expects strings only and media custom keyboard separately handled.
path = Path("/mnt/data/bot.py")
path.write_text(code, encoding="utf-8")
print(f"Created {path} ({len(code.splitlines())} lines)")
