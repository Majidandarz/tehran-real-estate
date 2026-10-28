import os
import json
import sqlite3
import logging
import asyncio
import requests
from datetime import datetime
from html import escape
from threading import Thread

from flask import Flask
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ==================== تنظیمات ====================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "6245308636"))
DB_PATH = os.getenv("DB_PATH", "realestate.db")
GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY", "").strip()

CHANNELS = {
    "fa": "@tehranrealstate",
    "en": "@tehranrealstate_eng",
    "az": "@tehranrealstate_az",
    "tr": "@tehranrealstate_tur",
    "ar": "@tehranrealstate_ara",
}

LANG_NAMES = {
    "fa": "🇮🇷 فارسی",
    "en": "🇬🇧 English",
    "az": "🇦🇿 Azərbaycan dili",
    "tr": "🇹🇷 Türkçe",
    "ar": "🇸🇦 العربية",
}

LANG_LABELS = {
    "fa": "فارسی",
    "en": "English",
    "az": "Azərbaycan dili",
    "tr": "Türkçe",
    "ar": "العربية",
}

LANGUAGE_KEYBOARD = [
    [LANG_NAMES["fa"], LANG_NAMES["en"]],
    [LANG_NAMES["az"], LANG_NAMES["tr"]],
    [LANG_NAMES["ar"]],
]

WELCOME_FA = """🏡✨ به گروه بزرگ مشاورین املاک تهران خوش آمدید! ✨🏡

🌟 مجموعه مشاورین املاک تهران با بیش از ۲۰ سال سابقه فعالیت، گسترده‌ترین شبکه اطلاعات ملکی در ایران و بیش از ۱۰۰۰ مشاور فعال در سراسر کشور، در کنار شماست.

🤝 هدف پرسنل و مدیریت مجموعه، جلب رضایت شما مشتریان عزیز و ارائه خدماتی شایسته، مطمئن و حرفه‌ای است.

🌹 امیدواریم تجربه‌ای رضایت‌بخش و همکاری ارزشمندی را در کنار ما داشته باشید.

💠 املاک تهران؛ همراه شما در مسیر انتخابی مطمئن. 💠"""

WELCOME = {
    "fa": WELCOME_FA,
    "en": """🏡✨ Welcome to Tehran Real Estate! ✨🏡

🌟 With over 20 years of experience, an extensive property information network in Iran, and more than 1,000 active consultants nationwide, we are here to help you.

🤝 Our goal is to provide reliable, professional services and earn your satisfaction.

🌹 We hope you enjoy a valuable and successful experience with us.

💠 Tehran Real Estate — your partner in making confident property decisions. 💠""",
    "az": """🏡✨ Tehran Daşınmaz Əmlak qrupuna xoş gəlmisiniz! ✨🏡

🌟 20 ildən artıq təcrübəmiz və ölkə üzrə 1.000-dən çox fəal məsləhətçimizlə sizə xidmət göstəririk.

🤝 Məqsədimiz etibarlı və peşəkar xidmət göstərməkdir.

🌹 Sizin üçün uğurlu və məmnunedici əməkdaşlıq arzulayırıq.

💠 Tehran Daşınmaz Əmlak — düzgün seçim yolunda tərəfdaşınız. 💠""",
    "tr": """🏡✨ Tahran Gayrimenkul grubuna hoş geldiniz! ✨🏡

🌟 20 yılı aşkın deneyimimiz ve ülke genelinde 1.000'den fazla aktif danışmanımızla hizmetinizdeyiz.

🤝 Amacımız güvenilir ve profesyonel hizmet sunmaktır.

🌹 Sizin için başarılı ve memnuniyet verici bir iş birliği dileriz.

💠 Tahran Gayrimenkul — doğru seçim yolunda yanınızda. 💠""",
    "ar": """🏡✨ أهلاً بكم في مجموعة عقارات طهران! ✨🏡

🌟 بخبرة تزيد عن 20 عاماً وشبكة واسعة تضم أكثر من 1,000 مستشار عقاري نشط في أنحاء البلاد، نحن هنا لخدمتكم.

🤝 هدفنا تقديم خدمات موثوقة واحترافية وتحقيق رضاكم.

🌹 نتمنى لكم تجربة ناجحة وتعاوناً مثمراً.

💠 عقارات طهران — شريككم لاختيار عقاري موثوق. 💠""",
}

