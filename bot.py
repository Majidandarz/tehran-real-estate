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

# ==================== تنظیمات ====================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "6245308636"))
DB_PATH = os.getenv("DB_PATH", "realestate.db")
GOOGLE_TRANSLATE_API_KEY = os.getenv(
    "GOOGLE_TRANSLATE_API_KEY", ""
).strip()

LANGUAGES = {
    "fa": {
        "name": "🇮🇷 فارسی",
        "native": "فارسی",
        "channel": "@tehranrealstate",
    },
    "en": {
        "name": "🇬🇧 English",
        "native": "English",
        "channel": "@tehranrealstate_en",
    },
    "az": {
        "name": "🇦🇿 Azərbaycan dili",
        "native": "Azərbaycan dili",
        "channel": "@tehranrealstate_az",
    },
    "tr": {
        "name": "🇹🇷 Türkçe",
        "native": "Türkçe",
        "channel": "@tehranrealstate_tr",
    },
    "ar": {
        "name": "🇸🇦 العربية",
        "native": "العربية",
        "channel": "@tehranrealstate_ar",
    },
}

LANG_CODES = tuple(LANGUAGES.keys())

# ==================== پیام خوشامدگویی ====================

WELCOME = {
    "fa": """🏡✨ به گروه بزرگ مشاورین املاک تهران خوش آمدید! ✨🏡

🌟 مجموعه مشاورین املاک تهران با بیش از ۲۰ سال سابقه فعالیت، گسترده‌ترین شبکه اطلاعات ملکی در ایران و بیش از ۱۰۰۰ مشاور فعال در سراسر کشور، در کنار شماست.

🤝 هدف پرسنل و مدیریت مجموعه، جلب رضایت شما مشتریان عزیز و ارائه خدماتی شایسته، مطمئن و حرفه‌ای است.

🌹 امیدواریم تجربه‌ای رضایت‌بخش و همکاری ارزشمندی را در کنار ما داشته باشید.

💠 املاک تهران؛ همراه شما در مسیر انتخابی مطمئن. 💠""",

    "en": """🏡✨ Welcome to the Tehran Real Estate Group! ✨🏡

🌟 With more than 20 years of experience, an extensive property information network in Iran, and over 1,000 active consultants nationwide, we are here to assist you.

🤝 Our management and team are committed to customer satisfaction and providing reliable, professional services.

🌹 We hope you have a satisfying experience and a valuable partnership with us.

💠 Tehran Real Estate — your trusted partner in making confident property decisions. 💠""",

    "az": """🏡✨ Tehran Daşınmaz Əmlak Məsləhətçiləri Qrupuna xoş gəlmisiniz! ✨🏡

🌟 20 ildən artıq fəaliyyət təcrübəmiz, geniş daşınmaz əmlak məlumat şəbəkəmiz və ölkə üzrə 1.000-dən çox fəal məsləhətçimizlə sizin xidmətinizdəyik.

🤝 Komandamızın və rəhbərliyimizin məqsədi müştəri məmnuniyyətini təmin etmək və etibarlı, peşəkar xidmət göstərməkdir.

🌹 Sizinlə uğurlu və dəyərli əməkdaşlıq arzulayırıq.

💠 Tehran Daşınmaz Əmlak — düzgün seçim yolunda etibarlı tərəfdaşınız. 💠""",

    "tr": """🏡✨ Tahran Gayrimenkul Danışmanları Grubuna hoş geldiniz! ✨🏡

🌟 20 yılı aşkın faaliyet deneyimimiz, İran genelindeki geniş gayrimenkul bilgi ağımız ve ülke çapında 1.000'den fazla aktif danışmanımızla hizmetinizdeyiz.

🤝 Yönetimimizin ve ekibimizin amacı müşteri memnuniyetini sağlamak, güvenilir ve profesyonel hizmet sunmaktır.

🌹 Sizinle memnuniyet verici ve değerli bir iş birliği yapmayı diliyoruz.

💠 Tahran Gayrimenkul — güvenilir bir seçim yapmanız için yanınızda. 💠""",

    "ar": """🏡✨ أهلاً وسهلاً بكم في مجموعة مستشاري عقارات طهران! ✨🏡

🌟 بخبرة تزيد على 20 عاماً في هذا المجال، وشبكة واسعة لمعلومات العقارات في إيران، وأكثر من 1,000 مستشار نشط في جميع أنحاء البلاد، نحن هنا لخدمتكم.

🤝 يهدف فريقنا وإدارتنا إلى تحقيق رضا العملاء وتقديم خدمات موثوقة ومهنية.

🌹 نتمنى لكم تجربة مرضية وتعاوناً مثمراً وقيّماً معنا.

💠 عقارات طهران — شريككم الموثوق لاتخاذ قرار عقاري مدروس. 💠""",
}

