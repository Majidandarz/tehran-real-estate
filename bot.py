import os
import json
import time
import sqlite3
import threading
import urllib.parse
import urllib.request
from flask import Flask, jsonify
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = 6245308636
CHANNEL_ID = "@tehranrealstate"
PORT = int(os.getenv("PORT", "10000"))
DB_PATH = os.getenv("DATABASE_PATH", "realestate.db")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN در تنظیمات Render تنظیم نشده است.")

app = Flask(__name__)
bot_app = None

db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.row_factory = sqlite3.Row
lock = threading.Lock()

with lock:
    db.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            data TEXT,
            status TEXT DEFAULT 'pending',
            created_at INTEGER
        )
    """)
    db.commit()

MAIN_MENU = [
    ["متقاضی خرید یا اجاره"],
    ["فروشنده یا موجر"],
    ["سرمایه‌گذاری ملکی و مشارکت در ساخت"],
    ["مشاور املاک"],
    ["پشتیبانی و ارتباط با مدیر"]
]

SUBMENUS = {
    "متقاضی خرید یا اجاره": [
        ["ثبت درخواست خرید یا اجاره"],
        ["جست‌وجوی ملک"],
        ["درخواست بازدید"],
        ["بازگشت به منوی اصلی"]
    ],
    "فروشنده یا موجر": [
        ["ثبت آگهی"],
        ["راهنمای ثبت آگهی"],
        ["پیگیری آگهی"],
        ["بازگشت به منوی اصلی"]
    ],
    "سرمایه‌گذاری ملکی و مشارکت در ساخت": [
        ["فرصت‌های سرمایه‌گذاری"],
        ["درخواست مشارکت در ساخت"],
        ["بازگشت به منوی اصلی"]
    ],
    "مشاور املاک": [
        ["ثبت آگهی ملک"],
        ["پیگیری مشتریان"],
        ["همکاری با مشاوران"],
        ["بازگشت به منوی اصلی"]
    ],
    "پشتیبانی و ارتباط با مدیر": [
        ["ارسال پیام به مدیر"],
        ["گزارش تخلف"],
        ["بازگشت به منوی اصلی"]
    ]
}

def keyboard(rows, resize=True):
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=resize,
        one_time_keyboard=False,
        input_field_placeholder="یک گزینه را انتخاب کن"
    )

def main_keyboard():
    return keyboard(MAIN_MENU)

def submenu_keyboard(section):
    return keyboard(SUBMENUS[section])

def api(method, data):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    request = urllib.request.Request(
        url, data=urllib.parse.urlencode(data).encode()
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode())

@app.get("/")
def home():
    return jsonify({"service": "Tehran Real Estate Bot", "status": "running"})

@app.get("/health")
def health():
    return jsonify({"status": "ok", "telegram_polling": True})

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "به سامانه املاک تهران خوش آمدی.\nبخش موردنظرت را انتخاب کن:",
        reply_markup=main_keyboard()
    )

async def show_listing_step(update, context):
    step = context.user_data.get("listing_step", 0)
    prompts = [
        ("نوع معامله را انتخاب کن:", [
            ["فروش", "خرید"], ["اجاره", "رهن کامل"],
            ["سرمایه‌گذاری"], ["لغو عملیات"]
        ]),
        ("نوع ملک را انتخاب کن:", [
            ["آپارتمان", "خانه و ویلا"], ["زمین", "مغازه و واحد تجاری"],
            ["دفتر اداری", "باغ"], ["سایر"], ["لغو عملیات"]
        ]),
        ("شهر ملک را بنویس:", None),
        ("محله یا محدوده ملک را بنویس:", None),
        ("قیمت یا مبلغ موردنظر را بنویس:", None),
        ("توضیحات ملک را بنویس:", None),
        ("شماره تماس یا روش تماس را بنویس:", None),
    ]
    if step >= len(prompts):
        return
    prompt, choices = prompts[step]
    await update.message.reply_text(
        prompt,
        reply_markup=keyboard(choices) if choices else keyboard([
            ["قبلی"], ["لغو عملیات"]
        ])
    )

async def begin_listing(update, context):
    context.user_data["listing_step"] = 0
    context.user_data["listing"] = {}
    await show_listing_step(update, context)

async def finish_listing(update, context):
    data = context.user_data["listing"]
    required = [
        "نوع معامله", "نوع ملک", "شهر", "محدوده",
        "قیمت", "توضیحات", "تماس"
    ]
    if not all(data.get(k) for k in required):
        await update.message.reply_text("اطلاعات آگهی کامل نیست.")
        return

    user = update.effective_user
    with lock:
        cur = db.execute(
            """INSERT INTO listings
            (user_id, username, data, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)""",
            (user.id, user.username or "",
             json.dumps(data, ensure_ascii=False), int(time.time()))
        )
        db.commit()
        listing_id = cur.lastrowid

    report = (
        f"آگهی شماره {listing_id}\n"
        f"کاربر: {user.id}\n\n" +
        "\n".join(f"{k}: {v}" for k, v in data.items()) +
        "\n\nبرای بررسی مدیر:\n"
        f"/approve_{listing_id}\n/reject_{listing_id}"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=report)
        await update.message.reply_text(
            f"آگهی شماره {listing_id} برای بررسی مدیر ارسال شد.",
            reply_markup=main_keyboard()
        )
    except Exception:
        await update.message.reply_text(
            f"آگهی ذخیره شد، اما ارسال به مدیر ناموفق بود. شماره آگهی: {listing_id}",
            reply_markup=main_keyboard()
        )

    context.user_data.clear()

async def review(update, context, approved):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("این دستور فقط برای مدیر اصلی است.")
        return

    try:
        listing_id = int(update.message.text.split("_", 1)[1])
    except (ValueError, IndexError):
        await update.message.reply_text("شماره آگهی معتبر نیست.")
        return

    with lock:
        row = db.execute(
            "SELECT * FROM listings WHERE id = ?", (listing_id,)
        ).fetchone()

    if not row:
        await update.message.reply_text("آگهی پیدا نشد.")
        return
    if row["status"] != "pending":
        await update.message.reply_text("این آگهی قبلاً بررسی شده است.")
        return

    if approved:
        data = json.loads(row["data"])
        public_text = (
            f"🏠 آگهی املاک شماره {listing_id}\n\n" +
            "\n".join(
                f"{k}: {v}" for k, v in data.items()
                if k != "تماس"
            )
        )
        try:
            await context.bot.send_message(CHANNEL_ID, public_text)
        except Exception as exc:
            await update.message.reply_text(
                f"انتشار ناموفق بود؛ دسترسی ربات به کانال را بررسی کن.\n{exc}"
            )
            return
        status = "published"
        answer = "آگهی تأیید و منتشر شد."
    else:
        status = "rejected"
        answer = "آگهی رد شد."

    with lock:
        db.execute(
            "UPDATE listings SET status=? WHERE id=?",
            (status, listing_id)
        )
        db.commit()

    await update.message.reply_text(answer)
    try:
        await context.bot.send_message(
            row["user_id"],
            f"وضعیت آگهی شماره {listing_id}: {answer}"
        )
    except Exception:
        pass

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        return

    if text == "لغو عملیات":
        context.user_data.clear()
        await update.message.reply_text(
            "عملیات لغو شد.", reply_markup=main_keyboard()
        )
        return

    if text == "بازگشت به منوی اصلی":
        context.user_data.clear()
        await update.message.reply_text(
            "منوی اصلی:", reply_markup=main_keyboard()
        )
        return

    if text in SUBMENUS:
        context.user_data.clear()
        await update.message.reply_text(
            text, reply_markup=submenu_keyboard(text)
        )
        return

    if text in ("ثبت آگهی", "ثبت آگهی ملک"):
        await begin_listing(update, context)
        return

    if text == "راهنمای ثبت آگهی":
        await update.message.reply_text(
            "گزینه ثبت آگهی را انتخاب کن و اطلاعات را مرحله‌به‌مرحله وارد کن.",
            reply_markup=submenu_keyboard("فروشنده یا موجر")
        )
        return

    if text.startswith("/approve_"):
        await review(update, context, True)
        return
    if text.startswith("/reject_"):
        await review(update, context, False)
        return

    if "listing_step" in context.user_data:
        step = context.user_data["listing_step"]
        keys = [
            "نوع معامله", "نوع ملک", "شهر", "محدوده",
            "قیمت", "توضیحات", "تماس"
        ]
        context.user_data["listing"][keys[step]] = text
        step += 1
        context.user_data["listing_step"] = step

        if step >= len(keys):
            await finish_listing(update, context)
        else:
            await show_listing_step(update, context)
        return

    messages = {
        "ثبت درخواست خرید یا اجاره": "ثبت درخواست در مرحله بعد تکمیل می‌شود.",
        "جست‌وجوی ملک": "جست‌وجوی ملک هنوز پیاده‌سازی نشده است.",
        "درخواست بازدید": "ثبت درخواست بازدید هنوز پیاده‌سازی نشده است.",
        "پیگیری آگهی": "برای پیگیری، شماره آگهی را برای پشتیبانی بفرست.",
        "فرصت‌های سرمایه‌گذاری": "فهرست فرصت‌های سرمایه‌گذاری هنوز آماده نیست.",
        "درخواست مشارکت در ساخت": "این بخش هنوز پیاده‌سازی نشده است.",
        "پیگیری مشتریان": "این بخش هنوز پیاده‌سازی نشده است.",
        "همکاری با مشاوران": "این بخش هنوز پیاده‌سازی نشده است.",
        "ارسال پیام به مدیر": "برای ارتباط با مدیر به @AtlasPrime021 پیام بده.",
        "گزارش تخلف": "برای گزارش تخلف به @AtlasPrime021 پیام بده."
    }
    await update.message.reply_text(
        messages.get(text, "از گزینه‌های منو استفاده کن."),
        reply_markup=main_keyboard()
    )

def main():
    global bot_app
    bot_app = Application.builder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("menu", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    bot_app.add_handler(MessageHandler(filters.COMMAND, handle_text))

    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=PORT),
        daemon=True
    ).start()

    bot_app.run_polling(drop_pending_updates=False)

if __name__ == "__main__":
    main()
