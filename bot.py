import os
import json
import time
import sqlite3
import threading
import requests
from flask import Flask

# ==================== تنظیمات ====================

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "AtlasPrime021").lstrip("@")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@tehranrealstate")
DB_PATH = os.getenv("DATABASE_PATH", "realestate.db")
PORT = int(os.getenv("PORT", "10000"))

if not TOKEN:
    raise RuntimeError("متغیر BOT_TOKEN در تنظیمات محیطی وارد نشده است.")

API = f"https://api.telegram.org/bot{TOKEN}"
app = Flask(__name__)

# ==================== پایگاه داده ====================

def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                phone TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                user_id INTEGER PRIMARY KEY,
                step TEXT NOT NULL,
                data TEXT NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                intent TEXT,
                property_type TEXT,
                city TEXT,
                district TEXT,
                price TEXT,
                area REAL,
                bedrooms INTEGER,
                features TEXT,
                details TEXT,
                photos TEXT,
                latitude REAL,
                longitude REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_user(user, phone=None):
    name = " ".join(
        x for x in [user.get("first_name"), user.get("last_name")] if x
    ) or "کاربر"

    with db() as c:
        c.execute("""
            INSERT INTO users (user_id, username, full_name, phone)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                phone = COALESCE(excluded.phone, users.phone)
        """, (user["id"], user.get("username"), name, phone))


def get_session(uid):
    with db() as c:
        row = c.execute(
            "SELECT step, data FROM sessions WHERE user_id=?", (uid,)
        ).fetchone()

    if not row:
        return None, {}

    try:
        return row["step"], json.loads(row["data"])
    except (TypeError, json.JSONDecodeError):
        return None, {}


def set_session(uid, step, data):
    with db() as c:
        c.execute("""
            INSERT INTO sessions (user_id, step, data)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                step=excluded.step, data=excluded.data
        """, (uid, step, json.dumps(data, ensure_ascii=False)))


def clear_session(uid):
    with db() as c:
        c.execute("DELETE FROM sessions WHERE user_id=?", (uid,))


# ==================== ارتباط با تلگرام ====================

def tg(method, payload=None, timeout=30):
    response = requests.post(
        f"{API}/{method}",
        json=payload or {},
        timeout=timeout
    )
    response.raise_for_status()
    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(result.get("description", "Telegram API error"))

    return result.get("result")


def send(chat_id, text, markup=None):
    payload = {"chat_id": chat_id, "text": str(text)}

    if markup:
        payload["reply_markup"] = markup

    try:
        tg("sendMessage", payload)
    except Exception as exc:
        print("ارسال پیام ناموفق:", exc)


def keyboard(rows):
    return {
        "keyboard": [
            [{"text": item} for item in row]
            for row in rows
        ],
        "resize_keyboard": True
    }


def choices(items, columns=2):
    rows = [
        items[i:i + columns]
        for i in range(0, len(items), columns)
    ]
    rows += [
        ["⬅️ مرحله قبل", "❌ لغو ثبت"],
        ["🏠 منوی اصلی"]
    ]
    return keyboard(rows)


MAIN_MENU = keyboard([
    ["🏠 متقاضی خرید یا اجاره"],
    ["🏡 فروشنده یا موجر"],
    ["📈 سرمایه‌گذاری و مشارکت در ساخت"],
    ["🧑‍💼 مشاور املاک"],
    ["📋 پیگیری آگهی"],
    ["🆘 پشتیبانی و ارتباط با مدیر"]
])

CANCEL_MENU = keyboard([
    ["❌ لغو ثبت"],
    ["🏠 منوی اصلی"]
])

INTENTS = [
    "فروش", "اجاره", "خرید", "رهن",
    "سرمایه‌گذاری", "مشارکت در ساخت"
]

PROPERTY_TYPES = [
    "آپارتمان", "ویلا", "زمین", "مغازه",
    "دفتر کار", "باغ", "کلنگی", "سایر"
]

