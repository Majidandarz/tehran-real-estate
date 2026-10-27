
import os
import json
import time
import html
import sqlite3
import urllib.parse
import urllib.request
import urllib.error

# ==================== تنظیمات ====================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = 6245308636
CHANNEL_ID = "@tehranrealstate"
DATABASE_PATH = os.getenv("DATABASE_PATH", "realestate.db")

if not BOT_TOKEN:
    raise RuntimeError("متغیر BOT_TOKEN در تنظیمات Render تنظیم نشده است.")

API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# ==================== پایگاه داده ====================

db = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
db.row_factory = sqlite3.Row

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

# ==================== ارتباط با تلگرام ====================

def api(method, data=None, timeout=60):
    data = data or {}
    encoded = urllib.parse.urlencode(data).encode()
    request = urllib.request.Request(API + method, data=encoded)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode())
    except Exception as exc:
        print(f"Telegram API error ({method}): {exc}")
        return None

    if not result.get("ok"):
        print(f"Telegram API returned error ({method}): {result}")
        return None

    return result.get("result")


def send_message(chat_id, text, keyboard=None, parse_mode="HTML"):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
    return api("sendMessage", payload)


def send_photo(chat_id, photo_id, caption, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "photo": photo_id,
        "caption": caption[:1024],
        "parse_mode": "HTML"
    }
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
    return api("sendPhoto", payload)


def answer_callback(callback_id, text=""):
    api("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": text
    })


