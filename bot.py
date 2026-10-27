
import os
import json
import time
import html
import sqlite3
import threading
import urllib.parse
import urllib.request

from flask import Flask, jsonify

# ==================== تنظیمات ====================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = 6245308636
CHANNEL_ID = "@tehranrealstate"
DATABASE_PATH = os.getenv("DATABASE_PATH", "realestate.db")
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN در تنظیمات Render تنظیم نشده است.")

API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

app = Flask(__name__)

# ==================== پایگاه داده ====================

db_lock = threading.RLock()
db = sqlite3.connect(
    DATABASE_PATH, check_same_thread=False, timeout=30
)
db.row_factory = sqlite3.Row

with db_lock:
    db.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT,
        data TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at INTEGER NOT NULL
    )
    """)
    db.commit()

sessions = {}
user_states = {}
polling_started = False
polling_lock = threading.Lock()
last_update_time = None
bot_username = None

# ==================== وب‌سرور Render ====================

@app.route("/")
def home():
    return jsonify({
        "service": "Tehran Real Estate Telegram Bot",
        "status": "running",
        "bot": bot_username
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "telegram_polling": polling_started,
        "last_update_time": last_update_time
    })


# ==================== ارتباط با تلگرام ====================

def api(method, data=None, timeout=60):
    data = data or {}
    request = urllib.request.Request(
        API + method,
        data=urllib.parse.urlencode(data).encode()
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode())
    except Exception as exc:
        print(f"Telegram API error ({method}): {exc}", flush=True)
        return None

    if not result.get("ok"):
        print(f"Telegram API error ({method}): {result}", flush=True)
        return None

    return result.get("result")


def send_message(chat_id, text, keyboard=None, parse_mode="HTML"):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if keyboard:
        payload["reply_markup"] = json.dumps(
            keyboard, ensure_ascii=False
        )
    return api("sendMessage", payload)


def send_photo(chat_id, photo_id, caption, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "photo": photo_id,
        "caption": caption[:1024],
        "parse_mode": "HTML"
    }
    if keyboard:
        payload["reply_markup"] = json.dumps(
            keyboard, ensure_ascii=False
        )
    return api("sendPhoto", payload)


def answer_callback(callback_id, text=""):
    api("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": text[:180]
    })


def button(text, callback_data):
    return {"text": text, "callback_data": callback_data}


def menu_keyboard():
    return {
        "inline_keyboard": [
            [button("ثبت آگهی", "new_listing")],
            [button("راهنمای ثبت آگهی", "help")],
            [button("لغو عملیات", "cancel")]
        ]
    }


def choices_keyboard(options):
    rows = [[button(label, f"pick:{value}")]
            for label, value in options]
    rows.append([
        button("قبلی", "back"),
        button("لغو", "cancel")
    ])
    return {"inline_keyboard": rows}


def navigation_keyboard():
    return {
        "inline_keyboard": [
            [button("قبلی", "back"), button("لغو", "cancel")]
        ]
    }


# ==================== مراحل ثبت آگهی ====================

STEPS = [
    "intent", "property_type", "city", "district",
    "price", "description", "contact", "location", "photos"
]

OPTIONS = {
    "intent": [
        ("فروش", "فروش"),
        ("خرید", "خرید"),
        ("اجاره", "اجاره"),
        ("رهن کامل", "رهن کامل"),
        ("سرمایه‌گذاری", "سرمایه‌گذاری")
    ],
    "property_type": [
        ("آپارتمان", "آپارتمان"),
        ("خانه و ویلا", "خانه و ویلا"),
        ("زمین", "زمین"),
        ("مغازه و واحد تجاری", "تجاری"),
        ("دفتر اداری", "اداری"),
        ("باغ", "باغ"),
        ("ملک صنعتی", "صنعتی"),
        ("سایر", "سایر")
    ],
    "city": [
        ("تهران", "تهران"),
        ("کرج", "کرج"),
        ("مشهد", "مشهد"),
        ("اصفهان", "اصفهان"),
        ("شیراز", "شیراز"),
        ("شهر دیگر", "other")
    ],
    "district": [
        ("شمال", "شمال"),
        ("جنوب", "جنوب"),
        ("شرق", "شرق"),
        ("غرب", "غرب"),
        ("مرکز", "مرکز"),
        ("نام محله یا محدوده دیگر", "other")
    ]
}


def start_listing(user_id, username):
    sessions[user_id] = {
        "user_id": user_id,
        "username": username or "",
        "photos": [],
        "location": None
    }
    user_states[user_id] = "intent"
    show_step(user_id)


def show_step(user_id):
    state = user_states.get(user_id)
    if user_id not in sessions or state not in STEPS:
        send_message(user_id, "از منوی اصلی استفاده کن.", menu_keyboard())
        return

    prompts = {
        "intent": "نوع معامله را انتخاب کن:",
        "property_type": "نوع ملک را انتخاب کن:",
        "city": "شهر ملک را انتخاب کن یا نام آن را بنویس:",
        "district": "محدوده را انتخاب کن یا نام محله را بنویس:",
        "price": "قیمت یا مبلغ موردنظر را وارد کن. مثال: ۱۲ میلیارد تومان",
        "description": "توضیحات ملک، متراژ، امکانات و شرایط معامله را بنویس:",
        "contact": "شماره تماس یا روش تماس را وارد کن:",
        "location": "موقعیت ملک را با پیوست تلگرام و گزینه Location بفرست یا رد کن:",
        "photos": "تصاویر ملک را بفرست. پس از اتمام، «پایان تصاویر» را بزن."
    }

    if state in OPTIONS:
        keyboard = choices_keyboard(OPTIONS[state])
    elif state == "location":
        keyboard = {
            "inline_keyboard": [
                [button("رد کردن", "skip:location")],
                [button("قبلی", "back"), button("لغو", "cancel")]
            ]
        }
    elif state == "photos":
        keyboard = {
            "inline_keyboard": [
                [button("پایان تصاویر و ارسال برای بررسی", "finish")],
                [button("بدون تصویر ادامه بده", "skip:photos")],
                [button("قبلی", "back"), button("لغو", "cancel")]
            ]
        }
    else:
        keyboard = navigation_keyboard()

    send_message(user_id, prompts[state], keyboard)


def go_next(user_id):
    state = user_states.get(user_id)
    if state not in STEPS:
        return
    index = STEPS.index(state)
    if index == len(STEPS) - 1:
        submit_listing(user_id)
    else:
        user_states[user_id] = STEPS[index + 1]
        show_step(user_id)


def go_back(user_id):
    state = user_states.get(user_id)
    if state not in STEPS:
        send_message(user_id, "منوی اصلی:", menu_keyboard())
        return
    index = STEPS.index(state)
    if index == 0:
        send_message(user_id, "منوی اصلی:", menu_keyboard())
    else:
        user_states[user_id] = STEPS[index - 1]
        show_step(user_id)


# ==================== آگهی‌ها ====================

def listing_text(listing_id, data):
    lines = [
        f"🏠 <b>آگهی املاک شماره {listing_id}</b>",
        "",
        f"معامله: {html.escape(data.get('intent', '-'))}",
        f"نوع ملک: {html.escape(data.get('property_type', '-'))}",
        f"شهر: {html.escape(data.get('city', '-'))}",
        f"محدوده: {html.escape(data.get('district', '-'))}",
        f"قیمت: {html.escape(data.get('price', '-'))}",
        "",
        "<b>توضیحات:</b>",
        html.escape(data.get("description", "-")),
        "",
        f"تماس: {html.escape(data.get('contact', '-'))}"
    ]

    loc = data.get("location")
    if loc:
        lines.append(
            f"موقعیت: {loc['latitude']}, {loc['longitude']}"
        )

    return "\n".join(lines)


def submit_listing(user_id):
    data = sessions.get(user_id)
    if not data:
        send_message(user_id, "اطلاعات آگهی پیدا نشد.", menu_keyboard())
        return

    required = [
        "intent", "property_type", "city", "district",
        "price", "description", "contact"
    ]
    missing = [key for key in required if not data.get(key)]
    if missing:
        user_states[user_id] = missing[0]
        show_step(user_id)
        return

    with db_lock:
        cursor = db.execute(
            """INSERT INTO listings
            (user_id, username, data, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)""",
            (
                user_id,
                data.get("username", ""),
                json.dumps(data, ensure_ascii=False),
                int(time.time())
            )
        )
        db.commit()
        listing_id = cursor.lastrowid

    caption = listing_text(listing_id, data)
    keyboard = {
        "inline_keyboard": [[
            button("تأیید و انتشار", f"approve:{listing_id}"),
            button("رد آگهی", f"reject:{listing_id}")
        ]]
    }

    if data.get("photos"):
        result = send_photo(
            ADMIN_ID, data["photos"][0], caption, keyboard
        )
    else:
        result = send_message(ADMIN_ID, caption, keyboard)

    sessions.pop(user_id, None)
    user_states.pop(user_id, None)

    if result:
        send_message(
            user_id,
            f"آگهی شماره {listing_id} برای بررسی مدیر ارسال شد.",
            menu_keyboard()
        )
    else:
        send_message(
            user_id,
            f"آگهی شماره {listing_id} ذخیره شد، اما ارسال آن به مدیر ناموفق بود.",
            menu_keyboard()
        )


def get_listing(listing_id):
    with db_lock:
        return db.execute(
            "SELECT * FROM listings WHERE id = ?", (listing_id,)
        ).fetchone()


def approve_listing(listing_id):
    row = get_listing(listing_id)
    if not row:
        return "آگهی پیدا نشد."
    if row["status"] != "pending":
        return "این آگهی قبلاً بررسی شده است."

    data = json.loads(row["data"])
    caption = listing_text(listing_id, data)

    if data.get("photos"):
        result = send_photo(CHANNEL_ID, data["photos"][0], caption)
    else:
        result = send_message(CHANNEL_ID, caption)

    if not result:
        return "انتشار ناموفق بود؛ دسترسی ربات به کانال را بررسی کن."

    with db_lock:
        db.execute(
            "UPDATE listings SET status = 'published' WHERE id = ?",
            (listing_id,)
        )
        db.commit()

    send_message(
        row["user_id"],
        f"آگهی شماره {listing_id} تأیید و منتشر شد."
    )
    return "آگهی تأیید و منتشر شد."


def reject_listing(listing_id):
    row = get_listing(listing_id)
    if not row:
        return "آگهی پیدا نشد."
    if row["status"] != "pending":
        return "این آگهی قبلاً بررسی شده است."

    with db_lock:
        db.execute(
            "UPDATE listings SET status = 'rejected' WHERE id = ?",
            (listing_id,)
        )
        db.commit()

    send_message(
        row["user_id"],
        f"آگهی شماره {listing_id} تأیید نشد. می‌توانی دوباره ثبت کنی."
    )
    return "آگهی رد شد."


# ==================== پیام‌های کاربران ====================

def handle_text(message):
    user_id = message["from"]["id"]
    username = message["from"].get("username", "")
    text = message.get("text", "").strip()

    if text in ("/start", "/menu"):
        sessions.pop(user_id, None)
        user_states.pop(user_id, None)
        send_message(
            user_id,
            "به سامانه املاک خوش آمدی. گزینه موردنظر را انتخاب کن:",
            menu_keyboard()
        )
        return

    if text == "/myid":
        send_message(user_id, f"شناسه شما: <code>{user_id}</code>")
        return

    if user_id not in sessions:
        send_message(user_id, "از منوی اصلی استفاده کن.", menu_keyboard())
        return

    state = user_states.get(user_id)
    data = sessions[user_id]

    if state in ("city", "district"):
        data[state] = text
        go_next(user_id)
    elif state in ("price", "description", "contact"):
        data[state] = text
        go_next(user_id)
    elif state == "photos":
        if text == "پایان تصاویر":
            submit_listing(user_id)
        else:
            send_message(
                user_id,
                "تصویر بفرست یا دکمه «پایان تصاویر» را بزن.",
                {
                    "inline_keyboard": [
                        [button("پایان تصاویر", "finish")],
                        [button("قبلی", "back"), button("لغو", "cancel")]
                    ]
                }
            )
    else:
        send_message(user_id, "از دکمه‌های مرحله فعلی استفاده کن.")


def handle_media(message):
    user_id = message["from"]["id"]
    state = user_states.get(user_id)
    data = sessions.get(user_id)

    if not data:
        return

    if state == "location" and message.get("location"):
        loc = message["location"]
        data["location"] = {
            "latitude": loc["latitude"],
            "longitude": loc["longitude"]
        }
        go_next(user_id)
    elif state == "photos" and message.get("photo"):
        data["photos"].append(message["photo"][-1]["file_id"])
        send_message(
            user_id,
            f"تصویر دریافت شد؛ تعداد تصاویر: {len(data['photos'])}",
            {
                "inline_keyboard": [
                    [button("ارسال تصویر دیگر", "more_photo")],
                    [button("پایان تصاویر", "finish")],
                    [button("قبلی", "back"), button("لغو", "cancel")]
                ]
            }
        )
    else:
        send_message(user_id, "این فایل در مرحله فعلی قابل استفاده نیست.")


# ==================== دکمه‌های تلگرام ====================

def handle_callback(query):
    callback_id = query["id"]
    user_id = query["from"]["id"]
    data = query.get("data", "")

    if data == "cancel":
        sessions.pop(user_id, None)
        user_states.pop(user_id, None)
        answer_callback(callback_id, "لغو شد")
        send_message(user_id, "عملیات لغو شد.", menu_keyboard())
        return

    if data == "help":
        answer_callback(callback_id)
        send_message(
            user_id,
            "مراحل ثبت آگهی را تکمیل کن. آگهی قبل از انتشار توسط مدیر بررسی می‌شود.",
            menu_keyboard()
        )
        return

    if data == "new_listing":
        answer_callback(callback_id)
        start_listing(user_id, query["from"].get("username", ""))
        return

    if data == "back":
        answer_callback(callback_id)
        go_back(user_id)
        return

    if data.startswith("pick:"):
        if user_id not in sessions:
            answer_callback(callback_id, "ابتدا ثبت آگهی را شروع کن.")
            return

        state = user_states.get(user_id)
        value = data.split(":", 1)[1]

        if state not in OPTIONS:
            answer_callback(callback_id, "مرحله معتبر نیست.")
            return

        if value not in {v for _, v in OPTIONS[state]}:
            answer_callback(callback_id, "گزینه نامعتبر است.")
            return

        if value == "other":
            answer_callback(callback_id)
            send_message(
                user_id,
                "نام موردنظر را به‌صورت متنی وارد کن.",
                navigation_keyboard()
            )
            return

        sessions[user_id][state] = value
        answer_callback(callback_id)
        go_next(user_id)
        return

    if data.startswith("skip:"):
        state = data.split(":", 1)[1]
        if user_id not in sessions or user_states.get(user_id) != state:
            answer_callback(callback_id, "مرحله معتبر نیست.")
            return
        answer_callback(callback_id)
        go_next(user_id)
        return

    if data == "more_photo":
        answer_callback(callback_id, "تصویر بعدی را بفرست.")
        return

    if data == "finish":
        if user_id not in sessions or user_states.get(user_id) != "photos":
            answer_callback(callback_id, "ثبت آگهی فعال نیست.")
            return
        answer_callback(callback_id, "در حال ارسال")
        submit_listing(user_id)
        return

    if data.startswith(("approve:", "reject:")):
        if user_id != ADMIN_ID:
            answer_callback(callback_id, "فقط مدیر اجازه دارد.")
            return

        action, listing_id_text = data.split(":", 1)
        try:
            listing_id = int(listing_id_text)
        except ValueError:
            answer_callback(callback_id, "شناسه نامعتبر است.")
            return

        result = (
            approve_listing(listing_id)
            if action == "approve"
            else reject_listing(listing_id)
        )
        answer_callback(callback_id, result)

        message = query.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")

        if chat_id and message_id:
            api("editMessageReplyMarkup", {
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": json.dumps({"inline_keyboard": []})
            })
        return

    answer_callback(callback_id, "دستور شناخته نشد.")


def process_update(update):
    global last_update_time
    last_update_time = int(time.time())

    if update.get("callback_query"):
        handle_callback(update["callback_query"])
        return

    message = update.get("message")
    if not message:
        return

    if message.get("text"):
        handle_text(message)
    elif message.get("photo") or message.get("location"):
        handle_media(message)


# ==================== دریافت پیام‌های تلگرام ====================

def polling_loop():
    global polling_started, bot_username

    api("deleteWebhook", {"drop_pending_updates": "false"})

    me = api("getMe")
    if me:
        bot_username = me.get("username")
        print(f"Telegram bot started: @{bot_username}", flush=True)
    else:
        print("Could not connect to Telegram API.", flush=True)

    polling_started = True
    offset = None

    while True:
        params = {"timeout": 30}
        if offset is not None:
            params["offset"] = offset

        updates = api("getUpdates", params, timeout=40)

        if updates is None:
            time.sleep(3)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            try:
                process_update(update)
            except Exception as exc:
                print(f"Update processing error: {exc}", flush=True)


def start_polling_once():
    global polling_started

    with polling_lock:
        existing = getattr(app, "_polling_thread", None)
        if existing and existing.is_alive():
            return

        thread = threading.Thread(
            target=polling_loop,
            name="telegram-polling",
            daemon=True
        )
        app._polling_thread = thread
        thread.start()


# ==================== شروع Web Service ====================

if __name__ == "__main__":
    start_polling_once()
    app.run(host="0.0.0.0", port=PORT)
