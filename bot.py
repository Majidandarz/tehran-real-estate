import os
import json
import sqlite3
import logging
import asyncio
import re
from threading import Thread
from html import escape

import requests
from flask import Flask, jsonify
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
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
PORT = int(os.getenv("PORT", "10000"))

CHANNELS = {
    "fa": "@tehranrealstate",
    "en": "@tehranrealstate_en",
    "az": "@tehranrealstate_az",
    "tr": "@tehranrealstate_tr",
    "ar": "@tehranrealstate_ar",
    "zh": "@tehranrealstate_zh",
    "ru": "@tehranrealstate_ru",
}

LANG_NAMES = {
    "fa": "🇮🇷 فارسی",
    "en": "🇬🇧 English",
    "az": "🇦🇿 Azərbaycan dili",
    "tr": "🇹🇷 Türkçe",
    "ar": "🇸🇦 العربية",
    "zh": "🇨🇳 中文",
    "ru": "🇷🇺 Русский",
}

LANG_LABELS = dict(LANG_NAMES)

LANGUAGE_KEYBOARD = [
    [LANG_NAMES["fa"], LANG_NAMES["en"]],
    [LANG_NAMES["az"], LANG_NAMES["tr"]],
    [LANG_NAMES["ar"]],
    [LANG_NAMES["zh"], LANG_NAMES["ru"]],
]

WELCOME = {
    "fa": """🏡✨ به گروه بزرگ مشاورین املاک تهران خوش آمدید! ✨🏡

🌟 مجموعه مشاورین املاک تهران با بیش از ۲۰ سال سابقه فعالیت، گسترده‌ترین شبکه اطلاعات ملکی در ایران و بیش از ۱۰۰۰ مشاور فعال در سراسر کشور، در کنار شماست.

🤝 هدف پرسنل و مدیریت مجموعه، جلب رضایت شما مشتریان عزیز و ارائه خدماتی شایسته، مطمئن و حرفه‌ای است.

🌹 امیدواریم تجربه‌ای رضایت‌بخش و همکاری ارزشمندی را در کنار ما داشته باشید.

💠 املاک تهران؛ همراه شما در مسیر انتخابی مطمئن. 💠""",
    "en": """🏡✨ Welcome to the Tehran Real Estate Group! ✨🏡

🌟 With over 20 years of experience, an extensive property information network in Iran, and more than 1,000 active consultants nationwide, we are here to help you.

🤝 Our staff and management are committed to customer satisfaction and providing services that are reliable, professional, and worthy of your trust.

🌹 We hope you enjoy a satisfying experience and a valuable partnership with us.

💠 Tehran Real Estate — your trusted companion on the path to making a confident choice. 💠""",
    "az": """🏡✨ Tehran Daşınmaz Əmlak Məsləhətçiləri Qrupuna xoş gəlmisiniz! ✨🏡

🌟 20 ildən artıq fəaliyyət təcrübəmiz, İranda ən geniş daşınmaz əmlak məlumat şəbəkəmiz və ölkə üzrə 1.000-dən çox fəal məsləhətçimizlə sizin yanınızdayıq.

🤝 Əməkdaşlarımızın və rəhbərliyimizin məqsədi müştərilərimizin məmnuniyyətini qazanmaq, layiqli, etibarlı və peşəkar xidmət göstərməkdir.

🌹 Sizinlə məmnunedici təcrübə və dəyərli əməkdaşlıq qurmağı arzulayırıq.

💠 Tehran Daşınmaz Əmlak — düzgün və etibarlı seçim yolunda sizin tərəfdaşınız. 💠""",
    "tr": """🏡✨ Tahran Gayrimenkul Danışmanları Grubuna hoş geldiniz! ✨🏡

🌟 20 yılı aşkın faaliyet deneyimimiz, İran'ın en geniş gayrimenkul bilgi ağımız ve ülke genelinde 1.000'den fazla aktif danışmanımızla yanınızdayız.

🤝 Ekibimizin ve yönetimimizin amacı müşteri memnuniyetini sağlamak, güvenilir, profesyonel ve size layık hizmet sunmaktır.

🌹 Bizimle memnuniyet verici bir deneyim ve değerli bir iş birliği yaşamanızı dileriz.

💠 Tahran Gayrimenkul — güvenilir bir seçim yapma yolunda yanınızda. 💠""",
    "ar": """🏡✨ أهلاً وسهلاً بكم في مجموعة مستشاري عقارات طهران! ✨🏡

🌟 بخبرة تزيد على 20 عاماً في هذا المجال، وأوسع شبكة لمعلومات العقارات في إيران، وأكثر من 1,000 مستشار نشط في جميع أنحاء البلاد، نحن إلى جانبكم.

🤝 يهدف فريق العمل والإدارة إلى تحقيق رضا عملائنا الكرام وتقديم خدمات جديرة بالثقة وموثوقة واحترافية.

🌹 نتمنى لكم تجربة مرضية وتعاوناً قيّماً ومثمراً معنا.

💠 عقارات طهران — رفيقكم الموثوق في طريق الاختيار بثقة. 💠""",
    "zh": """🏡✨ 欢迎加入德黑兰房地产顾问集团！✨🏡

🌟 我们拥有超过20年的行业经验、覆盖伊朗的房地产信息网络，以及遍布全国的1000多名活跃顾问。

🤝 我们致力于客户满意度，并提供可靠、专业的服务。

🌹 期待与您建立愉快而有价值的合作关系。

💠 德黑兰房地产——陪伴您做出安心的选择。💠""",
    "ru": """🏡✨ Добро пожаловать в группу специалистов по недвижимости Тегерана! ✨🏡

🌟 Более 20 лет опыта, широкая сеть информации о недвижимости в Иране и более 1000 активных консультантов по всей стране.

🤝 Наша цель — удовлетворение потребностей клиентов и предоставление надежных профессиональных услуг.

🌹 Надеемся на успешное и плодотворное сотрудничество с вами.

💠 Недвижимость Тегерана — ваш надежный партнер в выборе недвижимости. 💠""",
}