# ==================== ترجمة الرسائل ====================

TEXT = {
    "fa": {
        "select": "🌐 لطفاً زبان خود را انتخاب کنید:",
        "city": "شهر و منطقه ملک یا درخواست را وارد کنید:",
        "type": "نوع ملک را وارد کنید:",
        "area": "متراژ را وارد کنید:",
        "rooms": "تعداد اتاق را وارد کنید:",
        "price": "قیمت یا بودجه را وارد کنید:",
        "details": "توضیحات تکمیلی را وارد کنید:",
        "contact": "شماره تماس را وارد کنید:",
        "saved": "✅ اطلاعات ثبت شد و برای بررسی مدیر ارسال شد.",
        "support": "پیام خود را برای پشتیبانی ارسال کنید:",
        "support_sent": "✅ پیام شما برای مدیر ارسال شد.",
        "menu_error": "لطفاً از دکمه‌های منو استفاده کنید.",
        "my_items": "📋 ثبت‌های شما:",
        "empty": "هنوز موردی ثبت نکرده‌اید.",
        "cancel": "لغو فرم",
        "cancelled": "فرم لغو شد.",
        "lang_changed": "✅ زبان تغییر کرد.",
        "published": "✅ ثبت شما منتشر شد.",
        "rejected": "❌ ثبت شما پس از بررسی تأیید نشد.",
    },
    "en": {
        "select": "🌐 Please select your language:",
        "city": "Enter the city and area:",
        "type": "Enter the property type:",
        "area": "Enter the property area:",
        "rooms": "Enter the number of rooms:",
        "price": "Enter the price or budget:",
        "details": "Enter additional details:",
        "contact": "Enter your contact number:",
        "saved": "✅ Your submission was sent to the administrator for review.",
        "support": "Send your support message:",
        "support_sent": "✅ Your message was sent to the administrator.",
        "menu_error": "Please use the menu buttons.",
        "my_items": "📋 Your submissions:",
        "empty": "You have not submitted anything yet.",
        "cancel": "Cancel form",
        "cancelled": "The form was cancelled.",
        "lang_changed": "✅ Language changed.",
        "published": "✅ Your submission has been published.",
        "rejected": "❌ Your submission was not approved.",
    },
    "az": {
        "select": "🌐 Zəhmət olmasa, dilinizi seçin:",
        "city": "Şəhəri və ərazini daxil edin:",
        "type": "Əmlak növünü daxil edin:",
        "area": "Sahəni daxil edin:",
        "rooms": "Otaqların sayını daxil edin:",
        "price": "Qiyməti və ya büdcəni daxil edin:",
        "details": "Əlavə məlumatları daxil edin:",
        "contact": "Əlaqə nömrəsini daxil edin:",
        "saved": "✅ Məlumatınız yoxlanış üçün administratora göndərildi.",
        "support": "Dəstək mesajınızı göndərin:",
        "support_sent": "✅ Mesajınız administratora göndərildi.",
        "menu_error": "Zəhmət olmasa, menyu düymələrindən istifadə edin.",
        "my_items": "📋 Göndərdiyiniz məlumatlar:",
        "empty": "Hələ heç nə göndərməmisiniz.",
        "cancel": "Formanı ləğv et",
        "cancelled": "Forma ləğv edildi.",
        "lang_changed": "✅ Dil dəyişdirildi.",
        "published": "✅ Məlumatınız yayımlandı.",
        "rejected": "❌ Məlumatınız təsdiqlənmədi.",
    },
    "tr": {
        "select": "🌐 Lütfen dilinizi seçin:",
        "city": "Şehri ve bölgeyi girin:",
        "type": "Gayrimenkul türünü girin:",
        "area": "Metrekare bilgisini girin:",
        "rooms": "Oda sayısını girin:",
        "price": "Fiyatı veya bütçeyi girin:",
        "details": "Ek açıklamaları girin:",
        "contact": "İletişim numaranızı girin:",
        "saved": "✅ Bilgileriniz inceleme için yöneticiye gönderildi.",
        "support": "Destek mesajınızı gönderin:",
        "support_sent": "✅ Mesajınız yöneticiye gönderildi.",
        "menu_error": "Lütfen menü düğmelerini kullanın.",
        "my_items": "📋 Gönderileriniz:",
        "empty": "Henüz bir gönderi oluşturmadınız.",
        "cancel": "Formu iptal et",
        "cancelled": "Form iptal edildi.",
        "lang_changed": "✅ Dil değiştirildi.",
        "published": "✅ Gönderiniz yayımlandı.",
        "rejected": "❌ Gönderiniz onaylanmadı.",
    },
    "ar": {
        "select": "🌐 يرجى اختيار لغتك:",
        "city": "أدخل المدينة والمنطقة:",
        "type": "أدخل نوع العقار:",
        "area": "أدخل مساحة العقار:",
        "rooms": "أدخل عدد الغرف:",
        "price": "أدخل السعر أو الميزانية:",
        "details": "أدخل التفاصيل الإضافية:",
        "contact": "أدخل رقم التواصل:",
        "saved": "✅ تم إرسال معلوماتك إلى المدير للمراجعة.",
        "support": "أرسل رسالة الدعم:",
        "support_sent": "✅ تم إرسال رسالتك إلى المدير.",
        "menu_error": "يرجى استخدام أزرار القائمة.",
        "my_items": "📋 تسجيلاتك:",
        "empty": "لم ترسل أي تسجيل بعد.",
        "cancel": "إلغاء النموذج",
        "cancelled": "تم إلغاء النموذج.",
        "lang_changed": "✅ تم تغيير اللغة.",
        "published": "✅ تم نشر تسجيلك.",
        "rejected": "❌ لم تتم الموافقة على تسجيلك.",
    },
}

