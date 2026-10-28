import os
import json
import sqlite3
import logging
import asyncio
from threading import Thread
from html import escape

import requests
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

# ==================== SETTINGS ====================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "6245308636"))
DB_PATH = os.getenv("DB_PATH", "realestate.db")
GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY", "").strip()

CHANNELS = {
    "fa": "@tehranrealstate",
    "en": "@tehranrealstate_en",
    "az": "@tehranrealstate_az",
    "tr": "@tehranrealstate_tr",
    "ar": "@tehranrealstate_ar",
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

WELCOME = {
    "fa": """🏡✨ به گروه بزرگ مشاورین املاک تهران خوش آمدید! ✨🏡

🌟 مجموعه مشاورین املاک تهران با بیش از ۲۰ سال سابقه فعالیت، گسترده‌ترین شبکه اطلاعات ملکی در ایران و بیش از ۱۰۰۰ مشاور فعال در سراسر کشور، در کنار شماست.

🤝 هدف پرسنل و مدیریت مجموعه، جلب رضایت شما مشتریان عزیز و ارائه خدماتی شایسته، مطمئن و حرفه‌ای است.

🌹 امیدواریم تجربه‌ای رضایت‌بخش و همکاری ارزشمندی را در کنار ما داشته باشید.

💠 املاک تهران؛ همراه شما در مسیر انتخابی مطمئن. 💠""",

    "en": """🏡✨ Welcome to the Tehran Real Estate Group! ✨🏡

🌟 With over 20 years of experience, an extensive property information network in Iran, and more than 1,000 active consultants nationwide, we are here to help you.

🤝 Our team is committed to customer satisfaction and providing reliable, professional services.

🌹 We hope you have a satisfying experience and a valuable partnership with us.

💠 Tehran Real Estate — your trusted partner in making confident property decisions. 💠""",

    "az": """🏡✨ Tehran Daşınmaz Əmlak Məsləhətçiləri Qrupuna xoş gəlmisiniz! ✨🏡

🌟 20 ildən artıq təcrübəmiz, geniş daşınmaz əmlak məlumat şəbəkəmiz və ölkə üzrə 1.000-dən çox fəal məsləhətçimizlə sizin xidmətinizdəyik.

🤝 Məqsədimiz müştəri məmnuniyyətini təmin etmək və etibarlı, peşəkar xidmət göstərməkdir.

🌹 Sizinlə uğurlu və dəyərli əməkdaşlıq arzulayırıq.

💠 Tehran Daşınmaz Əmlak — düzgün seçim yolunda etibarlı tərəfdaşınız. 💠""",

    "tr": """🏡✨ Tahran Gayrimenkul Danışmanları Grubuna hoş geldiniz! ✨🏡

🌟 20 yılı aşkın deneyimimiz, geniş gayrimenkul bilgi ağımız ve ülke genelinde 1.000'den fazla aktif danışmanımızla hizmetinizdeyiz.

🤝 Amacımız müşteri memnuniyetini sağlamak ve güvenilir, profesyonel hizmet sunmaktır.

🌹 Sizinle başarılı ve değerli bir iş birliği yapmayı dileriz.

💠 Tahran Gayrimenkul — doğru seçim yolunda güvenilir ortağınız. 💠""",

    "ar": """🏡✨ أهلاً وسهلاً بكم في مجموعة مستشاري عقارات طهران! ✨🏡

🌟 بخبرة تزيد على 20 عاماً وشبكة واسعة لمعلومات العقارات وأكثر من 1,000 مستشار نشط في جميع أنحاء البلاد، نحن هنا لخدمتكم.

🤝 هدفنا تحقيق رضا العملاء وتقديم خدمات موثوقة واحترافية.

🌹 نتمنى لكم تجربة مرضية وتعاوناً مثمراً.

💠 عقارات طهران — شريككم الموثوق لاختيار عقاري مناسب. 💠""",
}

MENU = {
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
        ["🆘 Dəstək", "🌐 Dil dəyişdir"],
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

FIELDS = ["city", "property_type", "area", "rooms", "price", "details", "contact"]

FIELD_LABELS = {
    "fa": {
        "city": "شهر و منطقه",
        "property_type": "نوع ملک",
        "area": "متراژ",
        "rooms": "تعداد اتاق",
        "price": "قیمت یا بودجه",
        "details": "توضیحات",
        "contact": "شماره تماس",
    },
    "en": {
        "city": "City and area",
        "property_type": "Property type",
        "area": "Area",
        "rooms": "Number of rooms",
        "price": "Price or budget",
        "details": "Details",
        "contact": "Contact number",
    },
    "az": {
        "city": "Şəhər və ərazi",
        "property_type": "Əmlak növü",
        "area": "Sahə",
        "rooms": "Otaq sayı",
        "price": "Qiymət və ya büdcə",
        "details": "Ətraflı məlumat",
        "contact": "Əlaqə nömrəsi",
    },
    "tr": {
        "city": "Şehir ve bölge",
        "property_type": "Gayrimenkul türü",
        "area": "Metrekare",
        "rooms": "Oda sayısı",
        "price": "Fiyat veya bütçe",
        "details": "Açıklama",
        "contact": "İletişim numarası",
    },
    "ar": {
        "city": "المدينة والمنطقة",
        "property_type": "نوع العقار",
        "area": "المساحة",
        "rooms": "عدد الغرف",
        "price": "السعر أو الميزانية",
        "details": "التفاصيل",
        "contact": "رقم التواصل",
    },
}

KINDS = {
    "sell_ad": {
        "fa": "آگهی فروش",
        "en": "Property for sale",
        "az": "Satış elanı",
        "tr": "Satılık gayrimenkul",
        "ar": "عقار للبيع",
    },
    "rent_ad": {
        "fa": "آگهی اجاره",
        "en": "Property for rent",
        "az": "Kirayə elanı",
        "tr": "Kiralık gayrimenkul",
        "ar": "عقار للإيجار",
    },
    "buy_req": {
        "fa": "درخواست خرید",
        "en": "Property purchase request",
        "az": "Alış sorğusu",
        "tr": "Satın alma talebi",
        "ar": "طلب شراء عقار",
    },
    "rent_req": {
        "fa": "درخواست اجاره",
        "en": "Rental request",
        "az": "Kirayə sorğusu",
        "tr": "Kiralama talebi",
        "ar": "طلب استئجار عقار",
    },
    "broker_ad": {
        "fa": "همکاری مشاوران",
        "en": "Broker cooperation",
        "az": "Əmlak məsləhətçilərinin əməkdaşlığı",
        "tr": "Danışman iş birliği",
        "ar": "تعاون الوسطاء العقاريين",
    },
    "builder": {
        "fa": "پروژه سازنده",
        "en": "Builder / development project",
        "az": "Tikinti layihəsi",
        "tr": "İnşaat projesi",
        "ar": "مشروع بناء",
    },
}

# ==================== LOGGING ====================

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("tehran-real-estate")


# ==================== DATABASE ====================

def connect_db():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'fa',
                full_name TEXT DEFAULT '',
                username TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                kind TEXT NOT NULL,
                data TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
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


def save_user(user, language):
    with connect_db() as conn:
        conn.execute("""
            INSERT INTO users (user_id, language, full_name, username)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                language=excluded.language,
                full_name=excluded.full_name,
                username=excluded.username
        """, (
            user.id,
            language,
            user.full_name or "",
            user.username or "",
        ))


def get_user(user_id):
    with connect_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def create_submission(user_id, language, kind, data):
    with connect_db() as conn:
        cursor = conn.execute("""
            INSERT INTO submissions (user_id, language, kind, data)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            language,
            kind,
            json.dumps(data, ensure_ascii=False),
        ))
        return cursor.lastrowid


def get_submission(submission_id):
    with connect_db() as conn:
        row = conn.execute(
            "SELECT * FROM submissions WHERE id=?", (submission_id,)
        ).fetchone()
        return dict(row) if row else None


def set_submission_status(submission_id, status):
    with connect_db() as conn:
        conn.execute(
            "UPDATE submissions SET status=? WHERE id=?",
            (status, submission_id),
        )


def record_publication(submission_id, language, channel, status,
                       message_id=None, error=""):
    with connect_db() as conn:
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
        """, (
            submission_id, language, channel, status, message_id, error
        ))


# ==================== TRANSLATION ====================

def translate_sync(text, target, source=None):
    if not text or target == source:
        return text

    if not GOOGLE_TRANSLATE_API_KEY:
        raise RuntimeError("GOOGLE_TRANSLATE_API_KEY تنظیم نشده است.")

    response = requests.post(
        "https://translation.googleapis.com/language/translate/v2",
        params={"key": GOOGLE_TRANSLATE_API_KEY},
        json={
            "q": text,
            "target": target,
            "source": source,
            "format": "text",
        },
        timeout=25,
    )
    response.raise_for_status()
    return response.json()["data"]["translations"][0]["translatedText"]


async def translate(text, target, source=None):
    if not text or target == source:
        return text
    return await asyncio.to_thread(translate_sync, text, target, source)


async def translate_submission_data(data, source, target):
    result = dict(data)

    for key in ("city", "property_type", "details"):
        value = str(data.get(key, "")).strip()
        if value:
            result[key] = await translate(value, target, source)

    return result


# ==================== KEYBOARDS ====================

def language_keyboard():
    return ReplyKeyboardMarkup(
        LANGUAGE_KEYBOARD,
        resize_keyboard=True,
        one_time_keyboard=True,
        is_persistent=True,
    )


def main_keyboard(language):
    return ReplyKeyboardMarkup(
        MENU.get(language, MENU["fa"]),
        resize_keyboard=True,
        is_persistent=True,
    )


def parse_language(text):
    text = text.strip()
    for code, label in LANG_NAMES.items():
        if text == label:
            return code

    aliases = {
        "فارسی": "fa",
        "English": "en",
        "Azərbaycan dili": "az",
        "Türkçe": "tr",
        "العربية": "ar",
    }
    return aliases.get(text)


def language_prompt():
    return (
        "🌐 لطفاً زبان خود را انتخاب کنید:\n\n"
        "🌐 Please select your language:\n"
        "🌐 Zəhmət olmasa, dilinizi seçin:\n"
        "🌐 Lütfen dilinizi seçin:\n"
        "🌐 يرجى اختيار لغتك:"
    )


# ==================== START AND LANGUAGE ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    context.user_data.pop("form", None)

    await update.message.reply_text(
        language_prompt(),
        reply_markup=language_keyboard(),
    )


async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          language: str):
    user = update.effective_user
    save_user(user, language)

    await update.message.reply_text(
        WELCOME[language],
        reply_markup=main_keyboard(language),
    )


# ==================== FORM ROUTING ====================

def detect_kind(text):
    mapping = {
        "🏠 ثبت آگهی فروش": "sell_ad",
        "🏠 Sell Property": "sell_ad",
        "🏠 Satış elanı": "sell_ad",
        "🏠 Satılık İlan": "sell_ad",
        "🏠 إعلان بيع": "sell_ad",

        "🔑 ثبت آگهی اجاره": "rent_ad",
        "🔑 Rent Property": "rent_ad",
        "🔑 Kirayə elanı": "rent_ad",
        "🔑 Kiralık İlan": "rent_ad",
        "🔑 إعلان إيجار": "rent_ad",

        "🔎 درخواست خرید": "buy_req",
        "🔎 Buy Request": "buy_req",
        "🔎 Alış sorğusu": "buy_req",
        "🔎 Satın Alma Talebi": "buy_req",
        "🔎 طلب شراء": "buy_req",

        "🏘 درخواست اجاره": "rent_req",
        "🏘 Rent Request": "rent_req",
        "🏘 Kirayə sorğusu": "rent_req",
        "🏘 Kiralama Talebi": "rent_req",
        "🏘 طلب إيجار": "rent_req",

        "🤝 همکاری مشاوران": "broker_ad",
        "🤝 Broker Cooperation": "broker_ad",
        "🤝 Əməkdaşlıq": "broker_ad",
        "🤝 Danışman İş Birliği": "broker_ad",
        "🤝 تعاون الوسطاء": "broker_ad",

        "🏗 سازنده و پروژه": "builder",
        "🏗 Builder / Project": "builder",
        "🏗 Tikinti layihəsi": "builder",
        "🏗 İnşaat Projesi": "builder",
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
    await update.message.reply_text(
        f"📝 {FIELD_LABELS[language]['city']}:",
        reply_markup=main_keyboard(language),
    )


async def process_form(update, context):
    form = context.user_data.get("form")
    if not form:
        return False

    text = update.message.text.strip()
    language = form["language"]
    index = form["step"]
    field = FIELDS[index]
    form["data"][field] = text
    form["step"] += 1

    if form["step"] < len(FIELDS):
        next_field = FIELDS[form["step"]]
        await update.message.reply_text(
            f"➡️ {FIELD_LABELS[language][next_field]}:"
        )
        return True

    submission_id = create_submission(
        update.effective_user.id,
        language,
        form["kind"],
        form["data"],
    )
    context.user_data.pop("form", None)

    confirmations = {
        "fa": "✅ اطلاعات شما ثبت شد و برای بررسی مدیر ارسال می‌شود.",
        "en": "✅ Your submission has been received and sent for review.",
        "az": "✅ Məlumatınız qəbul edildi və yoxlanış üçün göndərildi.",
        "tr": "✅ Bilgileriniz alındı ve inceleme için gönderildi.",
        "ar": "✅ تم استلام معلوماتك وإرسالها للمراجعة.",
    }
    await update.message.reply_text(
        confirmations[language],
        reply_markup=main_keyboard(language),
    )

    await send_admin_review(context, submission_id)
    return True


# ==================== ADMIN REVIEW ====================

def review_keyboard(submission_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ تأیید و انتخاب زبان انتشار",
            callback_data=f"approve:{submission_id}",
        )],
        [InlineKeyboardButton(
            "❌ رد",
            callback_data=f"reject:{submission_id}",
        )],
    ])