def edit_message(chat_id, message_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
    return api("editMessageText", payload)


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


def choices_keyboard(options, back=True):
    rows = [[button(label, f"pick:{value}")]
            for label, value in options]
    if back:
        rows.append([button("قبلی", "back")])
    rows.append([button("لغو", "cancel")])
    return {"inline_keyboard": rows}


def navigation_keyboard():
    return {
        "inline_keyboard": [
            [button("قبلی", "back"), button("لغو", "cancel")]
        ]
    }


# ==================== مراحل ثبت آگهی ====================

STEPS = [
    "intent",
    "property_type",
    "city",
    "district",
    "price",
    "description",
    "contact",
    "location",
    "photos"
]

STEP_TITLES = {
    "intent": "نوع معامله",
    "property_type": "نوع ملک",
    "city": "شهر",
    "district": "محدوده",
    "price": "قیمت",
    "description": "توضیحات",
    "contact": "اطلاعات تماس",
    "location": "موقعیت مکانی",
    "photos": "تصاویر"
}

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
        ("سایر محدوده‌ها / نام محله", "other")
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
    data = sessions.get(user_id)

    if not data or state not in STEPS:
        send_message(user_id, "برای شروع ثبت آگهی، از منوی اصلی استفاده کن.",
                     menu_keyboard())
        return

    prompts = {
        "intent": "چه نوع معامله‌ای مدنظرت است؟",
        "property_type": "نوع ملک را انتخاب کن:",
        "city": "ملک در کدام شهر قرار دارد؟",
        "district": "محدوده یا جهت شهر را انتخاب کن:",
        "price": "قیمت یا مبلغ موردنظر را وارد کن.\nمثال: ۱۲ میلیارد تومان",
        "description": "توضیحات ملک را بنویس؛ متراژ، تعداد اتاق، امکانات و شرایط معامله را ذکر کن.",
        "contact": "شماره تماس یا روش تماس موردنظر را وارد کن.",
        "location": "اگر می‌خواهی، موقعیت مکانی ملک را با دکمه 📎 و بخش Location بفرست. اگر نمی‌خواهی، «رد کردن» را بزن.",
        "photos": "تصاویر ملک را ارسال کن. پس از ارسال تصاویر، «پایان تصاویر» را بزن. اگر تصویر نداری، رد کن."
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
    current = user_states.get(user_id)
    if current not in STEPS:
        return
    index = STEPS.index(current)
    if index + 1 >= len(STEPS):
        submit_listing(user_id)
        return
    user_states[user_id] = STEPS[index + 1]
    show_step(user_id)


def go_back(user_id):
    current = user_states.get(user_id)
    if current not in STEPS:
        send_message(user_id, "منوی اصلی:", menu_keyboard())
        return
    index = STEPS.index(current)
    if index == 0:
        send_message(user_id, "منوی اصلی:", menu_keyboard())
        return
    user_states[user_id] = STEPS[index - 1]
    show_step(user_id)


# ==================== ثبت و بررسی آگهی ====================

def listing_text(listing_id, data, include_contact=True):
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
        html.escape(data.get("description", "-"))
    ]

    if include_contact:
        lines.extend([
            "",
            f"تماس: {html.escape(data.get('contact', '-'))}"
        ])

    if data.get("location"):
        loc = data["location"]
        if "latitude" in loc and "longitude" in loc:
            lines.extend([
                "",
                f"موقعیت: {loc['latitude']}, {loc['longitude']}"
            ])

    return "\n".join(lines)


def submit_listing(user_id):
    data = sessions.get(user_id)
    if not data:
        send_message(user_id, "اطلاعات ثبت آگهی پیدا نشد. دوباره شروع کن.",
                     menu_keyboard())
        return

    required = [
        "intent", "property_type", "city",
        "district", "price", "description", "contact"
    ]
    missing = [key for key in required if not data.get(key)]
    if missing:
        user_states[user_id] = missing[0]
        send_message(user_id, "چند بخش هنوز تکمیل نشده است. ادامه بده.")
        show_step(user_id)
        return

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
    review_keyboard = {
        "inline_keyboard": [[
            button("تأیید و انتشار", f"approve:{listing_id}"),
            button("رد آگهی", f"reject:{listing_id}")
        ]]
    }

    admin_result = None
    if data.get("photos"):
        admin_result = send_photo(
            ADMIN_ID, data["photos"][0], caption, review_keyboard
        )
    else:
        admin_result = send_message(
            ADMIN_ID, caption, review_keyboard
        )

    if not admin_result:
        send_message(
            user_id,
            f"آگهی شماره {listing_id} ذخیره شد، اما ارسال آن برای مدیر ناموفق بود. لطفاً بعداً پیگیری کن.",
            menu_keyboard()
        )
    else:
        send_message(
            user_id,
            f"آگهی شما با شماره <b>{listing_id}</b> برای بررسی مدیر ارسال شد. پس از بررسی نتیجه اعلام می‌شود.",
            menu_keyboard()
        )

    sessions.pop(user_id, None)
    user_states.pop(user_id, None)


def approve_listing(listing_id, callback_message):
    row = db.execute(
        "SELECT * FROM listings WHERE id = ?", (listing_id,)
    ).fetchone()

    if not row:
        return "آگهی پیدا نشد."

    if row["status"] != "pending":
        return "این آگهی قبلاً بررسی شده است."

    data = json.loads(row["data"])
    caption = listing_text(listing_id, data)

    if data.get("photos"):
        published = send_photo(
            CHANNEL_ID, data["photos"][0], caption
        )
    else:
        published = send_message(CHANNEL_ID, caption)

    if not published:
        return "انتشار ناموفق بود. بررسی کن ربات در کانال مدیر باشد."

    db.execute(
        "UPDATE listings SET status = 'published' WHERE id = ?",
        (listing_id,)
    )
    db.commit()

    send_message(
        row["user_id"],
        f"آگهی شماره {listing_id} تأیید و در کانال منتشر شد."
    )
    return "آگهی تأیید و منتشر شد."


def reject_listing(listing_id):
    row = db.execute(
        "SELECT * FROM listings WHERE id = ?", (listing_id,)
    ).fetchone()

    if not row:
        return "آگهی پیدا نشد."

    if row["status"] != "pending":
        return "این آگهی قبلاً بررسی شده است."

    db.execute(
        "UPDATE listings SET status = 'rejected' WHERE id = ?",
        (listing_id,)
    )
    db.commit()

    send_message(
        row["user_id"],
        f"آگهی شماره {listing_id} تأیید نشد. برای اصلاح، دوباره آگهی ثبت کن."
    )
    return "آگهی رد شد."


# ==================== پردازش پیام‌ها ====================

def handle_text(message):
    user_id = message["from"]["id"]
    username = message["from"].get("username", "")
    text = message.get("text", "").strip()

    if text in ("/start", "/menu"):
        sessions.pop(user_id, None)
        user_states.pop(user_id, None)
        send_message(
            user_id,
            "به سامانه املاک خوش آمدی.\nاز منوی زیر استفاده کن:",
            menu_keyboard()
        )
        return

    if text == "/myid":
        send_message(user_id, f"شناسه عددی شما: <code>{user_id}</code>")
        return

    if user_id not in sessions:
        send_message(user_id, "از منوی اصلی یک گزینه انتخاب کن.",
                     menu_keyboard())
        return

    state = user_states.get(user_id)
    data = sessions[user_id]

    if state in ("city", "district") and text:
        data[state] = text
        go_next(user_id)
        return

    if state == "price":
        data["price"] = text
        go_next(user_id)
        return

    if state == "description":
        data["description"] = text
        go_next(user_id)
        return

    if state == "contact":
        data["contact"] = text
        go_next(user_id)
        return

    if state == "photos":
        if text in ("رد کردن", "بدون تصویر"):
            go_next(user_id)
        else:
            send_message(
                user_id,
                "در این مرحله تصویر بفرست یا «پایان تصاویر» را انتخاب کن.",
                {
                    "inline_keyboard": [
                        [button("پایان تصاویر", "finish")],
                        [button("قبلی", "back"), button("لغو", "cancel")]
                    ]
                }
            )
        return

    send_message(user_id, "از دکمه‌های نمایش‌داده‌شده استفاده کن.")


def handle_media(message):
    user_id = message["from"]["id"]
    data = sessions.get(user_id)
    state = user_states.get(user_id)

    if not data:
        return

    if state == "location" and message.get("location"):
        loc = message["location"]
        data["location"] = {
            "latitude": loc["latitude"],
            "longitude": loc["longitude"]
        }
        go_next(user_id)
        return

    if state == "photos" and message.get("photo"):
        photo_id = message["photo"][-1]["file_id"]
        data["photos"].append(photo_id)
        send_message(
            user_id,
            f"تصویر دریافت شد. تعداد تصاویر: {len(data['photos'])}",
            {
                "inline_keyboard": [
                    [button("ارسال تصویر دیگر", "more_photo")],
                    [button("پایان تصاویر", "finish")],
                    [button("قبلی", "back"), button("لغو", "cancel")]
                ]
            }
        )
        return

    send_message(user_id, "این فایل در مرحله فعلی قابل استفاده نیست.")


# ==================== پردازش دکمه‌ها ====================

def handle_callback(query):
    callback_id = query["id"]
    user_id = query["from"]["id"]
    data = query.get("data", "")
    message = query.get("message", {})
    chat_id = message.get("chat", {}).get("id", user_id)
    message_id = message.get("message_id")

    if data == "cancel":
        sessions.pop(user_id, None)
        user_states.pop(user_id, None)
        answer_callback(callback_id, "عملیات لغو شد")
        send_message(user_id, "به منوی اصلی برگشتی.", menu_keyboard())
        return

    if data == "help":
        answer_callback(callback_id)
        send_message(
            user_id,
            "ثبت آگهی را آغاز کن و مراحل را به‌ترتیب تکمیل کن. "
            "آگهی‌ها پیش از انتشار توسط مدیر بررسی می‌شوند.",
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

        value = data.split(":", 1)[1]
        state = user_states.get(user_id)

        if state not in OPTIONS:
            answer_callback(callback_id, "این انتخاب در مرحله فعلی معتبر نیست.")
            return

        allowed_values = {v for _, v in OPTIONS[state]}
        if value not in allowed_values:
            answer_callback(callback_id, "گزینه نامعتبر است.")
            return

        if value == "other" and state == "city":
            user_states[user_id] = "city"
            answer_callback(callback_id)
            send_message(user_id, "نام شهر را به‌صورت متنی وارد کن.",
                         navigation_keyboard())
            return

        if value == "other" and state == "district":
            user_states[user_id] = "district"
            answer_callback(callback_id)
            send_message(user_id, "نام محله یا محدوده را وارد کن.",
                         navigation_keyboard())
            return

        sessions[user_id][state] = value
        answer_callback(callback_id)
        go_next(user_id)
        return

    if data.startswith("skip:"):
        if user_id not in sessions:
            answer_callback(callback_id, "ثبت آگهی فعال نیست.")
            return
        state = data.split(":", 1)[1]
        if user_states.get(user_id) != state:
            answer_callback(callback_id, "این گزینه برای مرحله فعلی نیست.")
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
        answer_callback(callback_id, "در حال ارسال برای بررسی")
        submit_listing(user_id)
        return

    if data.startswith("approve:") or data.startswith("reject:"):
        if user_id != ADMIN_ID:
            answer_callback(callback_id, "این دسترسی فقط برای مدیر است.")
            return

        action, listing_id_text = data.split(":", 1)
        try:
            listing_id = int(listing_id_text)
        except ValueError:
            answer_callback(callback_id, "شناسه آگهی نامعتبر است.")
            return

        if action == "approve":
            result = approve_listing(listing_id, message)
        else:
            result = reject_listing(listing_id)

        answer_callback(callback_id, result[:180])

        if chat_id and message_id:
            try:
                api("editMessageReplyMarkup", {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": json.dumps(
                        {"inline_keyboard": []}
                    )
                })
            except Exception:
                pass
        return

    answer_callback(callback_id, "دستور شناخته نشد.")


# ==================== اجرای ربات ====================

def process_update(update):
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
    else:
        user_id = message.get("from", {}).get("id")
        if user_id:
            send_message(user_id, "لطفاً متن، تصویر یا موقعیت مکانی ارسال کن.")


def main():
    # حذف webhook قبلی برای جلوگیری از تداخل با polling
    api("deleteWebhook", {"drop_pending_updates": "false"})

    me = api("getMe")
    if me:
        print(f"Bot started: @{me.get('username', 'unknown')}")

    offset = None

    while True:
        try:
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
                    print(f"Update error: {exc}")

        except KeyboardInterrupt:
            break
        except Exception as exc:
            print(f"Polling error: {exc}")
            time.sleep(3)


if __name__ == "__main__":
    main()