MENU_ITEMS = {
    "fa": [
        ["🏠 ثبت آگهی فروش", "🔑 ثبت آگهی اجاره"],
        ["🔎 درخواست خرید", "🏘 درخواست اجاره"],
        ["🤝 همکاری مشاوران", "🏗 سازنده و پروژه"],
        ["📋 آگهی‌های من", "🆘 پشتیبانی"],
        ["🌐 تغییر زبان"],
    ],
    "en": [
        ["🏠 Sell Property", "🔑 Rent Property"],
        ["🔎 Buy Request", "🏘 Rent Request"],
        ["🤝 Broker Cooperation", "🏗 Builder / Project"],
        ["📋 My Listings", "🆘 Support"],
        ["🌐 Change Language"],
    ],
    "az": [
        ["🏠 Satış elanı", "🔑 Kirayə elanı"],
        ["🔎 Alış sorğusu", "🏘 Kirayə sorğusu"],
        ["🤝 Əməkdaşlıq", "🏗 Tikinti layihəsi"],
        ["📋 Elanlarım", "🆘 Dəstək"],
        ["🌐 Dil dəyişdir"],
    ],
    "tr": [
        ["🏠 Satılık İlan", "🔑 Kiralık İlan"],
        ["🔎 Satın Alma Talebi", "🏘 Kiralama Talebi"],
        ["🤝 Danışman İş Birliği", "🏗 İnşaat Projesi"],
        ["📋 İlanlarım", "🆘 Destek"],
        ["🌐 Dil Değiştir"],
    ],
    "ar": [
        ["🏠 إعلان بيع", "🔑 إعلان إيجار"],
        ["🔎 طلب شراء", "🏘 طلب إيجار"],
        ["🤝 تعاون الوسطاء", "🏗 مشروع بناء"],
        ["📋 إعلاناتي", "🆘 الدعم"],
        ["🌐 تغيير اللغة"],
    ],
}