MAIN_MENU = {
    "fa": [
        ["🏠 ثبت آگهی فروش", "🔑 ثبت آگهی اجاره"],
        ["🔎 درخواست خرید", "🏘 درخواست اجاره"],
        ["🤝 همکاری مشاوران", "🏗 سازنده و پروژه"],
        ["📋 آگهی‌های من", "📨 درخواست‌های من"],
        ["🆘 پشتیبانی", "🌐 تغییر زبان"],
    ],
    "en": [
        ["🏠 Sell Property", "🔑 Rent Property"],
        ["🔎 Buy Request", "🏘 Rent Request"],
        ["🤝 Broker Cooperation", "🏗 Builder / Project"],
        ["📋 My Listings", "📨 My Requests"],
        ["🆘 Support", "🌐 Change Language"],
    ],
    "az": [
        ["🏠 Satış elanı", "🔑 Kirayə elanı"],
        ["🔎 Alış sorğusu", "🏘 Kirayə sorğusu"],
        ["🤝 Əməkdaşlıq", "🏗 Tikinti layihəsi"],
        ["📋 Elanlarım", "📨 Sorğularım"],
        ["🆘 Dəstək", "🌐 Dil"],
    ],
    "tr": [
        ["🏠 Satılık İlan", "🔑 Kiralık İlan"],
        ["🔎 Satın Alma Talebi", "🏘 Kiralama Talebi"],
        ["🤝 Danışman İş Birliği", "🏗 İnşaat Projesi"],
        ["📋 İlanlarım", "📨 Taleplerim"],
        ["🆘 Destek", "🌐 Dil Değiştir"],
    ],
    "ar": [
        ["🏠 إعلان بيع", "🔑 إعلان إيجار"],
        ["🔎 طلب شراء", "🏘 طلب إيجار"],
        ["🤝 تعاون الوسطاء", "🏗 مشروع بناء"],
        ["📋 إعلاناتي", "📨 طلباتي"],
        ["🆘 الدعم", "🌐 تغيير اللغة"],
    ],
}

FIELD_LABELS = {
    "fa": {
        "kind": "نوع درخواست",
        "city": "شهر و منطقه",
        "property_type": "نوع ملک",
        "area": "متراژ",
        "rooms": "تعداد اتاق",
        "price": "قیمت یا بودجه",
        "details": "توضیحات",
        "contact": "شماره تماس",
    },
    "en": {
        "kind": "Request type",
        "city": "City and area",
        "property_type": "Property type",
        "area": "Area",
        "rooms": "Rooms",
        "price": "Price or budget",
        "details": "Details",
        "contact": "Contact number",
    },
    "az": {
        "kind": "Sorğunun növü",
        "city": "Şəhər və ərazi",
        "property_type": "Əmlak növü",
        "area": "Sahə",
        "rooms": "Otaq sayı",
        "price": "Qiymət və ya büdcə",
        "details": "Ətraflı məlumat",
        "contact": "Əlaqə nömrəsi",
    },
    "tr": {
        "kind": "Talep türü",
        "city": "Şehir ve bölge",
        "property_type": "Gayrimenkul türü",
        "area": "Metrekare",
        "rooms": "Oda sayısı",
        "price": "Fiyat veya bütçe",
        "details": "Açıklama",
        "contact": "İletişim numarası",
    },
    "ar": {
        "kind": "نوع الطلب",
        "city": "المدينة والمنطقة",
        "property_type": "نوع العقار",
        "area": "المساحة",
        "rooms": "عدد الغرف",
        "price": "السعر أو الميزانية",
        "details": "التفاصيل",
        "contact": "رقم التواصل",
    },
}

FORM_FIELDS = [
    "city",
    "property_type",
    "area",
    "rooms",
    "price",
    "details",
    "contact",
]

