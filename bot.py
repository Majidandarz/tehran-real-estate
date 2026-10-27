import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "6245308636"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@tehranrealstate")
DATABASE_PATH = os.getenv("DATABASE_PATH", "real_estate.db")
PORT = int(os.getenv("PORT", "10000"))

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("tehran_real_estate_bot")

BACK = "بازگشت به منوی اصلی"

MAIN_MENU = [
    ["متقاضی خرید یا اجاره"],
    ["فروشنده یا موجر"],
    ["سرمایه‌گذاری ملکی و مشارکت در ساخت"],
    ["مشاور املاک"],
    ["پشتیبانی و ارتباط با مدیر"],
]

SUBMENUS = {
    "متقاضی خرید یا اجاره": [
        ["ثبت تقاضای خرید"],
        ["ثبت تقاضای اجاره"],
        [BACK],
    ],
    "فروشنده یا موجر": [
        ["ثبت آگهی فروش"],
        ["ثبت آگهی اجاره"],
        [BACK],
    ],
    "سرمایه‌گذاری ملکی و مشارکت در ساخت": [
        ["درخواست پیش خرید"],
        ["سازنده آماده مشارکت هستم"],
        ["مالک ملک برای مشارکت در ساخت هستم"],
        [BACK],
    ],
    "مشاور املاک": [
        ["ثبت آگهی ملک"],
        ["پیگیری مشتریان"],
        ["درخواست همکاری با مشاوران"],
        [BACK],
    ],
    "پشتیبانی و ارتباط با مدیر": [
        ["ارسال پیام به مدیر"],
        ["گزارش مشکل یا تخلف"],
        [BACK],
    ],
}

FORM_FIELDS = {
    "ثبت تقاضای خرید": [
        ("نوع ملک موردنظر را وارد کنید (مثلاً آپارتمان، زمین، ویلا):", "نوع ملک"),
        ("شهر و محدوده موردنظر را وارد کنید:", "شهر و محدوده"),
        ("بودجه یا بازه قیمت را وارد کنید:", "بودجه"),
        ("توضیحات تکمیلی را وارد کنید یا «ندارم» بنویسید:", "توضیحات"),
        ("شماره تماس برای پیگیری را وارد کنید:", "شماره تماس"),
    ],
    "ثبت تقاضای اجاره": [
        ("نوع ملک موردنظر را وارد کنید:", "نوع ملک"),
        ("شهر و محدوده موردنظر را وارد کنید:", "شهر و محدوده"),
        ("بودجه اجاره و ودیعه را وارد کنید:", "بودجه و ودیعه"),
        ("توضیحات تکمیلی را وارد کنید یا «ندارم» بنویسید:", "توضیحات"),
        ("شماره تماس برای پیگیری را وارد کنید:", "شماره تماس"),
    ],
    "ثبت آگهی فروش": [
        ("نوع ملک را وارد کنید:", "نوع ملک"),
        ("شهر و محدوده ملک را وارد کنید:", "شهر و محدوده"),
        ("متراژ ملک را وارد کنید:", "متراژ"),
        ("قیمت پیشنهادی را وارد کنید:", "قیمت"),
        ("توضیحات ملک را وارد کنید:", "توضیحات"),
        ("شماره تماس را وارد کنید:", "شماره تماس"),
    ],
    "ثبت آگهی اجاره": [
        ("نوع ملک را وارد کنید:", "نوع ملک"),
        ("شهر و محدوده ملک را وارد کنید:", "شهر و محدوده"),
        ("متراژ ملک را وارد کنید:", "متراژ"),
        ("مبلغ ودیعه را وارد کنید:", "ودیعه"),
        ("مبلغ اجاره ماهانه را وارد کنید:", "اجاره ماهانه"),
        ("توضیحات ملک را وارد کنید:", "توضیحات"),
        ("شماره تماس را وارد کنید:", "شماره تماس"),
    ],
    "درخواست پیش خرید": [
        ("نوع پروژه یا ملک موردنظر را وارد کنید:", "نوع پروژه"),
        ("شهر و محدوده موردنظر را وارد کنید:", "شهر و محدوده"),
        ("بودجه تقریبی را وارد کنید:", "بودجه"),
        ("زمان تحویل یا شرایط مدنظر را بنویسید:", "شرایط"),
        ("شماره تماس را وارد کنید:", "شماره تماس"),
    ],
    "سازنده آماده مشارکت هستم": [
        ("نام یا عنوان سازنده/شرکت را وارد کنید:", "نام سازنده"),
        ("شهر و محدوده فعالیت را وارد کنید:", "محدوده فعالیت"),
        ("نوع پروژه و توان اجرایی را توضیح دهید:", "توان اجرایی"),
        ("شرایط مشارکت مدنظر را بنویسید:", "شرایط مشارکت"),
        ("شماره تماس را وارد کنید:", "شماره تماس"),
    ],
    "مالک ملک برای مشارکت در ساخت هستم": [
        ("نوع ملک و مشخصات کلی آن را وارد کنید:", "مشخصات ملک"),
        ("شهر و محدوده ملک را وارد کنید:", "شهر و محدوده"),
        ("مساحت زمین و مشخصات سند را وارد کنید:", "مساحت و سند"),
        ("شرایط اولیه مشارکت را بنویسید:", "شرایط مشارکت"),
        ("شماره تماس را وارد کنید:", "شماره تماس"),
    ],
    "ثبت آگهی ملک": [
        ("نوع معامله و ملک را وارد کنید:", "نوع معامله و ملک"),
        ("شهر و محدوده را وارد کنید:", "شهر و محدوده"),
        ("قیمت یا شرایط مالی را وارد کنید:", "قیمت/شرایط"),
        ("توضیحات و مشخصات ملک را وارد کنید:", "توضیحات"),
        ("شماره تماس را وارد کنید:", "شماره تماس"),
    ],
    "پیگیری مشتریان": [
        ("نام مشتری یا کد پیگیری را وارد کنید:", "مشتری/کد پیگیری"),
        ("توضیح درخواست پیگیری را بنویسید:", "شرح پیگیری"),
        ("شماره تماس خود را وارد کنید:", "شماره تماس"),
    ],
    "درخواست همکاری با مشاوران": [
        ("نام مشاور یا آژانس را وارد کنید:", "نام مشاور/آژانس"),
        ("شهر و محدوده فعالیت را وارد کنید:", "محدوده فعالیت"),
        ("نوع همکاری مدنظر را توضیح دهید:", "نوع همکاری"),
        ("شماره تماس را وارد کنید:", "شماره تماس"),
    ],
    "ارسال پیام به مدیر": [
        ("پیام خود را برای مدیر بنویسید:", "پیام"),
        ("شماره تماس (در صورت تمایل) را وارد کنید یا «ندارم» بنویسید:", "شماره تماس"),
    ],
    "گزارش مشکل یا تخلف": [
        ("موضوع گزارش را بنویسید:", "موضوع"),
        ("شرح گزارش را بنویسید:", "شرح"),
        ("شماره تماس (در صورت تمایل) را وارد کنید یا «ندارم» بنویسید:", "شماره تماس"),
    ],
}