MENU = {
    "fa": [
        ["🏠 ثبت آگهی فروش", "🔑 ثبت آگهی اجاره"],
        ["🔎 درخواست خرید", "🏘 درخواست اجاره"],
        ["🤝 همکاری مشاوران", "🏗 مشارکت در ساخت"],
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
    "zh": [
        ["🏠 发布出售房源", "🔑 发布出租房源"],
        ["🔎 求购房产", "🏘 求租房产"],
        ["🤝 经纪人合作", "🏗 开发商与项目"],
        ["📋 我的房源", "📨 我的需求"],
        ["🆘 客服支持", "🌐 更改语言"],
    ],
    "ru": [
        ["🏠 Продать недвижимость", "🔑 Сдать в аренду"],
        ["🔎 Запрос на покупку", "🏘 Запрос на аренду"],
        ["🤝 Сотрудничество брокеров", "🏗 Застройщик / Проект"],
        ["📋 Мои объявления", "📨 Мои запросы"],
        ["🆘 Поддержка", "🌐 Сменить язык"],
    ],
}

FIELDS = ["city", "property_type", "area", "rooms", "price", "details", "contact"]

FIELD_LABELS = {
    "fa": {"city": "شهر و منطقه", "property_type": "نوع ملک", "area": "متراژ", "rooms": "تعداد اتاق", "price": "قیمت یا بودجه", "details": "توضیحات", "contact": "شماره تماس"},
    "en": {"city": "City and area", "property_type": "Property type", "area": "Area", "rooms": "Number of rooms", "price": "Price or budget", "details": "Details", "contact": "Contact number"},
    "az": {"city": "Şəhər və ərazi", "property_type": "Əmlak növü", "area": "Sahə", "rooms": "Otaq sayı", "price": "Qiymət və ya büdcə", "details": "Ətraflı məlumat", "contact": "Əlaqə nömrəsi"},
    "tr": {"city": "Şehir ve bölge", "property_type": "Gayrimenkul türü", "area": "Metrekare", "rooms": "Oda sayısı", "price": "Fiyat veya bütçe", "details": "Açıklama", "contact": "İletişim numarası"},
    "ar": {"city": "المدينة والمنطقة", "property_type": "نوع العقار", "area": "المساحة", "rooms": "عدد الغرف", "price": "السعر أو الميزانية", "details": "التفاصيل", "contact": "رقم التواصل"},
    "zh": {"city": "城市和区域", "property_type": "房产类型", "area": "面积", "rooms": "房间数量", "price": "价格或预算", "details": "详细说明", "contact": "联系电话"},
    "ru": {"city": "Город и район", "property_type": "Тип недвижимости", "area": "Площадь", "rooms": "Количество комнат", "price": "Цена или бюджет", "details": "Описание", "contact": "Контактный номер"},
}

KINDS = {
    "sell_ad": {"fa": "آگهی فروش", "en": "Property for sale", "az": "Satış elanı", "tr": "Satılık gayrimenkul", "ar": "عقار للبيع", "zh": "出售房产", "ru": "Продажа недвижимости"},
    "rent_ad": {"fa": "آگهی اجاره", "en": "Property for rent", "az": "Kirayə elanı", "tr": "Kiralık gayrimenkul", "ar": "عقار للإيجار", "zh": "出租房产", "ru": "Аренда недвижимости"},
    "rent_office_ad": {"fa": "آگهی اجاره اداری", "en": "Office property for rent", "az": "İcarəyə verilən ofis", "tr": "Kiralık ofis", "ar": "مكتب للإيجار", "zh": "出租办公房产", "ru": "Аренда офисной недвижимости"},
    "buy_req": {"fa": "درخواست خرید", "en": "Property purchase request", "az": "Alış sorğusu", "tr": "Satın alma talebi", "ar": "طلب شراء عقار", "zh": "求购房产", "ru": "Запрос на покупку"},
    "rent_req": {"fa": "درخواست اجاره", "en": "Rental request", "az": "Kirayə sorğusu", "tr": "Kiralama talebi", "ar": "طلب استئجار عقار", "zh": "求租房产", "ru": "Запрос на аренду"},
    "broker_ad": {"fa": "همکاری مشاوران", "en": "Broker cooperation", "az": "Əmlak məsləhətçilərinin əməkdaşlığı", "tr": "Danışman iş birliği", "ar": "تعاون الوسطاء العقاريين", "zh": "经纪人合作", "ru": "Сотрудничество брокеров"},
    "builder": {"fa": "پروژه سازنده", "en": "Builder / development project", "az": "Tikinti layihəsi", "tr": "İnşaat projesi", "ar": "مشروع بناء", "zh": "开发商项目", "ru": "Проект застройщика"},
}

# ==================== LOGGING ====================

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
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
        """, (user.id, language, user.full_name or "", user.username or ""))


def get_user(user_id):
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def create_submission(user_id, language, kind, data):
    with connect_db() as conn:
        cursor = conn.execute(
            "INSERT INTO submissions (user_id, language, kind, data) VALUES (?, ?, ?, ?)",
            (user_id, language, kind, json.dumps(data, ensure_ascii=False)),
        )
        return cursor.lastrowid


def get_submission(submission_id):
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
        return dict(row) if row else None


def set_submission_status(submission_id, status):
    with connect_db() as conn:
        conn.execute("UPDATE submissions SET status=? WHERE id=?", (status, submission_id))


def record_publication(submission_id, language, channel, status, message_id=None, error=""):
    with connect_db() as conn:
        conn.execute("""
            INSERT INTO publications (submission_id, language, channel, status, message_id, error)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(submission_id, language) DO UPDATE SET
                channel=excluded.channel, status=excluded.status,
                message_id=excluded.message_id, error=excluded.error,
                created_at=CURRENT_TIMESTAMP
        """, (submission_id, language, channel, status, message_id, error))


# ==================== TRANSLATION ====================

def translate_sync(text, target, source=None):
    if not text or target == source:
        return text
    if not GOOGLE_TRANSLATE_API_KEY:
        raise RuntimeError("GOOGLE_TRANSLATE_API_KEY تنظیم نشده است.")
    payload = {"q": text, "target": target, "format": "text"}
    if source:
        payload["source"] = source
    response = requests.post(
        "https://translation.googleapis.com/language/translate/v2",
        params={"key": GOOGLE_TRANSLATE_API_KEY}, json=payload, timeout=25,
    )
    response.raise_for_status()
    return response.json()["data"]["translations"][0]["translatedText"]


async def translate(text, target, source=None):
    if not text or target == source:
        return text
    return await asyncio.to_thread(translate_sync, text, target, source)


async def translate_submission_data(data, source, target):
    result = dict(data)
    for key in ("city", "property_type", "details", "rental_category", "document_type", "office_property_type", "elevator", "lobby"):
        value = str(data.get(key, "")).strip()
        if value:
            result[key] = await translate(value, target, source)
    return result


# ==================== KEYBOARDS ====================

def language_keyboard():
    return ReplyKeyboardMarkup(LANGUAGE_KEYBOARD, resize_keyboard=True, one_time_keyboard=True, is_persistent=True)


def main_keyboard(language):
    return ReplyKeyboardMarkup(MENU.get(language, MENU["fa"]), resize_keyboard=True, is_persistent=True)


def submenu_keyboard(options, back_label="⬅️ بازگشت به منوی اصلی"):
    rows = [[option] for option in options]
    rows.append([back_label])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def parse_language(text):
    text = (text or "").strip()
    normalized = text
    for flag in ("🇮🇷", "🇬🇧", "🇦🇿", "🇹🇷", "🇸🇦", "🇨🇳", "🇷🇺"):
        normalized = normalized.replace(flag, "")
    normalized = normalized.strip()
    aliases = {
        "فارسی": "fa", "English": "en", "Azərbaycan dili": "az",
        "Türkçe": "tr", "العربية": "ar", "中文": "zh", "Русский": "ru",
    }
    if normalized in aliases:
        return aliases[normalized]
    for code, label in LANG_NAMES.items():
        if text == label:
            return code
    return None


def language_prompt():
    return (
        "🌐 لطفاً زبان خود را انتخاب کنید:\n\n"
        "🌐 Please select your language:\n"
        "🌐 Zəhmət olmasa, dilinizi seçin:\n"
        "🌐 Lütfen dilinizi seçin:\n"
        "🌐 يرجى اختيار لغتك:\n"
        "🌐 请选择您的语言：\n"
        "🌐 Пожалуйста, выберите язык:"
    )


# ==================== START AND LANGUAGE ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    context.user_data.pop("form", None)
    context.user_data.pop("awaiting_support", None)
    context.user_data.pop("rent_menu", None)
    await update.message.reply_text(language_prompt(), reply_markup=language_keyboard())


async def choose_language(update, context, language):
    user = update.effective_user
    if not user or not update.message:
        return
    context.user_data.pop("form", None)
    context.user_data.pop("awaiting_support", None)
    context.user_data.pop("rent_menu", None)
    save_user(user, language)
    await update.message.reply_text(WELCOME[language], reply_markup=main_keyboard(language))


# ==================== FORM ROUTING ====================

def detect_kind(text):
    mapping = {
        "🏠 ثبت آگهی فروش": "sell_ad", "🏠 Sell Property": "sell_ad",
        "🏠 Satış elanı": "sell_ad", "🏠 Satılık İlan": "sell_ad",
        "🏠 إعلان بيع": "sell_ad", "🏠 发布出售房源": "sell_ad",
        "🏠 Продать недвижимость": "sell_ad",
        "🔑 ثبت آگهی اجاره": "rent_ad", "🔑 Rent Property": "rent_ad",
        "🔑 Kirayə elanı": "rent_ad", "🔑 Kiralık İlan": "rent_ad",
        "🔑 إعلان إيجار": "rent_ad", "🔑 发布出租房源": "rent_ad",
        "🔑 Сдать в аренду": "rent_ad",
        "🔎 درخواست خرید": "buy_req", "🔎 Buy Request": "buy_req",
        "🔎 Alış sorğusu": "buy_req", "🔎 Satın Alma Talebi": "buy_req",
        "🔎 طلب شراء": "buy_req", "🔎 求购房产": "buy_req",
        "🔎 Запрос на покупку": "buy_req",
        "🏘 درخواست اجاره": "rent_req", "🏘 Rent Request": "rent_req",
        "🏘 Kirayə sorğusu": "rent_req", "🏘 Kiralama Talebi": "rent_req",
        "🏘 طلب إيجار": "rent_req", "🏘 求租房产": "rent_req",
        "🏘 Запрос на аренду": "rent_req",
        "🤝 همکاری مشاوران": "broker_ad", "🤝 Broker Cooperation": "broker_ad",
        "🤝 Əməkdaşlıq": "broker_ad", "🤝 Danışman İş Birliği": "broker_ad",
        "🤝 تعاون الوسطاء": "broker_ad", "🤝 经纪人合作": "broker_ad",
        "🤝 Сотрудничество брокеров": "broker_ad",
        "🏗 مشارکت در ساخت": "builder", "🏗 سازنده و پروژه": "builder",
        "🏗 Builder / Project": "builder", "🏗 Tikinti layihəsi": "builder",
        "🏗 İnşaat Projesi": "builder", "🏗 مشروع بناء": "builder",
        "🏗 开发商与项目": "builder", "🏗 Застройщик / Проект": "builder",
    }
    return mapping.get(text)


RENT_CATEGORY_BUTTONS = {
    "اداری", "مسکونی", "صنعتی", "تجاری",
    "Office", "Residential", "Industrial", "Commercial",
    "Ofis", "Yaşayış", "Sənaye", "Kommersiya",
    "Ofis", "Konut", "Sanayi", "Ticari",
    "مكتبي", "سكني", "صناعي", "تجاري",
    "办公", "住宅", "工业", "商业",
    "Офисная", "Жилая", "Промышленная", "Коммерческая",
}
RENT_CATEGORY_MAP = {
    "اداری": "اداری", "مسکونی": "مسکونی", "صنعتی": "صنعتی", "تجاری": "تجاری",
    "Office": "اداری", "Residential": "مسکونی", "Industrial": "صنعتی", "Commercial": "تجاری",
    "Ofis": "اداری", "Yaşayış": "مسکونی", "Sənaye": "صنعتی", "Kommersiya": "تجاری",
    "Konut": "مسکونی", "Sanayi": "صنعتی", "Ticari": "تجاری",
    "مكتبي": "اداری", "سكني": "مسکونی", "صناعي": "صنعتی", "تجاري": "تجاری",
    "办公": "اداری", "住宅": "مسکونی", "工业": "صنعتی", "商业": "تجاری",
    "Офисная": "اداری", "Жилая": "مسکونی", "Промышленная": "صنعتی", "Коммерческая": "تجاری",
}
BACK_BUTTONS = {"⬅️ بازگشت به منوی اصلی", "⬅️ Back to Main Menu", "⬅️ Ana menüyə qayıt", "⬅️ Ana menüye dön", "⬅️ العودة إلى القائمة الرئيسية", "⬅️ 返回主菜单", "⬅️ Вернуться в главное меню"}
CHOICE_BACK = "⬅️ بازگشت"
OFFICE_CHOICE_BUTTONS = {"سند اداری", "موقعیت اداری", "هر دو", "آپارتمان", "مستغلات", "هر دو مورد"}
BOOL_BUTTONS = {"دارد", "ندارد"}
CONTACT_BUTTONS = {"📱 اشتراک‌گذاری شماره تلگرام", "📱 Share Telegram phone number"}
CANCEL_FORM_BUTTONS = {"❌ لغو ثبت"}

async def begin_form(update, context, kind, language):
    context.user_data["awaiting_support"] = False
    context.user_data.pop("rent_menu", None)
    context.user_data["form"] = {
        "kind": kind, "language": language, "step": 0, "data": {},
        "mode": "office_rent" if kind == "rent_office_ad" else "standard",
        "images": [],
    }
    if kind == "rent_ad":
        context.user_data["rent_menu"] = True
        await update.message.reply_text(
            "نوع آگهی اجاره را انتخاب کنید:",
            reply_markup=submenu_keyboard(["اداری", "مسکونی", "صنعتی", "تجاری"]),
        )
        context.user_data.pop("form", None)
        return
    if kind == "rent_office_ad":
        await begin_office_rent_form(update, context, language)
        return
    await update.message.reply_text(
        f"📝 {FIELD_LABELS[language]['city']}:",
        reply_markup=main_keyboard(language),
    )


OFFICE_STEPS = [
    ("office_document_type", "نوع سند/موقعیت اداری را انتخاب کنید:", ["سند اداری", "موقعیت اداری", "هر دو"]),
    ("office_property_type", "نوع ملک را انتخاب کنید:", ["آپارتمان", "مستغلات", "هر دو"]),
    ("area", "متراژ ملک را فقط با عدد وارد کنید:"),
    ("parking", "تعداد پارکینگ را فقط با عدد وارد کنید:"),
    ("rooms", "تعداد اتاق را فقط با عدد وارد کنید:"),
    ("elevator", "آسانسور دارد؟", ["دارد", "ندارد"]),
    ("lobby", "لابی دارد؟", ["دارد", "ندارد"]),
    ("city", "شهر را فقط با حروف وارد کنید:"),
    ("municipal_district", "منطقه شهرداری را فقط با عدد وارد کنید:"),
    ("street", "نام خیابان را فقط با حروف وارد کنید:"),
    ("alley", "نام کوچه یا خیابان فرعی را وارد کنید (عدد و حروف مجاز است):"),
    ("plaque", "شماره پلاک را فقط با عدد وارد کنید:"),
    ("deposit", "مبلغ رهن را فقط با عدد وارد کنید:"),
    ("rent", "مبلغ اجاره ماهانه را فقط با عدد وارد کنید:"),
    ("images", "حداقل ۴ تصویر ملک را ارسال کنید. پس از ارسال ۴ تصویر یا بیشتر، عبارت «پایان تصاویر» را بفرستید."),
    ("contact", "برای ثبت شماره تماس، دکمه اشتراک‌گذاری شماره تلفن را بزنید."),
]

async def begin_office_rent_form(update, context, language):
    context.user_data["rent_menu"] = False
    context.user_data["form"] = {
        "kind": "rent_office_ad",
        "language": language,
        "step": 0,
        "data": {},
        "mode": "office_rent",
        "images": [],
    }
    await ask_office_step(update.message, context)


async def ask_office_step(message, context):
    form = context.user_data.get("form")
    if not form:
        return
    step = form["step"]
    key, prompt, *options = OFFICE_STEPS[step]
    if key == "contact":
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 اشتراک‌گذاری شماره تلگرام", request_contact=True)],
             ["❌ لغو ثبت"]],
            resize_keyboard=True,
            is_persistent=True,
        )
    elif key == "images":
        keyboard = ReplyKeyboardMarkup([["پایان تصاویر"], ["❌ لغو ثبت"]], resize_keyboard=True, is_persistent=True)
    elif options:
        keyboard = submenu_keyboard(options[0], "❌ لغو ثبت")
    else:
        keyboard = ReplyKeyboardMarkup([["❌ لغو ثبت"]], resize_keyboard=True, is_persistent=True)
    await message.reply_text(prompt, reply_markup=keyboard)


def digits_only(value):
    value = (value or "").strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    return bool(value) and value.isdigit()


def letters_only(value):
    value = (value or "").strip()
    return bool(value) and any(ch.isalpha() for ch in value) and all(ch.isalpha() or ch.isspace() or ch in "-'’" for ch in value)


async def process_office_rent(update, context):
    form = context.user_data.get("form")
    if not form or form.get("mode") != "office_rent":
        return False
    message = update.message
    if not message:
        return False
    text = (message.text or "").strip()
    language = form["language"]

    if text in CANCEL_FORM_BUTTONS:
        context.user_data.pop("form", None)
        await message.reply_text("ثبت آگهی لغو شد.", reply_markup=main_keyboard(language))
        return True

    if message.contact:
        if OFFICE_STEPS[form["step"]][0] != "contact":
            await message.reply_text("لطفاً در مرحله درخواست‌شده پاسخ دهید.")
            return True
        form["data"]["contact"] = message.contact.phone_number
        form["data"]["telegram_user_id"] = message.contact.user_id or update.effective_user.id
        form["data"]["telegram_username"] = update.effective_user.username or ""
        await finish_office_rent(update, context)
        return True

    key = OFFICE_STEPS[form["step"]][0]

    if key == "images":
        if message.photo:
            file_id = message.photo[-1].file_id
            form["images"].append(file_id)
            form["data"]["images"] = list(form["images"])
            await message.reply_text(
                f"تصویر دریافت شد. تعداد تصاویر: {len(form['images'])}\n"
                + ("اکنون «پایان تصاویر» را بفرستید یا تصویر بیشتری ارسال کنید." if len(form["images"]) >= 4 else f"حداقل {4-len(form['images'])} تصویر دیگر لازم است."),
                reply_markup=ReplyKeyboardMarkup([["پایان تصاویر"], ["❌ لغو ثبت"]], resize_keyboard=True, is_persistent=True),
            )
            return True
        if text == "پایان تصاویر":
            if len(form["images"]) < 4:
                await message.reply_text(f"حداقل ۴ تصویر لازم است. تاکنون {len(form['images'])} تصویر ارسال کرده‌اید.")
                return True
            form["step"] += 1
            await ask_office_step(message, context)
            return True
        await message.reply_text("لطفاً تصویر ملک ارسال کنید یا پس از ارسال حداقل ۴ تصویر، «پایان تصاویر» را بفرستید.")
        return True

    if not text:
        await message.reply_text("لطفاً پاسخ را به‌صورت متن یا با دکمه مناسب ارسال کنید.")
        return True

    if key in {"office_document_type", "office_property_type", "elevator", "lobby"}:
        allowed = OFFICE_STEPS[form["step"]][2]
        if text not in allowed:
            await message.reply_text("لطفاً یکی از گزینه‌های نمایش‌داده‌شده را انتخاب کنید.")
            return True
        form["data"][key] = text
    elif key in {"area", "parking", "rooms", "municipal_district", "plaque", "deposit", "rent"}:
        if not digits_only(text):
            await message.reply_text("ورودی این مرحله باید فقط عدد باشد. لطفاً دوباره وارد کنید.")
            return True
        form["data"][key] = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    elif key in {"city", "street"}:
        if not letters_only(text):
            await message.reply_text("لطفاً فقط حروف وارد کنید؛ از عدد و نشانه استفاده نکنید.")
            return True
        form["data"][key] = text
    elif key == "alley":
        if not any(ch.isalnum() or ch.isalpha() for ch in text):
            await message.reply_text("نام کوچه یا خیابان فرعی را با حروف یا عدد وارد کنید.")
            return True
        form["data"][key] = text
    else:
        form["data"][key] = text

    form["step"] += 1
    if form["step"] < len(OFFICE_STEPS):
        await ask_office_step(message, context)
    else:
        await finish_office_rent(update, context)
    return True


async def finish_office_rent(update, context):
    form = context.user_data.get("form")
    if not form:
        return
    submission_id = create_submission(
        update.effective_user.id,
        form["language"],
        form["kind"],
        form["data"],
    )
    language = form["language"]
    context.user_data.pop("form", None)
    confirmations = {
        "fa": f"✅ آگهی اجاره اداری شما با کد پیگیری {submission_id} ثبت شد و برای بررسی مدیر ارسال می‌شود.",
        "en": f"✅ Your office rental listing #{submission_id} was submitted for admin review.",
        "az": f"✅ Ofis icarə elanınız #{submission_id} nömrəsi ilə yoxlanışa göndərildi.",
        "tr": f"✅ Ofis kiralama ilanınız #{submission_id} numarasıyla incelemeye gönderildi.",
        "ar": f"✅ تم إرسال إعلان المكتب للإيجار رقم {submission_id} للمراجعة.",
        "zh": f"✅ 您的办公出租房源 #{submission_id} 已提交审核。",
        "ru": f"✅ Объявление об аренде офиса #{submission_id} отправлено на проверку.",
    }
    await update.message.reply_text(confirmations.get(language, confirmations["fa"]), reply_markup=main_keyboard(language))
    await send_admin_review(context, submission_id)


async def begin_form(update, context, kind, language):
    context.user_data["awaiting_support"] = False
    context.user_data.pop("rent_menu", None)
    if kind == "rent_ad":
        context.user_data.pop("form", None)
        context.user_data["rent_menu"] = True
        await update.message.reply_text(
            "نوع آگهی اجاره را انتخاب کنید:",
            reply_markup=submenu_keyboard(["اداری", "مسکونی", "صنعتی", "تجاری"]),
        )
        return
    if kind == "rent_office_ad":
        await begin_office_rent_form(update, context, language)
        return
    context.user_data["form"] = {"kind": kind, "language": language, "step": 0, "data": {}, "mode": "standard"}
    await update.message.reply_text(f"📝 {FIELD_LABELS[language]['city']}:", reply_markup=main_keyboard(language))


# ==================== ADMIN REVIEW ====================

def review_keyboard(submission_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید و انتخاب زبان انتشار", callback_data=f"approve:{submission_id}")],
        [InlineKeyboardButton("❌ رد", callback_data=f"reject:{submission_id}")],
    ])


async def render_submission(data, kind, language, source_language):
    translated = await translate_submission_data(data, source_language, language)
    lines = [f"🏡 <b>{escape(KINDS.get(kind, KINDS['rent_ad']).get(language, KINDS.get(kind, KINDS['rent_ad'])['fa']))}</b>", ""]
    if kind == "rent_office_ad":
        labels = {
            "office_document_type": "سند/موقعیت اداری",
            "office_property_type": "نوع ملک اداری",
            "area": "متراژ",
            "parking": "تعداد پارکینگ",
            "rooms": "تعداد اتاق",
            "elevator": "آسانسور",
            "lobby": "لابی",
            "city": "شهر",
            "municipal_district": "منطقه شهرداری",
            "street": "خیابان",
            "alley": "کوچه/خیابان فرعی",
            "plaque": "پلاک",
            "deposit": "مبلغ رهن",
            "rent": "مبلغ اجاره ماهانه",
            "contact": "شماره تلفن",
            "telegram_username": "نام کاربری تلگرام",
        }
        for key, label in labels.items():
            value = str(translated.get(key, "")).strip()
            if value:
                lines.append(f"<b>{escape(label)}:</b> {escape(value)}")
        image_count = len(data.get("images", []))
        lines.append(f"<b>تعداد تصاویر:</b> {image_count}")
        for index, file_id in enumerate(data.get("images", []), start=1):
            lines.append(f"<b>شناسه تصویر {index}:</b> <code>{escape(file_id)}</code>")
    else:
        for field in FIELDS:
            value = str(translated.get(field, "")).strip()
            if value:
                lines.append(f"<b>{escape(FIELD_LABELS[language][field])}:</b> {escape(value)}")
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
            body = await render_submission(data, submission["kind"], language, source_language)
            header = (
                f"📥 <b>ثبت جدید #{submission_id}</b>\n"
                f"👤 {escape(user.get('full_name', ''))}\n"
                f"🆔 <code>{submission['user_id']}</code>\n"
                f"🌐 زبان ثبت‌کننده: {escape(LANG_LABELS[source_language])}\n"
                f"📌 وضعیت: در انتظار بررسی\n\n"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID, text=header + body, parse_mode="HTML",
                reply_markup=review_keyboard(submission_id) if language == "fa" else None,
            )
        except Exception as exc:
            logger.exception("Admin review translation/send failed for %s", language)
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"⚠️ ارسال نسخه {LANG_LABELS[language]} برای ثبت #{submission_id} ناموفق بود.\n{str(exc)[:500]}",
                )
            except Exception:
                logger.exception("Could not report admin review failure")

    # ارسال تصاویر واقعی ملک برای مدیر، علاوه بر متن بررسی
    if submission["kind"] == "rent_office_ad":
        image_ids = data.get("images", [])
        if image_ids:
            try:
                from telegram import InputMediaPhoto
                media = [InputMediaPhoto(media=file_id) for file_id in image_ids[:10]]
                await context.bot.send_media_group(chat_id=ADMIN_ID, media=media)
            except Exception:
                logger.exception("Could not send office listing photos to admin")


# ==================== CHANNEL PUBLICATION ====================

async def publish_submission(context, submission, language):
    submission_id = submission["id"]
    channel = CHANNELS[language]
    with connect_db() as conn:
        previous = conn.execute(
            "SELECT status FROM publications WHERE submission_id=? AND language=?",
            (submission_id, language),
        ).fetchone()
    if previous and previous["status"] == "success":
        return True, "قبلاً منتشر شده است."
    data = json.loads(submission["data"])
    message_text = await render_submission(data, submission["kind"], language, submission["language"])
    message = await context.bot.send_message(
        chat_id=channel, text=message_text, parse_mode="HTML", disable_web_page_preview=True,
    )
    if submission["kind"] == "rent_office_ad":
        image_ids = data.get("images", [])
        if image_ids:
            from telegram import InputMediaPhoto
            media = [InputMediaPhoto(media=file_id) for file_id in image_ids[:10]]
            await context.bot.send_media_group(chat_id=channel, media=media)
    record_publication(submission_id, language, channel, "success", message_id=message.message_id)
    return True, "منتشر شد."


async def show_publication_languages(query, context, submission_id):
    selections = context.user_data.setdefault("publication_languages", {})
    selections.setdefault(submission_id, ["fa"])
    selected = selections[submission_id]
    keyboard = []
    for language, label in LANG_NAMES.items():
        mark = "✅" if language in selected else "▫️"
        keyboard.append([InlineKeyboardButton(f"{mark} {label}", callback_data=f"pubtoggle:{submission_id}:{language}")])
    keyboard.append([
        InlineKeyboardButton("🚀 تأیید و انتشار", callback_data=f"pubconfirm:{submission_id}"),
        InlineKeyboardButton("لغو", callback_data=f"pubcancel:{submission_id}"),
    ])
    await query.edit_message_text(
        f"🌐 زبان‌های انتشار ثبت #{submission_id} را انتخاب کنید.\nمی‌توانید چند زبان را هم‌زمان انتخاب کنید.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ فقط مدیر اصلی دسترسی دارد.", show_alert=True)
        return
    await query.answer()
    action = query.data or ""

    if action.startswith("approve:"):
        submission_id = int(action.split(":")[1])
        submission = get_submission(submission_id)
        if not submission:
            await query.edit_message_text("❌ ثبت موردنظر پیدا نشد.")
            return
        if submission["status"] == "rejected":
            await query.edit_message_text("❌ این ثبت قبلاً رد شده است.")
            return
        await show_publication_languages(query, context, submission_id)
        return

    if action.startswith("reject:"):
        submission_id = int(action.split(":")[1])
        submission = get_submission(submission_id)
        if not submission:
            await query.edit_message_text("❌ ثبت موردنظر پیدا نشد.")
            return
        set_submission_status(submission_id, "rejected")
        context.user_data.setdefault("publication_languages", {}).pop(submission_id, None)
        await query.edit_message_text(f"❌ ثبت #{submission_id} رد شد.")
        try:
            await context.bot.send_message(chat_id=submission["user_id"], text="❌ ثبت شما پس از بررسی تأیید نشد.")
        except Exception:
            logger.exception("Could not notify submitter")
        return

    if action.startswith("pubtoggle:"):
        _, raw_id, language = action.split(":")
        submission_id = int(raw_id)
        if language not in CHANNELS:
            await query.answer("زبان انتخاب‌شده معتبر نیست.", show_alert=True)
            return
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
        context.user_data.setdefault("publication_languages", {}).pop(submission_id, None)
        await query.edit_message_text("انتشار لغو شد.")
        return

    if action.startswith("pubconfirm:"):
        submission_id = int(action.split(":")[1])
        submission = get_submission(submission_id)
        if not submission:
            await query.edit_message_text("❌ ثبت موردنظر پیدا نشد.")
            return
        selections = context.user_data.setdefault("publication_languages", {})
        languages = list(selections.get(submission_id, ["fa"]))
        if not languages:
            await query.answer("حداقل یک زبان را انتخاب کنید.", show_alert=True)
            return
        if any(language not in CHANNELS for language in languages):
            await query.answer("یکی از زبان‌ها معتبر نیست.", show_alert=True)
            return
        selections.pop(submission_id, None)
        await query.edit_message_text(f"⏳ انتشار ثبت #{submission_id} در حال انجام است...")
        report = []
        successful = 0
        for language in languages:
            channel = CHANNELS[language]
            try:
                ok, detail = await publish_submission(context, submission, language)
                successful += int(ok)
                report.append(f"✅ {LANG_NAMES[language]} ({channel}): {detail}")
            except Exception as exc:
                logger.exception("Publication failed for %s", language)
                record_publication(submission_id, language, channel, "failed", error=str(exc)[:1000])
                report.append(f"❌ {LANG_NAMES[language]} ({channel})\nخطا: {str(exc)[:300]}")
        set_submission_status(submission_id, "approved" if successful else "pending")
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"📊 گزارش انتشار ثبت #{submission_id}\n\n" + "\n\n".join(report) + f"\n\nموفق: {successful}/{len(languages)}",
            )
        except Exception:
            logger.exception("Could not send publication report")
        try:
            if successful:
                await context.bot.send_message(chat_id=submission["user_id"], text="✅ ثبت شما منتشر شد.")
            else:
                await context.bot.send_message(chat_id=submission["user_id"], text="⚠️ انتشار انجام نشد؛ ثبت شما برای بررسی مجدد محفوظ است.")
        except Exception:
            logger.exception("Could not notify submitter after publication")
        return


# ==================== USER MESSAGES ====================

LANGUAGE_CHANGE_BUTTONS = {
    "🌐 تغییر زبان", "🌐 Change Language", "🌐 Dil dəyişdir",
    "🌐 Dil Değiştir", "🌐 تغيير اللغة", "🌐 更改语言", "🌐 Сменить язык",
}
SUPPORT_BUTTONS = {
    "🆘 پشتیبانی", "🆘 Support", "🆘 Dəstək", "🆘 Destek",
    "🆘 الدعم", "🆘 客服支持", "🆘 Поддержка",
}
MY_LISTINGS_BUTTONS = {
    "📋 آگهی‌های من", "📋 My Listings", "📋 Elanlarım",
    "📋 İlanlarım", "📋 إعلاناتي", "📋 我的房源", "📋 Мои объявления",
}
MY_REQUESTS_BUTTONS = {
    "📨 درخواست‌های من", "📨 My Requests", "📨 Sorğularım",
    "📨 Taleplerim", "📨 طلباتي", "📨 我的需求", "📨 Мои запросы",
}


async def show_user_submissions(update, user_id, only_requests=False):
    sql = "SELECT id, kind, status, created_at FROM submissions WHERE user_id=?"
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
        lines.append(f"#{row['id']} — {KINDS.get(row['kind'], {}).get('fa', row['kind'])} — {row['status']}")
    await update.message.reply_text("\n".join(lines))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user = update.effective_user
    if not user:
        return

    # فرایند اختصاصی اجاره اداری شامل متن، عکس و شماره تماس است.
    if context.user_data.get("form", {}).get("mode") == "office_rent":
        if update.message.contact or update.message.photo or update.message.text:
            if await process_office_rent(update, context):
                return

    if not update.message.text:
        return
    text = update.message.text.strip()

    language = parse_language(text)
    if language:
        await choose_language(update, context, language)
        return

    saved_user = get_user(user.id)
    if not saved_user:
        await update.message.reply_text(language_prompt(), reply_markup=language_keyboard())
        return
    user_language = saved_user["language"]

    if text in BACK_BUTTONS:
        context.user_data.pop("form", None)
        context.user_data.pop("rent_menu", None)
        context.user_data.pop("awaiting_support", None)
        await update.message.reply_text("به منوی اصلی بازگشتید.", reply_markup=main_keyboard(user_language))
        return

    if text in LANGUAGE_CHANGE_BUTTONS:
        context.user_data.pop("form", None)
        context.user_data.pop("awaiting_support", None)
        context.user_data.pop("rent_menu", None)
        await update.message.reply_text(language_prompt(), reply_markup=language_keyboard())
        return

    if text in MY_LISTINGS_BUTTONS:
        context.user_data.pop("form", None)
        context.user_data.pop("awaiting_support", None)
        await show_user_submissions(update, user.id)
        return

    if text in MY_REQUESTS_BUTTONS:
        context.user_data.pop("form", None)
        context.user_data.pop("awaiting_support", None)
        await show_user_submissions(update, user.id, only_requests=True)
        return

    if text in SUPPORT_BUTTONS:
        context.user_data.pop("form", None)
        context.user_data["awaiting_support"] = True
        await update.message.reply_text("پیام خود را برای پشتیبانی ارسال کنید:", reply_markup=main_keyboard(user_language))
        return

    if context.user_data.get("awaiting_support"):
        context.user_data["awaiting_support"] = False
        with connect_db() as conn:
            conn.execute("INSERT INTO support_messages (user_id, message) VALUES (?, ?)", (user.id, text))
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"🆘 پیام پشتیبانی\nکاربر: {user.id}\n\n{text}")
        except Exception:
            logger.exception("Support notification failed")
        confirmations = {
            "fa": "✅ پیام شما برای پشتیبانی ارسال شد.",
            "en": "✅ Your support message has been sent.",
            "az": "✅ Dəstək mesajınız göndərildi.",
            "tr": "✅ Destek mesajınız gönderildi.",
            "ar": "✅ تم إرسال رسالتك إلى الدعم.",
            "zh": "✅ 您的支持消息已发送.",
            "ru": "✅ Ваше сообщение в службу поддержки отправлено.",
        }
        await update.message.reply_text(confirmations.get(user_language, confirmations["fa"]), reply_markup=main_keyboard(user_language))
        return

    if context.user_data.get("rent_menu"):
        category = RENT_CATEGORY_MAP.get(text)
        if not category:
            await update.message.reply_text("لطفاً یکی از گزینه‌های زیرمنوی اجاره را انتخاب کنید.", reply_markup=submenu_keyboard(["اداری", "مسکونی", "صنعتی", "تجاری"]))
            return
        context.user_data.pop("rent_menu", None)
        if category == "اداری":
            await begin_office_rent_form(update, context, user_language)
        else:
            # زیرمنو برای هر چهار دسته نمایش داده می‌شود؛ فرم کامل فعلاً برای اداری تعریف شده است.
            await update.message.reply_text(
                f"بخش «{category}» انتخاب شد؛ فرم اختصاصی این دسته هنوز تعریف نشده است.",
                reply_markup=main_keyboard(user_language),
            )
        return

    kind = detect_kind(text)
    if kind:
        await begin_form(update, context, kind, user_language)
        return

    if await process_standard_form(update, context):
        return

    await update.message.reply_text("لطفاً از گزینه‌های منو استفاده کنید.", reply_markup=main_keyboard(user_language))


async def process_standard_form(update, context):
    form = context.user_data.get("form")
    if not form or form.get("mode") == "office_rent":
        return False
    if not update.message or not update.message.text:
        return False
    text = update.message.text.strip()
    language = form["language"]

    if text in LANGUAGE_CHANGE_BUTTONS:
        context.user_data.pop("form", None)
        await update.message.reply_text(language_prompt(), reply_markup=language_keyboard())
        return True
    if text in MY_LISTINGS_BUTTONS or text in MY_REQUESTS_BUTTONS:
        return False
    if text in SUPPORT_BUTTONS:
        context.user_data.pop("form", None)
        context.user_data["awaiting_support"] = True
        await update.message.reply_text("پیام خود را برای پشتیبانی ارسال کنید:", reply_markup=main_keyboard(language))
        return True
    new_kind = detect_kind(text)
    if new_kind:
        await begin_form(update, context, new_kind, language)
        return True

    index = form["step"]
    if index < 0 or index >= len(FIELDS):
        context.user_data.pop("form", None)
        await update.message.reply_text("فرم قبلی دچار اختلال شد. لطفاً دوباره شروع کنید.", reply_markup=main_keyboard(language))
        return True
    field = FIELDS[index]
    form["data"][field] = text
    form["step"] += 1
    if form["step"] < len(FIELDS):
        next_field = FIELDS[form["step"]]
        await update.message.reply_text(f"➡️ {FIELD_LABELS[language][next_field]}:", reply_markup=main_keyboard(language))
        return True

    submission_id = create_submission(update.effective_user.id, language, form["kind"], form["data"])
    context.user_data.pop("form", None)
    confirmations = {
        "fa": f"✅ اطلاعات شما با کد پیگیری {submission_id} ثبت شد و برای بررسی مدیر ارسال می‌شود.",
        "en": f"✅ Your submission #{submission_id} has been received and sent for review.",
        "az": f"✅ Məlumatınız #{submission_id} nömrəsi ilə qəbul edildi və yoxlanış üçün göndərildi.",
        "tr": f"✅ Bilgileriniz #{submission_id} numarasıyla alındı ve inceleme için gönderildi.",
        "ar": f"✅ تم استلام معلوماتك برقم {submission_id} وإرسالها للمراجعة.",
        "zh": f"✅ 您的信息已登记，编号为 #{submission_id}，并已提交管理员审核。",
        "ru": f"✅ Ваша заявка #{submission_id} зарегистрирована и отправлена администратору на проверку.",
    }
    await update.message.reply_text(confirmations[language], reply_markup=main_keyboard(language))
    await send_admin_review(context, submission_id)
    return True


# ==================== ERROR HANDLER ====================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Telegram update processing failed", exc_info=context.error)


# ==================== ADMIN COMMAND ====================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != ADMIN_ID:
        if update.message:
            await update.message.reply_text("⛔ دسترسی ندارید.")
        return
    with connect_db() as conn:
        pending = conn.execute("SELECT COUNT(*) AS n FROM submissions WHERE status='pending'").fetchone()["n"]
        total = conn.execute("SELECT COUNT(*) AS n FROM submissions").fetchone()["n"]
    await update.message.reply_text(f"🛠 پنل مدیر\n\n📥 در انتظار بررسی: {pending}\n📊 کل ثبت‌ها: {total}")


# ==================== RENDER HEALTH SERVER ====================

web_app = Flask(__name__)

@web_app.get("/")
def home():
    return jsonify({"service": "tehran-real-estate-bot", "status": "running"}), 200

@web_app.get("/health")
def health_check():
    return jsonify({"status": "ok"}), 200

def run_web():
    web_app.run(host="0.0.0.0", port=PORT, use_reloader=False, threaded=True)


# ==================== MAIN ====================

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده است.")
    init_db()
    web_thread = Thread(target=run_web, daemon=True)
    web_thread.start()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^(approve|reject):\d+$|^pubtoggle:\d+:(fa|en|az|tr|ar|zh|ru)$|^pubconfirm:\d+$|^pubcancel:\d+$",
        )
    )
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_text))
    application.add_error_handler(error_handler)
    logger.info("Tehran Real Estate bot starting.")
    logger.info("Render web server configured for port %s.", PORT)
    application.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