KIND_TEXT = {
    "sell_ad": "آگهی فروش",
    "rent_ad": "آگهی اجاره",
    "buy_req": "درخواست خرید",
    "rent_req": "درخواست اجاره",
    "broker_ad": "آگهی مشاور املاک",
    "builder": "پروژه سازنده",
}

# ==================== لاگ ====================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ==================== پایگاه داده ====================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'fa',
                full_name TEXT DEFAULT '',
                username TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                language TEXT DEFAULT 'fa',
                kind TEXT NOT NULL,
                data TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS publications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                channel TEXT NOT NULL,
                message_id INTEGER,
                status TEXT NOT NULL,
                error TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(submission_id, language)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS support_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def get_user(user_id):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def save_user(user_id, language, full_name="", username=""):
    with db() as conn:
        conn.execute("""
            INSERT INTO users (user_id, language, full_name, username)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                language=excluded.language,
                full_name=excluded.full_name,
                username=excluded.username
        """, (user_id, language, full_name, username))


def get_submission(submission_id):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM submissions WHERE id = ?", (submission_id,)
        ).fetchone()
        return dict(row) if row else None


def save_submission(user_id, language, kind, data):
    with db() as conn:
        cur = conn.execute("""
            INSERT INTO submissions (user_id, language, kind, data)
            VALUES (?, ?, ?, ?)
        """, (user_id, language, kind, json.dumps(data, ensure_ascii=False)))
        return cur.lastrowid


def update_status(submission_id, status):
    with db() as conn:
        conn.execute(
            "UPDATE submissions SET status=? WHERE id=?",
            (status, submission_id),
        )


def publication_status(submission_id, language, channel, status, message_id=None, error=""):
    with db() as conn:
        conn.execute("""
            INSERT INTO publications
                (submission_id, language, channel, status, message_id, error)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(submission_id, language) DO UPDATE SET
                channel=excluded.channel,
                status=excluded.status,
                message_id=excluded.message_id,
                error=excluded.error,
                created_at=CURRENT_TIMESTAMP
        """, (submission_id, language, channel, status, message_id, error))


# ==================== ترجمه گوگل ====================

def translate_sync(text, target_language, source_language=None):
    if not text or target_language == source_language:
        return text

    if not GOOGLE_TRANSLATE_API_KEY:
        raise RuntimeError("GOOGLE_TRANSLATE_API_KEY تنظیم نشده است.")

    url = "https://translation.googleapis.com/language/translate/v2"
    payload = {
        "q": text,
        "target": target_language,
        "format": "text",
    }
    if source_language:
        payload["source"] = source_language

    response = requests.post(
        url,
        params={"key": GOOGLE_TRANSLATE_API_KEY},
        json=payload,
        timeout=25,
    )
    response.raise_for_status()
    result = response.json()["data"]["translations"][0]["translatedText"]
    return result


async def translate_text(text, target_language, source_language=None):
    if not text or target_language == source_language:
        return text
    return await asyncio.to_thread(
        translate_sync, text, target_language, source_language
    )


async def translate_data(data, source_language, target_language):
    translated = dict(data)

    for key in ("city", "property_type", "details"):
        value = str(data.get(key, "")).strip()
        if not value:
            continue
        translated[key] = await translate_text(
            value, target_language, source_language
        )

    return translated


# ==================== نمایش اطلاعات ====================

def language_from_text(text):
    normalized = text.strip()
    for code, label in LANG_NAMES.items():
        if normalized == label or normalized == LANG_LABELS[code]:
            return code

    old_names = {
        "فارسی": "fa",
        "English": "en",
        "Azərbaycan dili": "az",
        "Türkçe": "tr",
        "العربية": "ar",
    }
    return old_names.get(normalized)


def menu_markup(language):
    return ReplyKeyboardMarkup(
        MAIN_MENU.get(language, MAIN_MENU["fa"]),
        resize_keyboard=True,
        is_persistent=True,
    )