async def render_submission(data, kind, language, source_language):
    translated = await translate_submission_data(
        data, source_language, language
    )

    lines = [
        f"🏡 <b>{escape(KINDS[kind][language])}</b>",
        "",
    ]

    for field in FIELDS:
        value = str(translated.get(field, "")).strip()
        if value:
            lines.append(
                f"<b>{escape(FIELD_LABELS[language][field])}:</b> "
                f"{escape(value)}"
            )

    return "\n".join(lines)


async def send_admin_review(context, submission_id):
    submission = get_submission(submission_id)
    if not submission:
        return

    data = json.loads(submission["data"])
    user = get_user(submission["user_id"]) or {}
    source_language = submission["language"]

    for language in CHANNELS:
        try:
            body = await render_submission(
                data, submission["kind"], language, source_language
            )
            header = (
                f"📥 <b>ثبت جدید #{submission_id}</b>\n"
                f"👤 {escape(user.get('full_name', ''))}\n"
                f"🆔 <code>{submission['user_id']}</code>\n"
                f"🌐 زبان ثبت‌کننده: "
                f"{escape(LANG_LABELS[source_language])}\n"
                f"📌 وضعیت: در انتظار بررسی\n\n"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=header + body,
                parse_mode="HTML",
                reply_markup=review_keyboard(submission_id)
                if language == "fa" else None,
            )
        except Exception as exc:
            logger.exception("Admin review translation/send failed")
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"⚠️ ارسال نسخه {LANG_LABELS[language]} برای ثبت "
                    f"#{submission_id} ناموفق بود.\n{str(exc)[:500]}"
                ),
            )