KINDS = {
    "sell": {
        "fa": "آگهی فروش",
        "en": "Property for sale",
        "az": "Satış elanı",
        "tr": "Satılık gayrimenkul",
        "ar": "عقار للبيع",
    },
    "rent": {
        "fa": "آگهی اجاره",
        "en": "Property for rent",
        "az": "Kirayə elanı",
        "tr": "Kiralık gayrimenkul",
        "ar": "عقار للإيجار",
    },
    "buy_request": {
        "fa": "درخواست خرید",
        "en": "Purchase request",
        "az": "Alış sorğusu",
        "tr": "Satın alma talebi",
        "ar": "طلب شراء",
    },
    "rent_request": {
        "fa": "درخواست اجاره",
        "en": "Rental request",
        "az": "Kirayə sorğusu",
        "tr": "Kiralama talebi",
        "ar": "طلب إيجار",
    },
    "broker": {
        "fa": "همکاری مشاوران",
        "en": "Broker cooperation",
        "az": "Əməkdaşlıq",
        "tr": "Danışman iş birliği",
        "ar": "تعاون الوسطاء",
    },
    "builder": {
        "fa": "سازنده و پروژه",
        "en": "Builder / project",
        "az": "Tikinti layihəsi",
        "tr": "İnşaat projesi",
        "ar": "مشروع بناء",
    },
}

FORM_FIELDS = ["city", "type", "area", "rooms", "price", "details", "contact"]

# ==================== لاگ ====================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("tehran-real-estate")


# ==================== دیتابیس ====================

def db():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with db() as conn:
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
    with db() as conn:
        conn.execute("""
            INSERT INTO users (user_id, language, full_name, username)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                language=excluded.language,
                full_name=excluded.full_name,
                username=excluded.username
        """, (
            user.id, language, user.full_name or "", user.username or ""
        ))


def get_user(user_id):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def create_submission(user_id, language, kind, data):
    with db() as conn:
        cursor = conn.execute("""
            INSERT INTO submissions (user_id, language, kind, data)
            VALUES (?, ?, ?, ?)
        """, (user_id, language, kind, json.dumps(data, ensure_ascii=False)))
        return cursor.lastrowid


def get_submission(submission_id):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM submissions WHERE id=?", (submission_id,)
        ).fetchone()
        return dict(row) if row else None


def set_status(submission_id, status):
    with db() as conn:
        conn.execute(
            "UPDATE submissions SET status=? WHERE id=?",
            (status, submission_id),
        )