def language_markup():
    return ReplyKeyboardMarkup(
        LANGUAGE_KEYBOARD,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def kind_label(kind, language):
    persian = KIND_TEXT.get(kind, kind)
    if language == "fa":
        return persian

    try:
        return translate_sync(persian, language, "fa")
    except Exception:
        return persian


async def render_submission(data, kind, language, source_language):
    labels = FIELD_LABELS[language]
    try:
        translated = await translate_data(data, source_language, language)
    except Exception as exc:
        raise RuntimeError(
            f"ترجمه به {LANG_LABELS[language]} انجام نشد: {exc}"
        )

    lines = [
        f"🏡 <b>{escape(kind_label(kind, language))}</b>",
        "",
    ]

    for key in FORM_FIELDS:
        value = str(translated.get(key, "")).strip()
        if not value:
            continue
        label = escape(labels.get(key, key))
        lines.append(f"<b>{label}:</b> {escape(value)}")

    return "\n".join(lines)


def review_keyboard(submission_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تأیید و انتخاب زبان انتشار",
                callback_data=f"approve:{submission_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "❌ رد آگهی",
                callback_data=f"reject:{submission_id}",
            )
        ],
    ])


async def send_admin_review(context, submission_id):
    submission = get_submission(submission_id)
    if not submission:
        return

    data = json.loads(submission["data"])
    source_language = submission["language"]
    kind = submission["kind"]
    user = get_user(submission["user_id"]) or {}

    header = (
        f"📥 <b>ثبت جدید #{submission_id}</b>\n"
        f"👤 نام: {escape(user.get('full_name', ''))}\n"
        f"🆔 کاربر: <code>{submission['user_id']}</code>\n"
        f"🌐 زبان کاربر: {LANG_LABELS.get(source_language, source_language)}\n"
        f"📌 وضعیت: در انتظار بررسی"
    )

    for language in CHANNELS:
        try:
            rendered = await render_submission(
                data, kind, language, source_language
            )
            message = f"{header}\n\n{rendered}"
        except Exception as exc:
            message = (
                f"{header}\n\n"
                f"⚠️ ترجمه به {LANG_LABELS[language]} ناموفق بود.\n"
                f"متن اصلی:\n{escape(json.dumps(data, ensure_ascii=False))}\n"
                f"خطا: {escape(str(exc))}"
            )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=message,
                parse_mode="HTML",
                reply_markup=review_keyboard(submission_id) if language == "fa" else None,
            )
        except Exception:
            logger.exception("ارسال بررسی به مدیر ناموفق بود")


# ==================== شروع و زبان ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    existing = get_user(user.id)
    if not existing:
        await update.message.reply_text(
            "🌐 زبان موردنظر خود را انتخاب کنید:",
            reply_markup=language_markup(),
        )
        return

    language = existing.get("language", "fa")
    await update.message.reply_text(
        WELCOME.get(language, WELCOME_FA),
        reply_markup=menu_markup(language),
    )


async def set_language(update, language):
    user = update.effective_user
    save_user(
        user.id,
        language,
        user.full_name or "",
        user.username or "",
    )
    await update.message.reply_text(
        WELCOME.get(language, WELCOME_FA),
        reply_markup=menu_markup(language),
    )


# ==================== فرم ثبت آگهی و درخواست ====================

def detect_kind(text):
    mapping = {
        "🏠 ثبت آگهی فروش": "sell_ad",
        "🏠 Sell Property": "sell_ad",
        "🏠 Satılık İlan": "sell_ad",
        "🏠 Satış elanı": "sell_ad",
        "🏠 إعلان بيع": "sell_ad",

        "🔑 ثبت آگهی اجاره": "rent_ad",
        "🔑 Rent Property": "rent_ad",
        "🔑 Kiralık İlan": "rent_ad",
        "🔑 Kirayə elanı": "rent_ad",
        "🔑 إعلان إيجار": "rent_ad",

        "🔎 درخواست خرید": "buy_req",
        "🔎 Buy Request": "buy_req",
        "🔎 Satın Alma Talebi": "buy_req",
        "🔎 Alış sorğusu": "buy_req",
        "🔎 طلب شراء": "buy_req",

        "🏘 درخواست اجاره": "rent_req",
        "🏘 Rent Request": "rent_req",
        "🏘 Kiralama Talebi": "rent_req",
        "🏘 Kirayə sorğusu": "rent_req",
        "🏘 طلب إيجار": "rent_req",

        "🤝 همکاری مشاوران": "broker_ad",
        "🤝 Broker Cooperation": "broker_ad",
        "🤝 Danışman İş Birliği": "broker_ad",
        "🤝 Əməkdaşlıq": "broker_ad",
        "🤝 تعاون الوسطاء": "broker_ad",

        "🏗 سازنده و پروژه": "builder",
        "🏗 Builder / Project": "builder",
        "🏗 İnşaat Projesi": "builder",
        "🏗 Tikinti layihəsi": "builder",
        "🏗 مشروع بناء": "builder",
    }
    return mapping.get(text)