web_app = Flask(__name__)
runtime_state = {
    "status": "starting",
    "telegram_polling": False,
    "last_update_time": None,
}


def init_db():
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                category TEXT NOT NULL,
                data TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
            )
        """)
        conn.commit()


def keyboard_for(rows):
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="یکی از گزینه‌ها را انتخاب کنید",
    )


def main_keyboard():
    return keyboard_for(MAIN_MENU)


def menu_keyboard(menu_name):
    rows = SUBMENUS.get(menu_name, [[BACK]])
    if not any(BACK in row for row in rows):
        rows.append([BACK])
    return keyboard_for(rows)


async def send_main_menu(update, text="منوی اصلی املاک تهران:"):
    if update.message:
        await update.message.reply_text(text, reply_markup=main_keyboard())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await send_main_menu(
        update,
        "به سامانه املاک تهران خوش آمدید.\n"
        "از منوی پایین یکی از گزینه‌ها را انتخاب کنید:",
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await send_main_menu(update, "عملیات لغو شد. منوی اصلی:")


def save_submission(user_id, username, category, answers):
    data_text = "\n".join(
        f"{key}: {value}" for key, value in answers.items()
    )
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO submissions
            (created_at, user_id, username, category, data, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                user_id,
                username,
                category,
                data_text,
            ),
        )
        conn.commit()
        return cursor.lastrowid, data_text


async def begin_form(update, context, form_name):
    fields = FORM_FIELDS[form_name]
    context.user_data["form"] = {
        "name": form_name,
        "fields": fields,
        "index": 0,
        "answers": {},
    }
    await update.message.reply_text(
        fields[0][0] + "\n\nبرای خروج، «بازگشت به منوی اصلی» را بزنید.",
        reply_markup=keyboard_for([[BACK]]),
    )


async def notify_admin(context, submission_id, update, form_name, data_text):
    user = update.effective_user
    username = f"@{user.username}" if user and user.username else "بدون نام کاربری"
    message = (
        f"درخواست جدید #{submission_id}\n"
        f"بخش: {form_name}\n"
        f"کاربر: {user.full_name if user else 'نامشخص'}\n"
        f"شناسه کاربر: {user.id if user else 'نامشخص'}\n"
        f"نام کاربری: {username}\n\n"
        f"{data_text}\n\n"
        f"تأیید: /approve_{submission_id}\n"
        f"رد: /reject_{submission_id}"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=message)
    except Exception:
        logger.exception("Could not notify admin for submission %s", submission_id)


async def handle_form_answer(update, context):
    form = context.user_data.get("form")
    if not form:
        return False

    text = (update.message.text or "").strip()

    if text == BACK:
        context.user_data.clear()
        await send_main_menu(update)
        return True

    key = form["fields"][form["index"]][1]
    form["answers"][key] = text
    form["index"] += 1

    if form["index"] < len(form["fields"]):
        prompt = form["fields"][form["index"]][0]
        await update.message.reply_text(
            prompt + "\n\nبرای خروج، «بازگشت به منوی اصلی» را بزنید.",
            reply_markup=keyboard_for([[BACK]]),
        )
        return True

    user = update.effective_user
    submission_id, data_text = save_submission(
        user_id=user.id,
        username=user.username,
        category=form["name"],
        answers=form["answers"],
    )
    form_name = form["name"]
    context.user_data.clear()

    await notify_admin(context, submission_id, update, form_name, data_text)
    await update.message.reply_text(
        f"اطلاعات شما با کد پیگیری {submission_id} ثبت شد و برای بررسی به مدیر ارسال شد.",
        reply_markup=main_keyboard(),
    )
    return True


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    runtime_state["last_update_time"] = int(
        datetime.now(timezone.utc).timestamp()
    )

    if text == BACK:
        context.user_data.clear()
        await send_main_menu(update)
        return

    # ادامه فرم ثبت اطلاعات
    if await handle_form_answer(update, context):
        return

    # نمایش زیرمنو
    if text in SUBMENUS:
        context.user_data.clear()
        await update.message.reply_text(
            f"بخش «{text}» را انتخاب کردید:",
            reply_markup=menu_keyboard(text),
        )
        return

    # شروع فرم
    if text in FORM_FIELDS:
        await begin_form(update, context, text)
        return

    await update.message.reply_text(
        "لطفاً یکی از گزینه‌های منو را انتخاب کنید یا /start را بزنید.",
        reply_markup=main_keyboard(),
    )


async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != ADMIN_ID:
        await update.message.reply_text("این دستور فقط برای مدیر اصلی فعال است.")
        return

    command = update.message.text.strip()
    is_approve = command.startswith("/approve_")
    prefix = "/approve_" if is_approve else "/reject_"

    try:
        submission_id = int(command[len(prefix):].split("@")[0])
    except ValueError:
        await update.message.reply_text("کد پیگیری معتبر نیست.")
        return

    new_status = "approved" if is_approve else "rejected"

    with sqlite3.connect(DATABASE_PATH) as conn:
        row = conn.execute(
            "SELECT category, data, user_id FROM submissions WHERE id = ?",
            (submission_id,),
        ).fetchone()

        if not row:
            await update.message.reply_text("درخواستی با این کد پیدا نشد.")
            return

        conn.execute(
            "UPDATE submissions SET status = ? WHERE id = ?",
            (new_status, submission_id),
        )
        conn.commit()

    category, data_text, owner_id = row

    if is_approve:
        try:
            await context.bot.send_message(
                chat_id=owner_id,
                text=f"درخواست شما با کد {submission_id} تأیید شد.",
            )
        except Exception:
            logger.exception("Could not notify submitter")

        await update.message.reply_text(f"درخواست #{submission_id} تأیید شد.")

        if category in {"ثبت آگهی فروش", "ثبت آگهی اجاره", "ثبت آگهی ملک"}:
            try:
                await context.bot.send_message(
                    chat_id=CHANNEL_USERNAME,
                    text=f"آگهی تأییدشده | کد {submission_id}\n\n{data_text}",
                )
            except Exception:
                logger.exception("Could not publish listing to channel")
                await update.message.reply_text(
                    "انتشار در کانال انجام نشد؛ دسترسی ربات به کانال را بررسی کنید."
                )
    else:
        try:
            await context.bot.send_message(
                chat_id=owner_id,
                text=f"درخواست شما با کد {submission_id} رد شد. برای پیگیری با مدیر تماس بگیرید.",
            )
        except Exception:
            logger.exception("Could not notify submitter")

        await update.message.reply_text(f"درخواست #{submission_id} رد شد.")


@web_app.get("/")
def home():
    return jsonify({"service": "tehran-real-estate-bot", **runtime_state})


@web_app.get("/health")
def health():
    return jsonify({"status": "ok", **runtime_state})


def run_web_server():
    web_app.run(host="0.0.0.0", port=PORT, use_reloader=False)


def main():
    if not BOT_TOKEN:
        raise RuntimeError("متغیر BOT_TOKEN در تنظیمات Render وارد نشده است.")

    init_db()
    threading.Thread(target=run_web_server, daemon=True).start()

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(
        MessageHandler(
            filters.Regex(r"^/approve_\d+(?:@\w+)?$"),
            admin_decision,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(r"^/reject_\d+(?:@\w+)?$"),
            admin_decision,
        )
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    runtime_state["status"] = "running"
    runtime_state["telegram_polling"] = True
    logger.info("Starting Telegram polling.")
    application.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