# ==================== CHANNEL PUBLICATION ====================

async def publish_submission(context, submission, language):
    submission_id = submission["id"]
    channel = CHANNELS[language]

    with connect_db() as conn:
        previous = conn.execute("""
            SELECT status FROM publications
            WHERE submission_id=? AND language=?
        """, (submission_id, language)).fetchone()

    if previous and previous["status"] == "success":
        return True, "قبلاً منتشر شده است."

    data = json.loads(submission["data"])
    message_text = await render_submission(
        data,
        submission["kind"],
        language,
        submission["language"],
    )

    message = await context.bot.send_message(
        chat_id=channel,
        text=message_text,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

    record_publication(
        submission_id,
        language,
        channel,
        "success",
        message_id=message.message_id,
    )
    return True, "منتشر شد."


async def show_publication_languages(query, context, submission_id):
    selections = context.user_data.setdefault("publication_languages", {})
    selections.setdefault(submission_id, ["fa"])
    selected = selections[submission_id]

    keyboard = []
    for language, label in LANG_NAMES.items():
        mark = "✅" if language in selected else "▫️"
        keyboard.append([InlineKeyboardButton(
            f"{mark} {label}",
            callback_data=f"pubtoggle:{submission_id}:{language}",
        )])

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
        f"🌐 زبان‌های انتشار ثبت #{submission_id} را انتخاب کنید.\n"
        "می‌توانید چند زبان را هم‌زمان انتخاب کنید.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ فقط مدیر اصلی دسترسی دارد.", show_alert=True)
        return

    await query.answer()
    action = query.data

    if action.startswith("approve:"):
        submission_id = int(action.split(":")[1])
        if not get_submission(submission_id):
            await query.edit_message_text("❌ ثبت موردنظر پیدا نشد.")
            return
        await show_publication_languages(query, context, submission_id)
        return

    if action.startswith("reject:"):
        submission_id = int(action.split(":")[1])
        submission = get_submission(submission_id)
        set_submission_status(submission_id, "rejected")
        await query.edit_message_text(f"❌ ثبت #{submission_id} رد شد.")

        if submission:
            try:
                await context.bot.send_message(
                    chat_id=submission["user_id"],
                    text="❌ ثبت شما پس از بررسی تأیید نشد.",
                )
            except Exception:
                logger.warning("Could not notify submitter")
        return

    if action.startswith("pubtoggle:"):
        _, raw_id, language = action.split(":")
        submission_id = int(raw_id)
        selections = context.user_data.setdefault("publication_languages", {})
        selected = selections.setdefault(submission_id, ["fa"])

        if language in selected:
            selected.remove(language)
        else:
            selected.append(language)

        await show_publication_languages(query, context, submission_id)
        return

    if action.startswith("pubcancel:"):
        submission_id = int(action.split(":")[1])
        context.user_data.setdefault(
            "publication_languages", {}
        ).pop(submission_id, None)
        await query.edit_message_text("انتشار لغو شد.")
        return

    if action.startswith("pubconfirm:"):
        submission_id = int(action.split(":")[1])
        submission = get_submission(submission_id)

        if not submission:
            await query.edit_message_text("❌ ثبت موردنظر پیدا نشد.")
            return

        selections = context.user_data.setdefault("publication_languages", {})
        languages = selections.pop(submission_id, ["fa"])

        if not languages:
            await query.edit_message_text(
                "❌ حداقل یک زبان را انتخاب کنید."
            )
            return

        await query.edit_message_text(
            f"⏳ انتشار ثبت #{submission_id} در حال انجام است..."
        )

        report = []
        successful = 0

        for language in languages:
            channel = CHANNELS[language]
            try:
                ok, detail = await publish_submission(
                    context, submission, language
                )
                successful += int(ok)
                report.append(
                    f"✅ {LANG_NAMES[language]} ({channel}): {detail}"
                )
            except Exception as exc:
                logger.exception("Publication failed for %s", language)
                record_publication(
                    submission_id,
                    language,
                    channel,
                    "failed",
                    error=str(exc)[:1000],
                )
                report.append(
                    f"❌ {LANG_NAMES[language]} ({channel})\n"
                    f"خطا: {str(exc)[:300]}"
                )

        set_submission_status(
            submission_id,
            "approved" if successful else "pending",
        )

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"📊 گزارش انتشار ثبت #{submission_id}\n\n"
                + "\n\n".join(report)
                + f"\n\nموفق: {successful}/{len(languages)}"
            ),
        )

        try:
            await context.bot.send_message(
                chat_id=submission["user_id"],
                text=(
                    "✅ ثبت شما منتشر شد."
                    if successful
                    else "⚠️ انتشار انجام نشد؛ ثبت شما برای بررسی مجدد محفوظ است."
                ),
            )
        except Exception:
            pass