async def begin_form(update, context, kind, language):
    context.user_data["form"] = {
        "kind": kind,
        "language": language,
        "step": 0,
        "data": {},
    }

    first_label = FIELD_LABELS[language]["city"]
    await update.message.reply_text(
        f"📝 {first_label} را وارد کنید:"
        if language == "fa"
        else f"📝 {first_label}:",
        reply_markup=menu_markup(language),
    )


async def handle_form(update, context):
    form = context.user_data.get("form")
    if not form:
        return False

    text = update.message.text.strip()
    language = form["language"]
    step = form["step"]
    key = FORM_FIELDS[step]

    form["data"][key] = text
    form["step"] += 1

    if form["step"] < len(FORM_FIELDS):
        next_key = FORM_FIELDS[form["step"]]
        label = FIELD_LABELS[language][next_key]
        await update.message.reply_text(f"➡️ {label}:")
        return True

    kind = form["kind"]
    data = form["data"]

    submission_id = save_submission(
        update.effective_user.id,
        language,
        kind,
        data,
    )

    context.user_data.pop("form", None)

    await update.message.reply_text(
        "✅ اطلاعات شما ثبت شد و پس از بررسی مدیر، نتیجه اعلام می‌شود."
        if language == "fa"
        else "✅ Your submission has been received and will be reviewed."
    )

    try:
        await send_admin_review(context, submission_id)
    except Exception:
        logger.exception("خطا در ارسال اطلاعات برای مدیر")

    return True


# ==================== انتشار آگهی ====================