def save_publication(submission_id, language, channel, status,
                     message_id=None, error=""):
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
        """, (
            submission_id, language, channel, status, message_id, error
        ))


# ==================== ترجمه ====================

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


async def translated_data(data, source, target):
    result = dict(data)
    for key in ("city", "type", "details"):
        value = str(data.get(key, "")).strip()
        if value:
            result[key] = await translate(value, target, source)
    return result


# ==================== صفحه‌کلید زبان ====================

def language_keyboard():
    # پرچم‌ها مستقیماً در متن هر دکمه قرار دارند.
    rows = [
        [LANGUAGES["fa"]["name"], LANGUAGES["en"]["name"]],
        [LANGUAGES["az"]["name"], LANGUAGES["tr"]["name"]],
        [LANGUAGES["ar"]["name"]],
    ]
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        one_time_keyboard=True,
        is_persistent=True,
    )


def main_keyboard(language):
    return ReplyKeyboardMarkup(
        MENU_ITEMS.get(language, MENU_ITEMS["fa"]),
        resize_keyboard=True,
        is_persistent=True,
    )


def parse_language(text):
    # تطبیق هم با پرچم و هم بدون پرچم؛ برای جلوگیری از مشکل کاراکترها.
    text = text.strip()
    for code, item in LANGUAGES.items():
        if text == item["name"] or text == item["native"]:
            return code
    return None


def language_prompt():
    return (
        "🌐 لطفاً زبان خود را انتخاب کنید:\n\n"
        "🌐 Please select your language:\n"
        "🌐 Zəhmət olmasa, dilinizi seçin:\n"
        "🌐 Lütfen dilinizi seçin:\n"
        "🌐 يرجى اختيار لغتك:"
    )


# ==================== شروع و انتخاب زبان ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    # شروع مجدد نباید فرم در حال تکمیل را ناخواسته پاک کند.
    await update.message.reply_text(
        language_prompt(),
        reply_markup=language_keyboard(),
    )


async def choose_language(update, context, language):
    user = update.effective_user
    save_user(user, language)

    # نکته مهم: context.user_data["form"] عمداً پاک نمی‌شود.
    form = context.user_data.get("form")
    if form:
        form["language"] = language

    await update.message.reply_text(
        WELCOME[language],
        reply_markup=main_keyboard(language),
    )

    if form:
        field = FORM_FIELDS[form["step"]]
        await update.message.reply_text(
            "📝 " + TEXT[language][field],
            reply_markup=main_keyboard(language),
        )


# ==================== نوع فرم ====================

KIND_BUTTONS = {
    "🏠 ثبت آگهی فروش": "sell",
    "🏠 Sell Property": "sell",
    "🏠 Satış elanı": "sell",
    "🏠 Satılık İlan": "sell",
    "🏠 إعلان بيع": "sell",

    "🔑 ثبت آگهی اجاره": "rent",
    "🔑 Rent Property": "rent",
    "🔑 Kirayə elanı": "rent",
    "🔑 Kiralık İlan": "rent",
    "🔑 إعلان إيجار": "rent",

    "🔎 درخواست خرید": "buy_request",
    "🔎 Buy Request": "buy_request",
    "🔎 Alış sorğusu": "buy_request",
    "🔎 Satın Alma Talebi": "buy_request",
    "🔎 طلب شراء": "buy_request",

    "🏘 درخواست اجاره": "rent_request",
    "🏘 Rent Request": "rent_request",
    "🏘 Kirayə sorğusu": "rent_request",
    "🏘 Kiralama Talebi": "rent_request",
    "🏘 طلب إيجار": "rent_request",

    "🤝 همکاری مشاوران": "broker",
    "🤝 Broker Cooperation": "broker",
    "🤝 Əməkdaşlıq": "broker",
    "🤝 Danışman İş Birliği": "broker",
    "🤝 تعاون الوسطاء": "broker",

    "🏗 سازنده و پروژه": "builder",
    "🏗 Builder / Project": "builder",
    "🏗 Tikinti layihəsi": "builder",
    "🏗 İnşaat Projesi": "builder",
    "🏗 مشروع بناء": "builder",
}

LANGUAGE_CHANGE_BUTTONS = {
    "🌐 تغییر زبان",
    "🌐 Change Language",
    "🌐 Dil dəyişdir",
    "🌐 Dil Değiştir",
    "🌐 تغيير اللغة",
}

SUPPORT_BUTTONS = {
    "🆘 پشتیبانی", "🆘 Support", "🆘 Dəstək",
    "🆘 Destek", "🆘 الدعم",
}

MY_LISTINGS_BUTTONS = {
    "📋 آگهی‌های من", "📋 My Listings", "📋 Elanlarım",
    "📋 İlanlarım", "📋 إعلاناتي",
}


async def begin_form(update, context, kind, language):
    context.user_data["form"] = {
        "kind": kind,
        "language": language,
        "step": 0,
        "data": {},
    }
    await update.message.reply_text(
        "📝 " + TEXT[language]["city"],
        reply_markup=main_keyboard(language),
    )


# ==================== ساخت متن آگهی ====================

async def render_submission(submission, language):
    data = json.loads(submission["data"])
    source = submission["language"]
    data = await translated_data(data, source, language)

    labels = {
        "fa": {
            "city": "شهر و منطقه", "type": "نوع ملک", "area": "متراژ",
            "rooms": "تعداد اتاق", "price": "قیمت یا بودجه",
            "details": "توضیحات", "contact": "شماره تماس",
        },
        "en": {
            "city": "City and area", "type": "Property type",
            "area": "Area", "rooms": "Rooms", "price": "Price or budget",
            "details": "Details", "contact": "Contact",
        },
        "az": {
            "city": "Şəhər və ərazi", "type": "Əmlak növü",
            "area": "Sahə", "rooms": "Otaq sayı", "price": "Qiymət",
            "details": "Ətraflı məlumat", "contact": "Əlaqə",
        },
        "tr": {
            "city": "Şehir ve bölge", "type": "Gayrimenkul türü",
            "area": "Metrekare", "rooms": "Oda sayısı", "price": "Fiyat",
            "details": "Açıklama", "contact": "İletişim",
        },
        "ar": {
            "city": "المدينة والمنطقة", "type": "نوع العقار",
            "area": "المساحة", "rooms": "عدد الغرف", "price": "السعر",
            "details": "التفاصيل", "contact": "التواصل",
        },
    }

    lines = [
        f"🏡 <b>{escape(KINDS[submission['kind']][language])}</b>",
        "",
    ]

    for field in FORM_FIELDS:
        value = str(data.get(field, "")).strip()
        if value:
            lines.append(
                f"<b>{escape(labels[language][field])}:</b> "
                f"{escape(value)}"
            )

    return "\n".join(lines)


# ==================== ارسال برای مدیر ====================

def admin_review_keyboard(submission_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ تأیید و انتخاب زبان انتشار",
            callback_data=f"approve:{submission_id}",
        )],
        [InlineKeyboardButton(
            "❌ رد آگهی",
            callback_data=f"reject:{submission_id}",
        )],
    ])


async def send_admin_review(context, submission_id):
    submission = get_submission(submission_id)
    if not submission:
        return

    user = get_user(submission["user_id"]) or {}

    # تمام نسخه‌های زبانی برای مدیر ارسال می‌شود.
    for language in LANG_CODES:
        try:
            body = await render_submission(submission, language)
            header = (
                f"📥 <b>ثبت جدید #{submission_id}</b>\n"
                f"👤 {escape(user.get('full_name', ''))}\n"
                f"🆔 <code>{submission['user_id']}</code>\n"
                f"🌐 زبان ثبت‌کننده: "
                f"{escape(LANGUAGES[submission['language']]['native'])}\n\n"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=header + body,
                parse_mode="HTML",
                reply_markup=(
                    admin_review_keyboard(submission_id)
                    if language == "fa" else None
                ),
            )
        except Exception:
            logger.exception(
                "ارسال نسخه %s برای مدیر ناموفق بود", language
            )


# ==================== انتخاب زبان انتشار توسط مدیر ====================

async def show_publication_languages(query, context, submission_id):
    selections = context.user_data.setdefault("publication_languages", {})
    selected = selections.setdefault(submission_id, ["fa"])

    keyboard = []
    for code in LANG_CODES:
        item = LANGUAGES[code]
        mark = "✅" if code in selected else "▫️"
        keyboard.append([
            InlineKeyboardButton(
                f"{mark} {item['name']}",
                callback_data=f"pubtoggle:{submission_id}:{code}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🚀 انتشار",
            callback_data=f"pubconfirm:{submission_id}",
        ),
        InlineKeyboardButton(
            "لغو",
            callback_data=f"pubcancel:{submission_id}",
        ),
    ])

    await query.edit_message_text(
        f"زبان‌های انتشار ثبت #{submission_id} را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def publish_submission(context, submission, language):
    channel = LANGUAGES[language]["channel"]

    with db() as conn:
        previous = conn.execute("""
            SELECT status FROM publications
            WHERE submission_id=? AND language=?
        """, (submission["id"], language)).fetchone()

    if previous and previous["status"] == "success":
        return "قبلاً منتشر شده است."

    body = await render_submission(submission, language)
    message = await context.bot.send_message(
        chat_id=channel,
        text=body,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

    save_publication(
        submission["id"],
        language,
        channel,
        "success",
        message_id=message.message_id,
    )
    return "منتشر شد."


# ==================== دکمه‌های مدیر ====================

async def admin_callback(update, context):
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "⛔ فقط مدیر اصلی دسترسی دارد.",
            show_alert=True,
        )
        return

    await query.answer()
    action = query.data

    if action.startswith("approve:"):
        submission_id = int(action.split(":")[1])
        if not get_submission(submission_id):
            await query.edit_message_text("ثبت پیدا نشد.")
            return
        await show_publication_languages(query, context, submission_id)
        return

    if action.startswith("reject:"):
        submission_id = int(action.split(":")[1])
        submission = get_submission(submission_id)
        if not submission:
            await query.edit_message_text("ثبت پیدا نشد.")
            return

        set_status(submission_id, "rejected")
        await query.edit_message_text(f"❌ ثبت #{submission_id} رد شد.")

        user = get_user(submission["user_id"])
        language = user["language"] if user else "fa"
        try:
            await context.bot.send_message(
                chat_id=submission["user_id"],
                text=TEXT[language]["rejected"],
            )
        except Exception:
            logger.exception("اطلاع‌رسانی رد آگهی ناموفق بود")
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
            await query.edit_message_text("ثبت پیدا نشد.")
            return

        selections = context.user_data.setdefault("publication_languages", {})
        languages = selections.pop(submission_id, ["fa"])

        if not languages:
            await query.edit_message_text(
                "حداقل یک زبان را انتخاب کنید."
            )
            return

        await query.edit_message_text("⏳ انتشار در حال انجام است...")
        report = []
        success_count = 0

        for language in languages:
            channel = LANGUAGES[language]["channel"]
            try:
                detail = await publish_submission(
                    context, submission, language
                )
                success_count += 1
                report.append(
                    f"✅ {LANGUAGES[language]['name']} — "
                    f"{channel}: {detail}"
                )
            except Exception as exc:
                logger.exception("انتشار در کانال ناموفق بود")
                save_publication(
                    submission_id,
                    language,
                    channel,
                    "failed",
                    error=str(exc)[:1000],
                )
                report.append(
                    f"❌ {LANGUAGES[language]['name']} — "
                    f"{channel}: {str(exc)[:250]}"
                )

        set_status(
            submission_id,
            "approved" if success_count else "pending",
        )

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"📊 گزارش انتشار #{submission_id}\n\n"
                + "\n".join(report)
                + f"\n\nموفق: {success_count}/{len(languages)}"
            ),
        )

        if success_count:
            user = get_user(submission["user_id"])
            language = user["language"] if user else "fa"
            try:
                await context.bot.send_message(
                    chat_id=submission["user_id"],
                    text=TEXT[language]["published"],
                )
            except Exception:
                logger.exception("اطلاع‌رسانی انتشار ناموفق بود")


# ==================== پیام‌های کاربر ====================

async def process_form(update, context):
    form = context.user_data.get("form")
    if not form:
        return False

    text = update.message.text.strip()
    language = form["language"]
    field = FORM_FIELDS[form["step"]]

    form["data"][field] = text
    form["step"] += 1

    if form["step"] < len(FORM_FIELDS):
        next_field = FORM_FIELDS[form["step"]]
        await update.message.reply_text(
            "📝 " + TEXT[language][next_field],
            reply_markup=main_keyboard(language),
        )
        return True

    submission_id = create_submission(
        update.effective_user.id,
        language,
        form["kind"],
        form["data"],
    )
    context.user_data.pop("form", None)

    await update.message.reply_text(
        TEXT[language]["saved"],
        reply_markup=main_keyboard(language),
    )
    await send_admin_review(context, submission_id)
    return True


async def show_user_submissions(update, user_id, language):
    with db() as conn:
        rows = conn.execute("""
            SELECT id, kind, status, created_at
            FROM submissions
            WHERE user_id=?
            ORDER BY id DESC LIMIT 20
        """, (user_id,)).fetchall()

    if not rows:
        await update.message.reply_text(TEXT[language]["empty"])
        return

    lines = [TEXT[language]["my_items"], ""]
    for row in rows:
        kind_name = KINDS.get(row["kind"], {}).get(language, row["kind"])
        lines.append(f"#{row['id']} — {kind_name} — {row['status']}")

    await update.message.reply_text("\n".join(lines))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    text = update.message.text.strip()

    # تغییر زبان باید قبل از دریافت پاسخ فرم بررسی شود.
    # فرم، اطلاعات قبلی و شماره مرحله در اینجا حفظ می‌شوند.
    language = parse_language(text)
    if language:
        await choose_language(update, context, language)
        return

    saved_user = get_user(user.id)
    if not saved_user:
        await update.message.reply_text(
            language_prompt(),
            reply_markup=language_keyboard(),
        )
        return

    current_language = saved_user["language"]

    if text in LANGUAGE_CHANGE_BUTTONS:
        await update.message.reply_text(
            language_prompt(),
            reply_markup=language_keyboard(),
        )
        return

    if text in SUPPORT_BUTTONS:
        context.user_data["awaiting_support"] = True
        await update.message.reply_text(
            TEXT[current_language]["support"],
            reply_markup=main_keyboard(current_language),
        )
        return

    if context.user_data.get("awaiting_support"):
        context.user_data["awaiting_support"] = False
        with db() as conn:
            conn.execute("""
                INSERT INTO support_messages (user_id, message)
                VALUES (?, ?)
            """, (user.id, text))

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🆘 پیام پشتیبانی از کاربر {user.id}:\n\n{text}",
        )
        await update.message.reply_text(
            TEXT[current_language]["support_sent"],
            reply_markup=main_keyboard(current_language),
        )
        return

    # اگر فرم فعال است، پاسخ این مرحله ثبت شود.
    if await process_form(update, context):
        return

    kind = KIND_BUTTONS.get(text)
    if kind:
        await begin_form(update, context, kind, current_language)
        return

    if text in MY_LISTINGS_BUTTONS:
        await show_user_submissions(update, user.id, current_language)
        return

    await update.message.reply_text(
        TEXT[current_language]["menu_error"],
        reply_markup=main_keyboard(current_language),
    )


# ==================== دستور مدیر ====================

async def admin_command(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ دسترسی ندارید.")
        return

    with db() as conn:
        pending = conn.execute("""
            SELECT COUNT(*) AS n FROM submissions WHERE status='pending'
        """).fetchone()["n"]
        total = conn.execute("""
            SELECT COUNT(*) AS n FROM submissions
        """).fetchone()["n"]

    await update.message.reply_text(
        f"🛠 پنل مدیر\n\n"
        f"📥 در انتظار بررسی: {pending}\n"
        f"📊 کل ثبت‌ها: {total}"
    )


# ==================== سرور سلامت Render ====================

web_app = Flask(__name__)


@web_app.get("/")
def home():
    return "Tehran Real Estate Bot is running.", 200


@web_app.get("/health")
def health():
    return {"status": "ok"}, 200


def run_web():
    port = int(os.getenv("PORT", "10000"))
    web_app.run(host="0.0.0.0", port=port)


# ==================== اجرای ربات ====================

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
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    logger.info("Tehran Real Estate bot started.")
    application.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