CITIES = [
    "تهران", "کرج", "پردیس", "دماوند",
    "شهریار", "شهر دیگر"
]

DISTRICTS = [
    "شمال", "جنوب", "شرق", "غرب",
    "مرکز", "محدوده دیگر"
]

PRICES = [
    "زیر ۵ میلیارد",
    "۵ تا ۱۰ میلیارد",
    "۱۰ تا ۲۰ میلیارد",
    "۲۰ تا ۵۰ میلیارد",
    "بیش از ۵۰ میلیارد",
    "توافقی"
]

FEATURES = [
    "پارکینگ", "آسانسور", "انباری",
    "بالکن", "استخر", "حیاط",
    "سند رسمی", "نوساز", "بدون مورد خاص"
]


def ask(uid, chat_id, step, data, message, options=None):
    set_session(uid, step, data)
    send(
        chat_id,
        message,
        choices(options) if options else CANCEL_MENU
    )


def start_listing(chat_id, user, intent):
    data = {
        "intent": intent,
        "features": [],
        "photos": [],
        "latitude": None,
        "longitude": None
    }
    ask(
        user["id"], chat_id,
        "property_type", data,
        "نوع ملک را انتخاب کنید:",
        PROPERTY_TYPES
    )


# ==================== ثبت آگهی ====================