async def publish_to_channel(context, submission, language):
    submission_id = submission["id"]
    channel = CHANNELS[language]
    data = json.loads(submission["data"])
    source_language = submission["language"]

    with db() as conn:
        existing = conn.execute("""
            SELECT status FROM publications
            WHERE submission_id=? AND language=?
        """, (submission_id, language)).fetchone()

    if existing and existing["status"] == "success":
        return True, "قبلاً منتشر شده است."

    text = await render_submission(
        data,
        submission["kind"],
        language,
        source_language,
    )

    sent = await context.bot.send_message(
        chat_id=channel,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

    publication_status(
        submission_id,
        language,
        channel,
        "success",
        message_id=sent.message_id,
    )
    return True, "منتشر شد."


async def show_language_selector(query, context, submission_id):
    selected = context.user_data.setdefault("pub_selected", {})
    selected.setdefault(submission_id, ["fa"])

    languages = selected[submission_id]
    keyboard = []

    for code, label in LANG_NAMES.items():
        marker = "✅" if code in languages else "▫️"
        keyboard.append([
            InlineKeyboardButton(
                f"{marker} {label}",
                callback_data=f"pubtoggle:{submission_id}:{code}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🚀 تأیید و انتشار",
            callback_data=f"pubconfirm:{submission_id}",
        ),
        InlineKeyboardButton(
            "لغو",
            callback_data=f"pubcancel:{submission_id}",
        ),
    ])

    await query.edit_message_text(
        f"🌐 زبان‌های انتشار آگهی #{submission_id} را انتخاب کنید.\n"
        "برای انتشار در چند کانال، چند زبان را انتخاب کنید.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ فقط مدیر اصلی دسترسی دارد.", show_alert=True)
        return

    action = query.data

    if action.startswith("approve:"):
        submission_id = int(action.split(":")[1])
        submission = get_submission(submission_id)

        if not submission:
            await query.edit_message_text("❌ اطلاعات پیدا نشد.")
            return

        await show_language_selector(query, context, submission_id)
        return

    if action.startswith("reject:"):
        submission_id = int(action.split(":")[1])
        update_status(submission_id, "rejected")
        await query.edit_message_text(
            f"❌ ثبت #{submission_id} رد شد."
        )
        submission = get_submission(submission_id)
        if submission:
            try:
                await context.bot.send_message(
                    chat_id=submission["user_id"],
                    text="❌ آگهی یا درخواست شما پس از بررسی تأیید نشد.",
                )
            except Exception:
                pass
        return

    if action.startswith("pubtoggle:"):
        _, raw_id, language = action.split(":")
        submission_id = int(raw_id)
        selected = context.user_data.setdefault("pub_selected", {})
        languages = selected.setdefault(submission_id, ["fa"])

        if language in languages:
            languages.remove(language)
        else:
            languages.append(language)

        if not languages:
            languages.append("fa")

        await show_language_selector(query, context, submission_id)
        return

    if action.startswith("pubcancel:"):
        submission_id = int(action.split(":")[1])
        context.user_data.setdefault("pub_selected", {}).pop(submission_id, None)
        await query.edit_message_text("انتشار لغو شد.")
        return

    if action.startswith("pubconfirm:"):
        submission_id = int(action.split(":")[1])
        submission = get_submission(submission_id)

        if not submission:
            await query.edit_message_text("❌ اطلاعات پیدا نشد.")
            return

        selected = context.user_data.setdefault("pub_selected", {})
        languages = selected.pop(submission_id, ["fa"])

        await query.edit_message_text(
            f"⏳ انتشار آگهی #{submission_id} در حال انجام است..."
        )

        results = []
        success_count = 0

        for language in languages:
            channel = CHANNELS[language]
            try:
                ok, message = await publish_to_channel(
                    context, submission, language
                )
                success_count += int(ok)
                results.append(
                    f"✅ {LANG_LABELS[language]} — {channel}: {message}"
                )
            except Exception as exc:
                logger.exception("انتشار ناموفق: %s", language)
                publication_status(
                    submission_id,
                    language,
                    channel,
                    "failed",
                    error=str(exc),
                )
                results.append(
                    f"❌ {LANG_LABELS[language]} — {channel}\n"
                    f"خطا: {str(exc)[:300]}"
                )

        update_status(
            submission_id,
            "approved" if success_count else "pending",
        )

        report = (
            f"📊 <b>گزارش انتشار آگهی #{submission_id}</b>\n\n"
            + "\n\n".join(results)
            + f"\n\nموفق: {success_count} از {len(languages)}"
        )

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=report,
            parse_mode="HTML",
        )

        submission = get_submission(submission_id)
        if submission:
            try:
                await context.bot.send_message(
                    chat_id=submission["user_id"],
                    text=(
                        "✅ آگهی شما در کانال‌های انتخاب‌شده منتشر شد."
                        if success_count
                        else "⚠️ انتشار آگهی انجام نشد. اطلاعات شما برای بررسی مجدد محفوظ است."
                    ),
                )
            except Exception:
                pass