# ==================== USER MESSAGES ====================

LANGUAGE_CHANGE_BUTTONS = {
    "🌐 تغییر زبان", "🌐 Change Language", "🌐 Dil dəyişdir",
    "🌐 Dil Değiştir", "🌐 تغيير اللغة",
}

SUPPORT_BUTTONS = {
    "🆘 پشتیبانی", "🆘 Support", "🆘 Dəstək",
    "🆘 Destek", "🆘 الدعم",
}

MY_LISTINGS_BUTTONS = {
    "📋 آگهی‌های من", "📋 My Listings", "📋 Elanlarım",
    "📋 İlanlarım", "📋 إعلاناتي",
}

MY_REQUESTS_BUTTONS = {
    "📨 درخواست‌های من", "📨 My Requests", "📨 Sorğularım",
    "📨 Taleplerim", "📨 طلباتي",
}


async def show_user_submissions(update, user_id, only_requests=False):
    sql = """
        SELECT id, kind, status, created_at
        FROM submissions
        WHERE user_id=?
    """
    if only_requests:
        sql += " AND kind IN ('buy_req','rent_req')"
    sql += " ORDER BY id DESC LIMIT 20"

    with connect_db() as conn:
        rows = conn.execute(sql, (user_id,)).fetchall()

    if not rows:
        await update.message.reply_text("هنوز موردی ثبت نکرده‌اید.")
        return

    lines = ["📋 ثبت‌های شما:\n"]
    for row in rows:
        lines.append(
            f"#{row['id']} — {KINDS.get(row['kind'], {}).get('fa', row['kind'])}"
            f" — {row['status']}"
        )

    await update.message.reply_text("\n".join(lines))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    text = update.message.text.strip()

    language = parse_language(text)
    if language:
        context.user_data.pop("form", None)
        await choose_language(update, context, language)
        return

    saved_user = get_user(user.id)
    if not saved_user:
        await update.message.reply_text(
            language_prompt(),
            reply_markup=language_keyboard(),
        )
        return

    user_language = saved_user["language"]

    if await process_form(update, context):
        return

    if text in LANGUAGE_CHANGE_BUTTONS:
        await update.message.reply_text(
            language_prompt(),
            reply_markup=language_keyboard(),
        )
        return

    kind = detect_kind(text)
    if kind:
        await begin_form(update, context, kind, user_language)
        return

    if text in MY_LISTINGS_BUTTONS:
        await show_user_submissions(update, user.id)
        return

    if text in MY_REQUESTS_BUTTONS:
        await show_user_submissions(update, user.id, only_requests=True)
        return

    if text in SUPPORT_BUTTONS:
        context.user_data["awaiting_support"] = True
        await update.message.reply_text("پیام خود را برای پشتیبانی ارسال کنید:")
        return

    if context.user_data.get("awaiting_support"):
        context.user_data["awaiting_support"] = False

        with connect_db() as conn:
            conn.execute(
                "INSERT INTO support_messages (user_id, message) VALUES (?, ?)",
                (user.id, text),
            )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"🆘 پیام پشتیبانی\n"
                    f"کاربر: {user.id}\n\n{text}"
                ),
            )
        except Exception:
            logger.exception("Support notification failed")

        await update.message.reply_text("✅ پیام شما برای پشتیبانی ارسال شد.")
        return

    await update.message.reply_text(
        "لطفاً از گزینه‌های منو استفاده کنید.",
        reply_markup=main_keyboard(user_language),
    )


# ==================== ADMIN COMMAND ====================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ دسترسی ندارید.")
        return

    with connect_db() as conn:
        pending = conn.execute(
            "SELECT COUNT(*) AS n FROM submissions WHERE status='pending'"
        ).fetchone()["n"]
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM submissions"
        ).fetchone()["n"]

    await update.message.reply_text(
        f"🛠 پنل مدیر\n\n"
        f"📥 در انتظار بررسی: {pending}\n"
        f"📊 کل ثبت‌ها: {total}"
    )


# ==================== RENDER HEALTH SERVER ====================

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


# ==================== MAIN ====================

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده است.")

    init_db()
    Thread(target=run_web, daemon=True).start()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=(
                r"^(approve|reject):\d+$"
                r"|^pubtoggle:\d+:(fa|en|az|tr|ar)$"
                r"|^pubconfirm:\d+$"
                r"|^pubcancel:\d+$"
            ),
        )
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    logger.info("Tehran Real Estate bot started.")
    application.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