def save_listing(uid, data):
    with db() as c:
        cur = c.execute("""
            INSERT INTO listings (
                user_id, intent, property_type, city, district,
                price, area, bedrooms, features, details, photos,
                latitude, longitude, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (
            uid,
            data["intent"],
            data["property_type"],
            data["city"],
            data["district"],
            data["price"],
            data["area"],
            data["bedrooms"],
            json.dumps(data.get("features", []), ensure_ascii=False),
            data.get("details", ""),
            json.dumps(data.get("photos", [])),
            data.get("latitude"),
            data.get("longitude")
        ))

        return cur.lastrowid


def listing_text(listing_id, data):
    return (
        f"🏡 آگهی جدید املاک تهران\n\n"
        f"کد آگهی: {listing_id}\n"
        f"نوع معامله: {data['intent']}\n"
        f"نوع ملک: {data['property_type']}\n"
        f"شهر: {data['city']}\n"
        f"محدوده: {data['district']}\n"
        f"قیمت: {data['price']}\n"
        f"متراژ: {data['area']} متر مربع\n"
        f"تعداد خواب: {data['bedrooms']}\n"
        f"امکانات: {', '.join(data.get('features', [])) or 'ذکر نشده'}\n"
        f"توضیحات: {data.get('details') or 'ندارد'}\n"
        f"تعداد عکس‌ها: {len(data.get('photos', []))}\n"
        f"موقعیت ملک: "
        f"{'ثبت شده' if data.get('latitude') is not None else 'ثبت نشده'}\n\n"
        "وضعیت: در انتظار بررسی مدیر"
    )


def notify_admin(listing_id, data, user):
    if not ADMIN_ID:
        print("ADMIN_ID تنظیم نشده؛ آگهی در پایگاه داده ذخیره شد.")
        return

    text = listing_text(listing_id, data)
    text += f"\nشناسه ثبت‌کننده: {user['id']}"

    markup = {
        "inline_keyboard": [[
            {
                "text": "✅ تأیید و انتشار",
                "callback_data": f"approve:{listing_id}"
            },
            {
                "text": "❌ رد آگهی",
                "callback_data": f"reject:{listing_id}"
            }
        ]]
    }

    try:
        tg("sendMessage", {
            "chat_id": ADMIN_ID,
            "text": text,
            "reply_markup": markup
        })

        for photo_id in data.get("photos", [])[:10]:
            tg("sendPhoto", {
                "chat_id": ADMIN_ID,
                "photo": photo_id,
                "caption": f"عکس آگهی شماره {listing_id}"
            })

        if data.get("latitude") is not None:
            tg("sendLocation", {
                "chat_id": ADMIN_ID,
                "latitude": data["latitude"],
                "longitude": data["longitude"]
            })

    except Exception as exc:
        print("خطا در ارسال آگهی به مدیر:", exc)


def publish_listing(listing_id):
    with db() as c:
        row = c.execute(
            "SELECT * FROM listings WHERE id=?",
            (listing_id,)
        ).fetchone()

        if not row or row["status"] != "pending":
            return False, "آگهی پیدا نشد یا قبلاً بررسی شده است."

        features = json.loads(row["features"] or "[]")
        photos = json.loads(row["photos"] or "[]")

        text = (
            f"🏡 آگهی تأییدشده املاک تهران\n\n"
            f"کد آگهی: {row['id']}\n"
            f"نوع معامله: {row['intent']}\n"
            f"نوع ملک: {row['property_type']}\n"
            f"شهر: {row['city']}\n"
            f"محدوده: {row['district']}\n"
            f"قیمت: {row['price']}\n"
            f"متراژ: {row['area']} متر مربع\n"
            f"تعداد خواب: {row['bedrooms']}\n"
            f"امکانات: {', '.join(features) or 'ذکر نشده'}\n"
            f"توضیحات: {row['details'] or 'ندارد'}\n\n"
            "برای پیگیری این آگهی، از ربات استفاده کنید."
        )

        try:
            if photos:
                tg("sendPhoto", {
                    "chat_id": CHANNEL_ID,
                    "photo": photos[0],
                    "caption": text
                })

                for photo_id in photos[1:10]:
                    tg("sendPhoto", {
                        "chat_id": CHANNEL_ID,
                        "photo": photo_id
                    })
            else:
                tg("sendMessage", {
                    "chat_id": CHANNEL_ID,
                    "text": text
                })

            c.execute(
                "UPDATE listings SET status='published' "
                "WHERE id=? AND status='pending'",
                (listing_id,)
            )
            return True, "آگهی در کانال منتشر شد."

        except Exception as exc:
            print("خطای انتشار:", exc)
            return False, "انتشار ناموفق بود؛ دسترسی ربات به کانال را بررسی کنید."


# ==================== تأیید مدیر ====================

def handle_callback(update):
    query = update["callback_query"]
    user = query["from"]
    callback = query.get("data", "")

    if not ADMIN_ID or user["id"] != ADMIN_ID:
        tg("answerCallbackQuery", {
            "callback_query_id": query["id"],
            "text": "این عملیات فقط برای مدیر اصلی مجاز است.",
            "show_alert": True
        })
        return

    try:
        action, raw_id = callback.split(":", 1)
        listing_id = int(raw_id)
    except (ValueError, TypeError):
        tg("answerCallbackQuery", {
            "callback_query_id": query["id"],
            "text": "درخواست نامعتبر است."
        })
        return

    if action == "approve":
        success, message = publish_listing(listing_id)

    elif action == "reject":
        with db() as c:
            cur = c.execute("""
                UPDATE listings SET status='rejected'
                WHERE id=? AND status='pending'
            """, (listing_id,))
            success = cur.rowcount > 0

        message = "آگهی رد شد." if success else "آگهی بررسی شده یا وجود ندارد."

        if success:
            with db() as c:
                row = c.execute(
                    "SELECT user_id FROM listings WHERE id=?",
                    (listing_id,)
                ).fetchone()

            if row:
                send(
                    row["user_id"],
                    f"آگهی شماره {listing_id} توسط مدیر تأیید نشد.",
                    MAIN_MENU
                )
    else:
        success, message = False, "عملیات ناشناخته است."

    tg("answerCallbackQuery", {
        "callback_query_id": query["id"],
        "text": message[:190],
        "show_alert": True
    })

    if success and action == "approve":
        with db() as c:
            row = c.execute(
                "SELECT user_id FROM listings WHERE id=?",
                (listing_id,)
            ).fetchone()

        if row:
            send(
                row["user_id"],
                f"آگهی شماره {listing_id} تأیید و منتشر شد.",
                MAIN_MENU
            )

    try:
        tg("editMessageReplyMarkup", {
            "chat_id": query["message"]["chat"]["id"],
            "message_id": query["message"]["message_id"],
            "reply_markup": {"inline_keyboard": []}
        })
    except Exception as exc:
        print("خطا در حذف دکمه‌های بررسی:", exc)


# ==================== مدیریت پیام‌ها ====================

def handle_message(message):
    chat_id = message["chat"]["id"]
    user = message.get("from", {})
    uid = user.get("id")

    if not uid:
        return

    text = (message.get("text") or "").strip()
    save_user(user)

    if message.get("contact"):
        contact = message["contact"]

        if contact.get("user_id") == uid:
            save_user(user, contact.get("phone_number"))
            send(chat_id, "شماره تماس ذخیره شد.", MAIN_MENU)
        else:
            send(chat_id, "لطفاً شماره تماس خودتان را ارسال کنید.", MAIN_MENU)
        return

    step, data = get_session(uid)

    if text in ("/start", "/menu", "🏠 منوی اصلی"):
        clear_session(uid)
        send(
            chat_id,
            "به سامانه املاک تهران خوش آمدید.\nیکی از گزینه‌ها را انتخاب کنید.",
            MAIN_MENU
        )
        return

    if text in ("❌ لغو ثبت", "/cancel"):
        clear_session(uid)
        send(chat_id, "ثبت لغو شد.", MAIN_MENU)
        return

    if text == "🆘 پشتیبانی و ارتباط با مدیر":
        send(
            chat_id,
            f"برای ارتباط با مدیر: @{ADMIN_USERNAME}",
            MAIN_MENU
        )
        return

    if text == "🏠 متقاضی خرید یا اجاره":
        ask(
            uid, chat_id, "intent",
            {"features": [], "photos": []},
            "نوع درخواست را انتخاب کنید:",
            ["خرید", "اجاره", "رهن"]
        )
        return

    if text == "🏡 فروشنده یا موجر":
        ask(
            uid, chat_id, "intent",
            {"features": [], "photos": []},
            "نوع معامله را انتخاب کنید:",
            ["فروش", "اجاره", "رهن"]
        )
        return

    if text == "📈 سرمایه‌گذاری و مشارکت در ساخت":
        ask(
            uid, chat_id, "intent",
            {"features": [], "photos": []},
            "نوع درخواست را انتخاب کنید:",
            ["سرمایه‌گذاری", "مشارکت در ساخت"]
        )
        return

    if text == "🧑‍💼 مشاور املاک":
        send(
            chat_id,
            "برای ثبت آگهی از بخش «فروشنده یا موجر» استفاده کنید.",
            MAIN_MENU
        )
        return

    if text == "📋 پیگیری آگهی":
        send(
            chat_id,
            "کد آگهی را به این شکل ارسال کنید:\n/status 12",
            MAIN_MENU
        )
        return

    if text.startswith("/status"):
        parts = text.split()

        if len(parts) != 2 or not parts[1].isdigit():
            send(chat_id, "نمونه صحیح: /status 12", MAIN_MENU)
            return

        with db() as c:
            row = c.execute("""
                SELECT id, status FROM listings
                WHERE id=? AND user_id=?
            """, (int(parts[1]), uid)).fetchone()

        if row:
            send(
                chat_id,
                f"کد آگهی: {row['id']}\nوضعیت: {row['status']}",
                MAIN_MENU
            )
        else:
            send(chat_id, "آگهی با این کد برای شما پیدا نشد.", MAIN_MENU)
        return

    # مرحله انتخاب نوع معامله
    if step == "intent":
        if text not in INTENTS:
            send(chat_id, "یکی از گزینه‌های نوع معامله را انتخاب کنید.",
                 choices(INTENTS))
            return

        data["intent"] = text
        ask(uid, chat_id, "property_type", data,
            "نوع ملک را انتخاب کنید:", PROPERTY_TYPES)
        return

    if step == "property_type":
        if text not in PROPERTY_TYPES:
            send(chat_id, "نوع ملک را از گزینه‌ها انتخاب کنید.",
                 choices(PROPERTY_TYPES))
            return

        data["property_type"] = text
        ask(uid, chat_id, "city", data,
            "شهر ملک را انتخاب کنید:", CITIES)
        return

    if step == "city":
        if text not in CITIES:
            send(chat_id, "شهر را از گزینه‌ها انتخاب کنید.", choices(CITIES))
            return

        data["city"] = text
        ask(uid, chat_id, "district", data,
            "محدوده ملک را انتخاب کنید:", DISTRICTS)
        return

    if step == "district":
        if text not in DISTRICTS:
            send(chat_id, "محدوده را از گزینه‌ها انتخاب کنید.",
                 choices(DISTRICTS))
            return

        data["district"] = text
        ask(uid, chat_id, "price", data,
            "بازه قیمت یا بودجه را انتخاب کنید:", PRICES)
        return

    if step == "price":
        if text not in PRICES:
            send(chat_id, "قیمت را از گزینه‌ها انتخاب کنید.", choices(PRICES))
            return

        data["price"] = text
        ask(
            uid, chat_id, "features", data,
            "امکانات را انتخاب کنید. برای انتخاب چند مورد، چند دکمه را بزنید؛ سپس «ادامه» را بزنید.",
            FEATURES + ["ادامه"]
        )
        return

    if step == "features":
        if text == "ادامه":
            ask(uid, chat_id, "area", data,
                "متراژ را به عدد و بر حسب متر مربع وارد کنید.")
            return

        if text in FEATURES:
            selected = data.setdefault("features", [])

            if text == "بدون مورد خاص":
                data["features"] = [text]
            else:
                if "بدون مورد خاص" in selected:
                    selected.remove("بدون مورد خاص")

                if text in selected:
                    selected.remove(text)
                else:
                    selected.append(text)

            set_session(uid, "features", data)
            send(
                chat_id,
                "انتخاب ثبت شد. مورد دیگری انتخاب کنید یا «ادامه» را بزنید.",
                choices(FEATURES + ["ادامه"])
            )
            return

        send(chat_id, "از دکمه‌های امکانات استفاده کنید.",
             choices(FEATURES + ["ادامه"]))
        return

    if step == "area":
        try:
            area = float(text.replace(",", "").replace("٫", "."))
            if not 0 < area <= 1000000:
                raise ValueError
        except ValueError:
            send(chat_id, "متراژ باید عددی بزرگ‌تر از صفر باشد.")
            return

        data["area"] = area
        ask(uid, chat_id, "bedrooms", data,
            "تعداد خواب را وارد کنید. برای زمین عدد صفر بنویسید.")
        return

    if step == "bedrooms":
        try:
            bedrooms = int(text)
            if not 0 <= bedrooms <= 30:
                raise ValueError
        except ValueError:
            send(chat_id, "تعداد خواب باید عددی بین صفر تا ۳۰ باشد.")
            return

        data["bedrooms"] = bedrooms
        ask(
            uid, chat_id, "details", data,
            "توضیحات تکمیلی را بنویسید یا «بدون توضیح» را انتخاب کنید.",
            ["بدون توضیح"]
        )
        return

    if step == "details":
        data["details"] = "" if text == "بدون توضیح" else text[:3000]
        ask(
            uid, chat_id, "media", data,
            "عکس‌های ملک را ارسال کنید. می‌توانید موقعیت ملک را هم با گزینه مکان تلگرام بفرستید. پس از پایان، «اتمام رسانه‌ها» را بزنید.",
            None
        )
        send(
            chat_id,
            "برای پایان ثبت، این دکمه را بزنید:",
            keyboard([
                ["اتمام رسانه‌ها"],
                ["❌ لغو ثبت"],
                ["🏠 منوی اصلی"]
            ])
        )
        return

    if step == "media":
        if message.get("photo"):
            photos = data.setdefault("photos", [])

            if len(photos) >= 10:
                send(chat_id, "حداکثر ۱۰ عکس می‌توانید ارسال کنید.")
                return

            photos.append(message["photo"][-1]["file_id"])
            set_session(uid, "media", data)

            send(
                chat_id,
                f"عکس دریافت شد ({len(photos)} از ۱۰). عکس دیگری بفرستید یا «اتمام رسانه‌ها» را بزنید.",
                keyboard([
                    ["اتمام رسانه‌ها"],
                    ["❌ لغو ثبت"],
                    ["🏠 منوی اصلی"]
                ])
            )
            return

        if message.get("location"):
            loc = message["location"]
            data["latitude"] = loc["latitude"]
            data["longitude"] = loc["longitude"]
            set_session(uid, "media", data)

            send(
                chat_id,
                "موقعیت دریافت شد. برای پایان، «اتمام رسانه‌ها» را بزنید.",
                keyboard([
                    ["اتمام رسانه‌ها"],
                    ["❌ لغو ثبت"],
                    ["🏠 منوی اصلی"]
                ])
            )
            return

        if text == "اتمام رسانه‌ها":
            listing_id = save_listing(uid, data)
            clear_session(uid)

            notify_admin(listing_id, data, user)

            send(
                chat_id,
                f"آگهی شما با کد {listing_id} ثبت شد و در انتظار بررسی مدیر است.",
                MAIN_MENU
            )
            return

        send(
            chat_id,
            "لطفاً عکس، موقعیت ملک یا دکمه «اتمام رسانه‌ها» را ارسال کنید.",
            keyboard([
                ["اتمام رسانه‌ها"],
                ["❌ لغو ثبت"],
                ["🏠 منوی اصلی"]
            ])
        )
        return

    if text == "⬅️ مرحله قبل" and step:
        previous = {
            "property_type": ("intent", "نوع معامله را انتخاب کنید:", INTENTS),
            "city": ("property_type", "نوع ملک را انتخاب کنید:", PROPERTY_TYPES),
            "district": ("city", "شهر را انتخاب کنید:", CITIES),
            "price": ("district", "محدوده ملک را انتخاب کنید:", DISTRICTS),
            "features": ("price", "بازه قیمت را انتخاب کنید:", PRICES),
            "area": ("features", "امکانات ملک را انتخاب کنید:", FEATURES + ["ادامه"]),
            "bedrooms": ("area", "متراژ را وارد کنید:", None),
            "details": ("bedrooms", "تعداد خواب را وارد کنید:", None)
        }

        if step in previous:
            new_step, prompt, options = previous[step]
            ask(uid, chat_id, new_step, data, prompt, options)
            return

    send(
        chat_id,
        "برای شروع از گزینه‌های منو استفاده کنید یا /start را بزنید.",
        MAIN_MENU
    )


# ==================== وب‌سرور و اجرای ربات ====================

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

            response = requests.get(
                f"{API}/getUpdates",
                params=params,
                timeout=35
            )
            response.raise_for_status()

            for update in response.json().get("result", []):
                offset = update["update_id"] + 1

                try:
                    if update.get("callback_query"):
                        handle_callback(update)
                    elif update.get("message"):
                        handle_message(update["message"])
                except Exception as exc:
                    print("خطا در پردازش به‌روزرسانی:", exc)

        except Exception as exc:
            print("خطای دریافت پیام‌ها:", exc)
            time.sleep(5)


if __name__ == "__main__":
    init_db()

    threading.Thread(
        target=polling,
        daemon=True
    ).start()

    app.run(
        host="0.0.0.0",
        port=PORT
    )