# ==================== پیام‌های کاربر ====================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    text = update.message.text.strip()

    if text.startswith("/"):
        return

    selected_language = language_from_text(text)
    existing_user = get_user(user.id)

    if selected_language:
        await set_language(update, selected_language)
        return

    if not existing_user:
        await update.message.reply_text(
            "🌐 ابتدا زبان موردنظر خود را انتخاب کنید:",
            reply_markup=language_markup(),
        )
        return

    language = existing_user.get("language", "fa")

    if await handle_form(update, context):
        return

    if text in ("🌐 تغییر زبان", "🌐 Change Language", "🌐 Dil", "🌐 Dil Değiştir", "🌐 تغيير اللغة"):
        await update.message.reply_text(
            "🌐 زبان موردنظر خود را انتخاب کنید:",
            reply_markup=language_markup(),
        )
        return

    kind = detect_kind(text)
    if kind:
        await begin_form(update, context, kind, language)
        return

    if text in ("📋 آگهی‌های من", "📋 My Listings", "📋 Elanlarım", "📋 İlanlarım", "📋 إعلاناتي"):
        with db() as conn:
            rows = conn.execute("""
                SELECT id, kind, status, created_at
                FROM submissions
                WHERE user_id=?
                ORDER BY id DESC LIMIT 20
            """, (user.id,)).fetchall()

        if not rows:
            await update.message.reply_text("هنوز آگهی یا درخواستی ثبت نکرده‌اید.")
            return

        lines = ["📋 <b>آگهی‌ها و درخواست‌های شما</b>\n"]
        for row in rows:
            lines.append(
                f"#{row['id']} — {escape(KIND_TEXT.get(row['kind'], row['kind']))}"
                f" — {escape(row['status'])}"
            )

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=menu_markup(language),
        )
        return

    if text in ("📨 درخواست‌های من", "📨 My Requests", "📨 Sorğularım", "📨 Taleplerim", "📨 طلباتي"):
        with db() as conn:
            rows = conn.execute("""
                SELECT id, kind, status, created_at
                FROM submissions
                WHERE user_id=? AND kind IN ('buy_req','rent_req')
                ORDER BY id DESC LIMIT 20
            """, (user.id,)).fetchall()

        if not rows:
            await update.message.reply_text("هنوز درخواستی ثبت نکرده‌اید.")
            return

        lines = ["📨 <b>درخواست‌های شما</b>\n"]
        for row in rows:
            lines.append(
                f"#{row['id']} — {escape(KIND_TEXT.get(row['kind'], row['kind']))}"
                f" — {escape(row['status'])}"
            )

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=menu_markup(language),
        )
        return

    if text in ("🆘 پشتیبانی", "🆘 Support", "🆘 Dəstək", "🆘 Destek", "🆘 الدعم"):
        context.user_data["awaiting_support"] = True
        await update.message.reply_text(
            "پیام خود را برای پشتیبانی ارسال کنید:"
            if language == "fa"
            else "Please send your support message."
        )
        return

    if context.user_data.pop("awaiting_support", False):
        with db() as conn:
            conn.execute(
                "INSERT INTO support_messages (user_id, message) VALUES (?, ?)",
                (user.id, text),
            )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"🆘 <b>پیام پشتیبانی</b>\n"
                    f"کاربر: <code>{user.id}</code>\n\n"
                    f"{escape(text)}"
                ),
                parse_mode="HTML",
            )
        except Exception:
            logger.exception("ارسال پیام پشتیبانی ناموفق بود")

        await update.message.reply_text(
            "✅ پیام شما برای پشتیبانی ارسال شد."
        )
        return

    await update.message.reply_text(
        "از منوی زیر استفاده کنید یا یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=menu_markup(language),
    )


# ==================== پنل مدیریتی متنی ====================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ دسترسی ندارید.")
        return

    with db() as conn:
        pending = conn.execute(
            "SELECT COUNT(*) AS n FROM submissions WHERE status='pending'"
        ).fetchone()["n"]
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM submissions"
        ).fetchone()["n"]

    await update.message.reply_text(
        f"🛠 پنل مدیر\n\n"
        f"📥 در انتظار بررسی: {pending}\n"
        f"📊 مجموع ثبت‌ها: {total}\n\n"
        f"برای بررسی، پیام‌های ارسالی ربات را مشاهده کنید."
    )


# ==================== سرور Render ====================

web_app = Flask(__name__)


@web_app.get("/")
def health():
    return "Tehran Real Estate Bot is running.", 200


@web_app.get("/health")
def health_check():
    return {"status": "ok"}, 200


def run_web():
    port = int(os.getenv("PORT", "10000"))
    web_app.run(host="0.0.0.0", port=port)


def main():
    if not BOT_TOKEN:
        raise RuntimeError("متغیر BOT_TOKEN تنظیم نشده است.")

    init_db()

    Thread(target=run_web, daemon=True).start()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(
        CallbackQueryHandler(
            review_callback,
            pattern=r"^(approve|reject):\d+$|^pubtoggle:\d+:(fa|en|az|tr|ar)$|^pubconfirm:\d+$|^pubcancel:\d+$",
        )
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    logger.info("ربات املاک تهران اجرا شد.")
    application.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
