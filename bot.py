import os
import json
import sqlite3
import logging
import asyncio
import re
import zlib
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
LANGUAGE_BUTTONS = {
    "fa": "🌐 تغییر زبان", "en": "🌐 Change Language", "az": "🌐 Dil dəyişdir",
    "tr": "🌐 Dil Değiştir", "ar": "🌐 تغيير اللغة", "zh": "🌐 更改语言", "ru": "🌐 Сменить язык",
}
LANGUAGE_BUTTON = LANGUAGE_BUTTONS["fa"]

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
    "fa": [["🏠 خرید ملک", "🔑 اجاره ملک"], ["📝 درخواست خرید", "📨 درخواست اجاره"], ["💼 سرمایه‌گذاری ملکی", "🏗 مشارکت در ساخت"], ["🏢 پیش‌فروش‌ها", "🆘 پشتیبانی"]],
    "en": [["🏠 Buy Property", "🔑 Rent Property"], ["📝 Buy Request", "📨 Rental Request"], ["💼 Property Investment", "🏗 Joint Construction"], ["🏢 Presales", "🆘 Support"]],
    "az": [["🏠 Əmlak al", "🔑 Əmlak kirayələ"], ["📝 Alış sorğusu", "📨 İcarə sorğusu"], ["💼 Əmlaka investisiya", "🏗 Birgə tikinti"], ["🏢 Ön satışlar", "🆘 Dəstək"]],
    "tr": [["🏠 Gayrimenkul satın al", "🔑 Gayrimenkul kirala"], ["📝 Satın alma talebi", "📨 Kiralama talebi"], ["💼 Gayrimenkul yatırımı", "🏗 Kat karşılığı inşaat"], ["🏢 Ön satış", "🆘 Destek"]],
    "ar": [["🏠 شراء عقار", "🔑 استئجار عقار"], ["📝 طلب شراء", "📨 طلب إيجار"], ["💼 الاستثمار العقاري", "🏗 شراكة بناء"], ["🏢 البيع على الخارطة", "🆘 الدعم"]],
    "zh": [["🏠 购买房产", "🔑 租赁房产"], ["📝 求购需求", "📨 求租需求"], ["💼 房地产投资", "🏗 合作建设"], ["🏢 预售房源", "🆘 客服"]],
    "ru": [["🏠 Купить недвижимость", "🔑 Арендовать недвижимость"], ["📝 Запрос на покупку", "📨 Запрос на аренду"], ["💼 Инвестиции в недвижимость", "🏗 Совместное строительство"], ["🏢 Предпродажа", "🆘 Поддержка"]],
}

# Полный каталог категорий. Кнопки переводятся на язык пользователя при показе.
SUBMENUS = {
    "buy": ["🏢 آپارتمان مسکونی", "🏡 ویلا و خانه مستقل", "🌳 زمین و باغ", "🏬 مغازه و ملک تجاری", "🏢 دفتر کار و ملک اداری", "🏭 ملک صنعتی، کارخانه و کارگاه", "🏗 سوله و انبار", "🏚 ملک کلنگی", "🏗 پیش‌خرید و پروژه در حال ساخت", "💎 املاک لوکس و گران‌قیمت", "📈 ملک مناسب سرمایه‌گذاری", "🏙 مستغلات و مجتمع تجاری", "📦 مشاهده همه آگهی‌های خرید"],
    "rent": ["🏢 آپارتمان مسکونی", "🏡 ویلا و خانه مستقل", "🏬 مغازه و ملک تجاری", "🏢 دفتر کار و ملک اداری", "🏭 ملک صنعتی، کارخانه و کارگاه", "🏗 سوله و انبار", "💎 املاک لوکس"],
    "buy_req": ["🏢 آپارتمان مسکونی", "🏡 ویلا و خانه مستقل", "🌳 زمین و باغ", "🏬 مغازه و ملک تجاری", "🏢 دفتر کار و ملک اداری", "🏭 ملک صنعتی، کارخانه و کارگاه", "🏗 سوله و انبار", "🏚 ملک کلنگی", "🏗 پیش‌خرید و پروژه در حال ساخت", "💎 ملک لوکس و گران‌قیمت"],
    "rent_req": ["🏢 آپارتمان مسکونی", "🏡 ویلا و خانه مستقل", "🏬 مغازه و ملک تجاری", "🏢 دفتر کار و ملک اداری", "🏭 ملک صنعتی، کارخانه و کارگاه", "🏗 سوله و انبار", "💎 ملک لوکس"],
    "investment": ["🏠 خرید ملک برای اجاره‌دادن", "📈 خرید برای افزایش قیمت و فروش", "🏬 سرمایه‌گذاری در املاک تجاری", "💎 املاک لوکس و خاص", "🏗 پروژه‌های ساختمانی و در حال ساخت", "🏙 پروژه‌ها و سرمایه‌گذاری‌های بزرگ", "🤝 جذب شریک یا سرمایه‌گذار برای پروژه", "🌳 سرمایه‌گذاری در زمین و باغ"],
    "construction": ["🧑‍💼 مالک زمین/ملک دنبال سازنده", "🏗 سازنده دنبال زمین/ملک", "💰 سرمایه‌گذار دنبال پروژه مشارکتی", "🤝 دنبال شریک برای پروژه ساختمانی", "📋 معرفی پروژه‌های آماده مشارکت", "🧭 مشاوره و ارزیابی شرایط مشارکت", "🏙 پروژه‌های بزرگ و چندواحدی"],
    "presale": ["🏢 پیش‌فروش آپارتمان", "🏡 پیش‌فروش ویلا", "🏬 پیش‌فروش واحد تجاری", "🏢 پیش‌فروش واحد اداری", "🏙 پیش‌فروش ساختمان تجاری", "🏢 پیش‌فروش ساختمان اداری"],
}

MAIN_ACTIONS = {
    "🏠 خرید ملک":"buy", "🔑 اجاره ملک":"rent", "📝 درخواست خرید":"buy_req", "📨 درخواست اجاره":"rent_req",
    "💼 سرمایه‌گذاری ملکی":"investment", "🏗 مشارکت در ساخت":"construction", "🏢 پیش‌فروش‌ها":"presale", "🏢 Presales":"presale", "🏢 Предпродажа":"presale", "🏢 预售房源":"presale", "🏢 البيع على الخارطة":"presale", "🏢 Ön satış":"presale", "🏢 Ön satışlar":"presale",
    "🆘 پشتیبانی":"support",
}
KIND_FOR_MENU = {"buy":"sell_ad", "rent":"rent_ad", "buy_req":"buy_req", "rent_req":"rent_req", "investment":"builder", "construction":"builder", "presale":"builder"}

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
    "rent_apartment_ad": {"fa": "آگهی اجاره آپارتمان", "en": "Apartment for rent", "az": "Kirayə mənzil elanı", "tr": "Kiralık daire ilanı", "ar": "إعلان شقة للإيجار", "zh": "公寓出租信息", "ru": "Объявление об аренде квартиры"},
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


_TRANSLATION_CACHE = {}

async def translate(text, target, source=None):
    if not text or target == source:
        return text
    cache_key = (str(text), target, source or "")
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key]
    result = await asyncio.to_thread(translate_sync, text, target, source)
    _TRANSLATION_CACHE[cache_key] = result
    return result


async def localized(text, language):
    """Translate UI copy to the selected language, with safe fallback if translation is unavailable."""
    if language == "fa":
        return text
    try:
        return await translate(text, language, "fa")
    except Exception:
        logger.exception("UI translation failed for language %s", language)
        return text


async def translate_submission_data(data, source, target):
    # Keep original values in the database; translate only the rendered copy.
    result = dict(data)
    if source == target:
        return result
    protected = {"contact", "contact_user_id", "telegram_user_id", "telegram_username", "exact_address", "images", "videos", "map_location", "source_language", "menu_mode"}
    for key, raw in data.items():
        if key in protected or raw is None or not isinstance(raw, str):
            continue
        value = raw.strip()
        if value:
            try:
                result[key] = await translate(value, target, source)
            except Exception:
                logger.exception("Translation failed for field %s", key)
                result[key] = raw
    return result


# ==================== KEYBOARDS ====================

EMOJI_PREFIXES = ("🏢 ", "🏠 ", "🏭 ", "🏬 ", "📄 ", "📍 ", "🏛 ", "🔀 ", "✅ ", "❌ ", "📷 ", "📱 ", "⬅️ ", "🆘 ", "🌐 ", "🔑 ", "📝 ", "📨 ", "💼 ", "🏗 ", "⭐ ", "🌳 ", "🏚 ", "🏡 ", "🏨 ", "💎 ", "📈 ", "📦 ", "🤝 ", "💰 ", "🧑‍💼 ", "🏙 ", "📋 ", "🔔 ", "⚖️ ", "🗑 ", "💲 ", "🧭 ")


# ==================== GLOBAL BUTTON NUMBERING ====================
# Numbers are assigned once per visible label and persisted so deleted numbers
# are never recycled. Every reply-keyboard button is numbered automatically.
BUTTON_NUMBER_FILE = os.getenv("BUTTON_NUMBER_FILE", "realestate_button_numbers.json")
_BUTTON_NUMBER_LOCK = __import__("threading").RLock()
_BUTTON_NUMBERS = {}
_BUTTON_NEXT = 1


def _strip_button_number(value):
    return re.sub(r"^\s*\d{3,6}\s*[|.)-]\s*", "", str(value or "")).strip()


def _button_key(value):
    """Return a language-independent identity for the logical button.

    For UI strings translated by localized(), use the original Persian source
    text as the identity. Main-menu labels are maintained as parallel rows in
    MENU, so their translations also resolve to the same identity even though
    they are written explicitly rather than translated at runtime.
    """
    value = _strip_button_number(value)
    visible = re.sub(r"\s+", " ", value).strip()

    # Resolve explicit translations of the main menu by semantic action, not
    # by row/column position (layouts may differ between languages).
    main_menu_aliases = {
        "🏠 خرید ملک": "menu:buy", "🏠 Buy Property": "menu:buy", "🏠 Əmlak al": "menu:buy", "🏠 Gayrimenkul satın al": "menu:buy", "🏠 شراء عقار": "menu:buy", "🏠 购买房产": "menu:buy", "🏠 Купить недвижимость": "menu:buy",
        "🔑 اجاره ملک": "menu:rent", "🔑 Rent Property": "menu:rent", "🔑 Əmlak kirayələ": "menu:rent", "🔑 Gayrimenkul kirala": "menu:rent", "🔑 استئجار عقار": "menu:rent", "🔑 租赁房产": "menu:rent", "🔑 Арендовать недвижимость": "menu:rent",
        "📝 درخواست خرید": "menu:buy_request", "📝 Buy Request": "menu:buy_request", "📝 Alış sorğusu": "menu:buy_request", "📝 Satın alma talebi": "menu:buy_request", "📝 طلب شراء": "menu:buy_request", "📝 求购需求": "menu:buy_request", "📝 Запрос на покупку": "menu:buy_request",
        "📨 درخواست اجاره": "menu:rent_request", "📨 Rental Request": "menu:rent_request", "📨 İcarə sorğusu": "menu:rent_request", "📨 Kiralama talebi": "menu:rent_request", "📨 طلب إيجار": "menu:rent_request", "📨 求租需求": "menu:rent_request", "📨 Запрос на аренду": "menu:rent_request",
        "💼 سرمایه‌گذاری ملکی": "menu:investment", "💼 Property Investment": "menu:investment", "💼 Əmlaka investisiya": "menu:investment", "💼 Gayrimenkul yatırımı": "menu:investment", "💼 الاستثمار العقاري": "menu:investment", "💼 房地产投资": "menu:investment", "💼 Инвестиции в недвижимость": "menu:investment",
        "🏗 مشارکت در ساخت": "menu:construction", "🏗 Joint Construction": "menu:construction", "🏗 Birgə tikinti": "menu:construction", "🏗 Kat karşılığı inşaat": "menu:construction", "🏗 شراكة بناء": "menu:construction", "🏗 合作建设": "menu:construction", "🏗 Совместное строительство": "menu:construction",
        "🏢 پیش‌فروش‌ها": "menu:presale", "🏢 Presales": "menu:presale", "🏢 Предпродажа": "menu:presale", "🏢 预售房源": "menu:presale", "🏢 البيع على الخارطة": "menu:presale", "🏢 Ön satış": "menu:presale", "🏢 Ön satışlar": "menu:presale",
        "🆘 پشتیبانی": "menu:support", "🆘 Support": "menu:support", "🆘 Dəstək": "menu:support", "🆘 Destek": "menu:support", "🆘 الدعم": "menu:support", "🆘 客服": "menu:support", "🆘 Поддержка": "menu:support",
    }
    if visible.casefold() in {k.casefold() for k in main_menu_aliases}:
        for alias, canonical in main_menu_aliases.items():
            if alias.casefold() == visible.casefold():
                return canonical

    # Resolve all explicitly translated language-change buttons to one key.
    try:
        if visible.casefold() in {str(x).casefold() for x in LANGUAGE_BUTTONS.values()}:
            return "system:change_language"
    except NameError:
        pass

    # Translation cache maps (source, target language, source language) to the
    # translated label. Reuse the source string so all language variants share
    # one persistent number.
    try:
        for (source_text, target_lang, source_lang), translated_text in _TRANSLATION_CACHE.items():
            if str(translated_text).strip().casefold() == visible.casefold():
                visible = str(source_text).strip()
                break
    except NameError:
        pass

    # Emoji and spacing are presentation only; strip them from the identity.
    normalized = normalize_button_text(visible) if "normalize_button_text" in globals() else visible
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def _load_button_numbers():
    global _BUTTON_NUMBERS, _BUTTON_NEXT
    try:
        with open(BUTTON_NUMBER_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        _BUTTON_NUMBERS = {str(k): int(v) for k, v in data.get("numbers", {}).items()}
        _BUTTON_NEXT = max(int(data.get("next", 1)), max(_BUTTON_NUMBERS.values(), default=0) + 1)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        _BUTTON_NUMBERS, _BUTTON_NEXT = {}, 1


def _save_button_numbers():
    folder = os.path.dirname(os.path.abspath(BUTTON_NUMBER_FILE))
    os.makedirs(folder, exist_ok=True)
    tmp = BUTTON_NUMBER_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"next": _BUTTON_NEXT, "numbers": _BUTTON_NUMBERS}, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, BUTTON_NUMBER_FILE)


_load_button_numbers()


def numbered_button(value):
    global _BUTTON_NEXT
    raw = str(value or "")
    if not raw.strip() or re.match(r"^\s*\d{3,6}\s*[|.)-]\s*", raw):
        return raw
    key = _button_key(raw)
    with _BUTTON_NUMBER_LOCK:
        if key not in _BUTTON_NUMBERS:
            _BUTTON_NUMBERS[key] = _BUTTON_NEXT
            _BUTTON_NEXT += 1
            _save_button_numbers()
        number = _BUTTON_NUMBERS[key]
    return f"{number:03d} | {raw}"


def number_keyboard_rows(rows):
    numbered = []
    for row in rows:
        new_row = []
        for item in row:
            if isinstance(item, KeyboardButton):
                # Preserve special button behavior such as Telegram contact sharing.
                item.text = numbered_button(item.text)
                new_row.append(item)
            else:
                new_row.append(numbered_button(item))
        numbered.append(new_row)
    return numbered


def normalize_button_text(value):
    """Remove leading menu emoji so labels remain compatible with existing flows."""
    value = _strip_button_number(value or "")
    changed = True
    while changed:
        changed = False
        for prefix in EMOJI_PREFIXES:
            if value.startswith(prefix):
                value = value[len(prefix):].strip()
                changed = True
    return value


def with_language_button(rows, language="fa"):
    """Keep a language-change control on every user keyboard, in the selected language."""
    result = [list(row) for row in rows]
    aliases = {normalize_button_text(x) for x in LANGUAGE_BUTTONS.values()}
    for row in result:
        row[:] = [item for item in row if normalize_button_text(str(item).replace("🌐 ", "")) not in aliases]
    result.append([LANGUAGE_BUTTONS.get(language, LANGUAGE_BUTTONS["fa"])])
    return result


def language_keyboard():
    # Language picker itself is intentionally exempt from the persistent language button.
    return ReplyKeyboardMarkup(number_keyboard_rows(LANGUAGE_KEYBOARD), resize_keyboard=True, one_time_keyboard=True, is_persistent=True)


def main_keyboard(language):
    rows = with_language_button(MENU.get(language, MENU["fa"]), language)
    return ReplyKeyboardMarkup(number_keyboard_rows(rows), resize_keyboard=True, is_persistent=True)


BACK_LABELS = {
    "fa": "⬅️ بازگشت به منوی اصلی", "en": "⬅️ Back to Main Menu",
    "az": "⬅️ Əsas menyuya qayıt", "tr": "⬅️ Ana menüye dön",
    "ar": "⬅️ العودة إلى القائمة الرئيسية", "zh": "⬅️ 返回主菜单", "ru": "⬅️ Вернуться в главное меню",
}

def submenu_keyboard(options, back_label=None, language="fa"):
    rows = [[option] for option in options]
    rows.append([back_label or BACK_LABELS.get(language, BACK_LABELS["fa"])])
    rows = with_language_button(rows, language)
    return ReplyKeyboardMarkup(number_keyboard_rows(rows), resize_keyboard=True, is_persistent=True)


def form_keyboard(rows, language="fa"):
    return ReplyKeyboardMarkup(number_keyboard_rows(with_language_button(rows, language)), resize_keyboard=True, is_persistent=True)


def parse_language(text):
    """Recognize language keyboard labels despite Telegram/Unicode emoji variants."""
    import unicodedata

    if not isinstance(text, str):
        return None

    # Remove invisible formatting characters and emoji variation selectors,
    # then normalize whitespace/case before comparing the visible label.
    cleaned = []
    for char in unicodedata.normalize("NFKC", text):
        category = unicodedata.category(char)
        codepoint = ord(char)
        if category == "Cf" or codepoint in (0xFE0E, 0xFE0F, 0x200B, 0x200C, 0x200D, 0xFEFF):
            continue
        # Regional-indicator characters are the components of flag emojis.
        if 0x1F1E6 <= codepoint <= 0x1F1FF:
            continue
        cleaned.append(char)

    normalized = " ".join("".join(cleaned).split()).strip().casefold()
    aliases = {
        "فارسی": "fa", "english": "en", "azərbaycan dili": "az",
        "türkçe": "tr", "العربية": "ar", "中文": "zh", "русский": "ru",
    }
    if normalized in aliases:
        return aliases[normalized]

    # Compare normalized versions of the configured labels too, so the
    # keyboard and parser cannot drift apart when emoji formatting changes.
    for code, label in LANG_NAMES.items():
        label_cleaned = []
        for char in unicodedata.normalize("NFKC", label):
            category = unicodedata.category(char)
            codepoint = ord(char)
            if category == "Cf" or codepoint in (0xFE0E, 0xFE0F, 0x200B, 0x200C, 0x200D, 0xFEFF):
                continue
            if 0x1F1E6 <= codepoint <= 0x1F1FF:
                continue
            label_cleaned.append(char)
        label_normalized = " ".join("".join(label_cleaned).split()).strip().casefold()
        if normalized == label_normalized:
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
    context.user_data.pop("rent_property_menu", None)
    await update.message.reply_text(language_prompt(), reply_markup=language_keyboard())


async def choose_language(update, context, language):
    user = update.effective_user
    if not user or not update.message:
        return
    # Preserve the current workflow when the user changes language mid-process.
    active_form = context.user_data.get("form")
    if active_form:
        active_form["language"] = language
    save_user(user, language)
    if active_form and active_form.get("mode") in {"office_rent", "apartment_rent"}:
        await update.message.reply_text(WELCOME[language], reply_markup=main_keyboard(language))
        if active_form.get("mode") == "apartment_rent":
            if active_form.get("awaiting_images"):
                await update.message.reply_text(await localized("حداقل ۴ عکس ارسال کنید؛ سپس «📷 پایان تصاویر» را بفرستید.", language), reply_markup=form_keyboard([[await localized("📷 پایان تصاویر", language)], [await localized("❌ لغو ثبت", language)]], language))
            elif active_form.get("awaiting_agent_name"):
                await update.message.reply_text(await localized("نام و نام خانوادگی مشاور را وارد کنید (فقط برای مدیر اصلی):", language))
            elif active_form.get("awaiting_agency_name"):
                await update.message.reply_text(await localized("نام دفتر املاک را وارد کنید (فقط برای مدیر اصلی):", language))
            elif active_form.get("dynamic_parking_count"):
                await update.message.reply_text(await localized("تعداد جای پارک را فقط با عدد وارد کنید:", language))
            else:
                await ask_apartment_step(update.message, context)
        else:
            await ask_office_step(update.message, context)
        return
    if active_form and active_form.get("mode") == "complete":
        await update.message.reply_text(WELCOME[language], reply_markup=main_keyboard(language))
        await ask_complete_form_step(update.message, context)
        return
    if active_form:
        await update.message.reply_text(WELCOME[language], reply_markup=main_keyboard(language))
        step = active_form.get("step", 0)
        if 0 <= step < len(FIELDS):
            await update.message.reply_text(f"📝 {FIELD_LABELS[language][FIELDS[step]]}:", reply_markup=main_keyboard(language))
        return
    if context.user_data.get("rent_menu"):
        await update.message.reply_text(WELCOME[language] + "\n\n" + RENT_CATEGORY_PROMPTS.get(language, RENT_CATEGORY_PROMPTS["fa"]), reply_markup=submenu_keyboard(rent_category_options(language), language=language))
        return
    if context.user_data.get("rent_property_menu"):
        labels = {"fa": ["🏢 آپارتمان", "🏡 ویلا", "🏠 خانه مستقل"], "en": ["🏢 Apartment", "🏡 Villa", "🏠 Detached house"], "az": ["🏢 Mənzil", "🏡 Villa", "🏠 Müstəqil ev"], "tr": ["🏢 Daire", "🏡 Villa", "🏠 Müstakil ev"], "ar": ["🏢 شقة", "🏡 فيلا", "🏠 منزل مستقل"], "zh": ["🏢 公寓", "🏡 别墅", "🏠 独立住宅"], "ru": ["🏢 Квартира", "🏡 Вилла", "🏠 Отдельный дом"]}.get(language, ["🏢 آپارتمان", "🏡 ویلا", "🏠 خانه مستقل"])
        await update.message.reply_text(await localized("نوع ملک مسکونی را انتخاب کنید:", language), reply_markup=submenu_keyboard(labels, language=language))
        return
    if context.user_data.get("awaiting_support"):
        await update.message.reply_text(WELCOME[language] + "\n\n" + await localized("پیام خود را برای پشتیبانی ارسال کنید:", language), reply_markup=main_keyboard(language))
        return
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


RENT_CATEGORY_LABELS = {
    "fa": {"اداری": "🏢 اداری", "مسکونی": "🏠 مسکونی", "صنعتی": "🏭 صنعتی", "تجاری": "🏬 تجاری"},
    "en": {"اداری": "🏢 Office", "مسکونی": "🏠 Residential", "صنعتی": "🏭 Industrial", "تجاری": "🏬 Commercial"},
    "az": {"اداری": "🏢 Ofis", "مسکونی": "🏠 Yaşayış", "صنعتی": "🏭 Sənaye", "تجاری": "🏬 Kommersiya"},
    "tr": {"اداری": "🏢 Ofis", "مسکونی": "🏠 Konut", "صنعتی": "🏭 Sanayi", "تجاری": "🏬 Ticari"},
    "ar": {"اداری": "🏢 مكتبي", "مسکونی": "🏠 سكني", "صنعتی": "🏭 صناعي", "تجاری": "🏬 تجاري"},
    "zh": {"اداری": "🏢 办公", "مسکونی": "🏠 住宅", "صنعتی": "🏭 工业", "تجاری": "🏬 商业"},
    "ru": {"اداری": "🏢 Офисная", "مسکونی": "🏠 Жилая", "صنعتی": "🏭 Промышленная", "تجاری": "🏬 Коммерческая"},
}
RENT_CATEGORY_PROMPTS = {
    "fa": "نوع آگهی اجاره را انتخاب کنید:", "en": "Choose the rental property category:",
    "az": "İcarə elanının kateqoriyasını seçin:", "tr": "Kiralık gayrimenkul kategorisini seçin:",
    "ar": "اختر فئة العقار للإيجار:", "zh": "请选择出租房产类别：", "ru": "Выберите категорию аренды недвижимости:",
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

def rent_category_options(language):
    labels = RENT_CATEGORY_LABELS.get(language, RENT_CATEGORY_LABELS["fa"])
    return [labels[key] for key in ("اداری", "مسکونی", "صنعتی", "تجاری")]
BACK_BUTTONS = {"⬅️ بازگشت به منوی اصلی", "⬅️ Back to Main Menu", "⬅️ Əsas menyuya qayıt", "⬅️ Ana menüyə qayıt", "⬅️ Ana menüye dön", "⬅️ العودة إلى القائمة الرئيسية", "⬅️ 返回主菜单", "⬅️ Вернуться в главное меню"}
CHOICE_BACK = "⬅️ بازگشت"
OFFICE_CHOICE_BUTTONS = {"سند اداری", "موقعیت اداری", "آپارتمان", "مستغلات"}
BOOL_BUTTONS = {"دارد", "ندارد"}
CONTACT_BUTTONS = {"📱 اشتراک‌گذاری شماره تلگرام", "📱 Share Telegram phone number"}
CANCEL_FORM_BUTTONS = {"❌ لغو ثبت"}

# انتخاب‌های عددی برای جلوگیری از ورود دستی اعداد در فرم‌ها.
# گزینه‌ها در همه زبان‌ها از یک مقدار پایه استفاده می‌کنند تا شماره دکمه‌ها یکسان بماند.
def count_options(max_value=6):
    return [str(i) for i in range(max_value + 1)] + ["+10"]

def room_options():
    return ["1", "2", "3", "4", "+5"]

def master_room_options(selected_rooms):
    """Master-bedroom choices cannot exceed the selected bedroom count."""
    value = normalize_button_text(str(selected_rooms or ""))
    if value == "+5":
        return ["1", "2", "3", "4", "+5"]
    try:
        count = int(value)
    except (TypeError, ValueError):
        return ["1", "2", "3", "4", "+5"]
    return [str(i) for i in range(1, max(1, min(count, 4)) + 1)]

def floor_options():
    return ["0", "2", "3", "4", "5", "6", "+7"]

def numeric_choice_rows(options, language):
    # Compact rows make long numeric menus easier to scan on mobile.
    return [[options[i:i+5] for i in range(0, len(options), 5)]]

APARTMENT_STEPS = [
    ("listing_role", "ثبت‌کننده ملک هستید یا مشاور املاک / واسطه؟", ["👤 مالک", "🏢 مشاور املاک / واسطه"]),
    ("area", "متراژ آپارتمان را فقط با عدد وارد کنید:"),
    ("rooms", "تعداد اتاق خواب را انتخاب کنید:", room_options()),
    ("master_rooms", "تعداد اتاق مستر را انتخاب کنید:", count_options(6)),
    ("lobby", "ساختمان لابی دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("caretaker", "ساختمان سرایدار مقیم دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("elevator", "ساختمان آسانسور دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("parking", "تعداد پارکینگ را انتخاب کنید:", count_options(6)),
    ("shared_pool", "ساختمان امکانات آبی مشترک دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("roof_garden", "ساختمان روف‌گاردن دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("floor", "طبقه واحد را انتخاب کنید (اعداد منفی زیرزمین و ۰ همکف است):", floor_options()),
    ("building_age", "سن بنا را انتخاب کنید:", ["نوساز تا ۵ سال", "۵ تا ۱۵ سال", "۱۵ تا ۲۰ سال", "بیشتر از ۲۰ سال"]),
    ("furnished", "وضعیت مبله بودن آپارتمان را انتخاب کنید:", ["مبله", "غیرمبله"]),
    ("pets", "وضعیت نگهداری حیوان خانگی را انتخاب کنید:", ["مجاز است", "مجاز نیست"]),
    ("total_floors", "تعداد کل طبقات ساختمان را انتخاب کنید:", ["1", "2", "3", "4", "5", "6", "+7"]),
    ("units_per_floor", "تعداد واحد در هر طبقه را انتخاب کنید:", count_options(10)),
    ("storage", "تعداد انباری را انتخاب کنید:", count_options(6)),
    ("city", "نام شهر را وارد کنید:"),
    ("municipal_district", "شماره منطقه شهرداری را فقط با عدد وارد کنید:"),
    ("street", "نام خیابان اصلی را وارد کنید:"),
    ("alley", "نام کوچه یا خیابان فرعی را وارد کنید (این اطلاعات عمومی نمی‌شود):"),
    ("building_number", "شماره پلاک ساختمان را وارد کنید (این اطلاعات عمومی نمی‌شود):"),
    ("unit_number", "شماره واحد را وارد کنید (این اطلاعات عمومی نمی‌شود):"),
    ("deposit", "مبلغ رهن را به تومان و فقط با عدد وارد کنید:"),
    ("rent", "مبلغ اجاره ماهانه را به تومان و فقط با عدد وارد کنید:"),
    ("details", "توضیحات تکمیلی آگهی را وارد کنید:"),
    ("images_choice", "آیا مایل به ارسال عکس‌های ملک هستید؟", ["بله", "خیر"]),
    ("contact", "برای تأیید شماره تلفن، دکمه اشتراک‌گذاری شماره تماس خودتان را بزنید."),
]

APARTMENT_NUMERIC_FIELDS = {"area", "rooms", "master_rooms", "total_floors", "units_per_floor", "storage", "parking", "municipal_district", "building_number", "unit_number", "deposit", "rent"}
APARTMENT_BOOL_FIELDS = {"terrace", "lobby", "caretaker", "elevator", "shared_pool", "roof_garden"}

async def begin_apartment_rent_form(update, context, language):
    context.user_data["form"] = {"kind": "rent_apartment_ad", "language": language, "step": 0, "data": {}, "mode": "apartment_rent", "images": []}
    await ask_apartment_step(update.message, context)

async def ask_apartment_step(message, context):
    form = context.user_data.get("form")
    if not form or form.get("mode") != "apartment_rent":
        return
    key, prompt, *options = APARTMENT_STEPS[form["step"]]
    if key == "master_rooms":
        options = [master_room_options(form.get("data", {}).get("rooms"))]
    language = form["language"]
    if key == "contact":
        rows = [[KeyboardButton(await localized("📱 اشتراک‌گذاری شماره تلگرام", language), request_contact=True)], [await localized("❌ لغو ثبت", language)]]
    elif key == "images_choice":
        rows = [[await localized("بله", language), await localized("خیر", language)], [await localized("❌ لغو ثبت", language)]]
    elif options:
        rows = []
        for option_row in (options[0][i:i+5] for i in range(0, len(options[0]), 5)):
            rows.append([await localized(opt, language) for opt in option_row])
    else:
        rows = []
    rows.append([await localized(PREV_STEP_LABELS.get(language, PREV_STEP_LABELS["fa"]), language)])
    rows.append([await localized("❌ لغو ثبت", language)])
    await message.reply_text(await localized(prompt, language), reply_markup=form_keyboard(rows, language))

async def apartment_next(message, context):
    form = context.user_data.get("form")
    if form and form["step"] < len(APARTMENT_STEPS):
        await ask_apartment_step(message, context)

async def process_apartment_rent(update, context):
    form = context.user_data.get("form")
    if not form or form.get("mode") != "apartment_rent":
        return False
    message = update.message
    if not message:
        return False
    language = form["language"]
    text = _strip_button_number((message.text or "").strip())
    cancel = normalize_button_text(await localized("❌ لغو ثبت", language))
    if normalize_button_text(text) in {normalize_button_text(x) for x in CANCEL_FORM_BUTTONS} | {cancel}:
        context.user_data.pop("form", None)
        await message.reply_text(await localized("ثبت آگهی لغو شد.", language), reply_markup=main_keyboard(language))
        return True
    previous_labels = {normalize_button_text(x) for x in PREV_STEP_LABELS.values()}
    previous_labels.add(normalize_button_text(await localized(PREV_STEP_LABELS.get(language, PREV_STEP_LABELS["fa"]), language)))
    if normalize_button_text(text) in previous_labels:
        if form["step"] > 0:
            form["step"] -= 1
            form["awaiting_images"] = False
            await ask_apartment_step(message, context)
        else:
            await message.reply_text(await localized("در اولین مرحله هستید.", language), reply_markup=main_keyboard(language))
        return True

    # Branches that temporarily collect information without advancing the main step.
    if form.get("awaiting_agent_name"):
        if not text:
            await message.reply_text(await localized("نام و نام خانوادگی مشاور را وارد کنید.", language)); return True
        form["data"]["agent_name"] = text
        form["awaiting_agent_name"] = False
        form["awaiting_agency_name"] = True
        await message.reply_text(await localized("نام دفتر املاک را وارد کنید (فقط برای مدیر اصلی):", language), reply_markup=form_keyboard([[await localized("❌ لغو ثبت", language)]], language))
        return True
    if form.get("awaiting_agency_name"):
        if not text:
            await message.reply_text(await localized("نام دفتر املاک را وارد کنید.", language)); return True
        form["data"]["agency_name"] = text
        form["awaiting_agency_name"] = False
        form["step"] += 1
        await ask_apartment_step(message, context)
        return True
    if form.get("dynamic_parking_count"):
        normalized = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        if not normalized.isdigit():
            await message.reply_text(await localized("تعداد جای پارک باید فقط عدد باشد.", language)); return True
        form["data"]["parking_spaces"] = normalized
        form["dynamic_parking_count"] = False
        await ask_apartment_step(message, context)
        return True
    if form.get("awaiting_images"):
        if message.photo:
            form["images"].append(message.photo[-1].file_id)
            form["data"]["images"] = list(form["images"])
            await message.reply_text(await localized(f"تصویر دریافت شد. تعداد فعلی: {len(form['images'])}؛ حداقل ۴ تصویر لازم است.", language), reply_markup=form_keyboard([[await localized("📷 پایان تصاویر", language)], [await localized("❌ لغو ثبت", language)]], language))
            return True
        if normalize_button_text(text) in {"پایان تصاویر", normalize_button_text(await localized("📷 پایان تصاویر", language))}:
            if len(form["images"]) < 4:
                await message.reply_text(await localized(f"حداقل ۴ تصویر لازم است؛ تاکنون {len(form['images'])} تصویر ارسال کرده‌اید.", language)); return True
            form["awaiting_images"] = False
            form["step"] = next(i for i, step in enumerate(APARTMENT_STEPS) if step[0] == "contact")
            await ask_apartment_step(message, context)
            return True
        await message.reply_text(await localized("عکس ارسال کنید یا پس از حداقل ۴ عکس، پایان تصاویر را بفرستید.", language))
        return True

    key = APARTMENT_STEPS[form["step"]][0]
    if message.contact:
        if key != "contact":
            await message.reply_text(await localized("لطفاً در مرحله درخواست‌شده پاسخ دهید.", language)); return True
        if message.contact.user_id and message.contact.user_id != update.effective_user.id:
            await message.reply_text(await localized("فقط شماره تماس متعلق به حساب تلگرام خودتان قابل قبول است.", language)); return True
        phone = (message.contact.phone_number or "").strip()
        with connect_db() as conn:
            rows = conn.execute("SELECT user_id, data FROM submissions WHERE kind='rent_apartment_ad'").fetchall()
        for row in rows:
            try: saved = json.loads(row["data"])
            except Exception: continue
            if saved.get("contact") == phone and row["user_id"] != update.effective_user.id:
                await message.reply_text(await localized("این شماره قبلاً برای حساب دیگری استفاده شده است؛ ثبت آگهی با این شماره ممکن نیست.", language)); return True
        form["data"]["contact"] = phone
        form["data"]["telegram_user_id"] = update.effective_user.id
        form["data"]["telegram_username"] = update.effective_user.username or ""
        await finish_apartment_rent(update, context)
        return True

    if key == "contact":
        await message.reply_text(await localized("برای ادامه، شماره تماس خودتان را با دکمه اشتراک‌گذاری شماره تماس ارسال کنید.", language)); return True
    if not text:
        await message.reply_text(await localized("لطفاً پاسخ این مرحله را ارسال کنید.", language)); return True

    if key == "images_choice":
        norm = normalize_button_text(text).casefold()
        yes_values = {normalize_button_text(await localized("بله", language)).casefold(), "بله", "yes", "да", "نعم", "evet", "是", "bəli"}
        no_values = {normalize_button_text(await localized("خیر", language)).casefold(), "خیر", "no", "нет", "لا", "hayır", "不", "xeyr"}
        if norm in yes_values:
            form["data"]["images_submitted"] = "yes"
            form["data"]["images"] = []
            form["awaiting_images"] = True
            await message.reply_text(await localized("حداقل ۴ عکس ارسال کنید؛ سپس «📷 پایان تصاویر» را بفرستید.", language), reply_markup=form_keyboard([[await localized("📷 پایان تصاویر", language)], [await localized("❌ لغو ثبت", language)]], language))
            return True
        if norm in no_values:
            form["data"]["images_submitted"] = "no"
            form["data"]["images"] = []
            form["step"] += 1
            await ask_apartment_step(message, context)
            return True
        await message.reply_text(await localized("لطفاً بله یا خیر را انتخاب کنید.", language)); return True

    # All predefined choice fields (including numeric counts and floors) accept
    # button selections only; typed values are rejected.
    step_options = APARTMENT_STEPS[form["step"]][2:]
    if key == "master_rooms":
        step_options = [master_room_options(form.get("data", {}).get("rooms"))]
    if step_options and key in {"rooms", "master_rooms", "parking", "floor", "total_floors", "units_per_floor", "storage"}:
        allowed = step_options[0]
        matched = None
        for opt in allowed:
            if normalize_button_text(text) in {normalize_button_text(opt), normalize_button_text(await localized(opt, language))}:
                matched = opt
                break
        if matched is None:
            await message.reply_text(await localized("لطفاً فقط یکی از دکمه‌های نمایش‌داده‌شده را انتخاب کنید.", language))
            return True
        value = normalize_button_text(matched)
        if key == "parking":
            form["data"]["parking_spaces"] = value
            form["data"]["parking"] = "دارد" if value not in {"0", "ندارد"} else "ندارد"
        else:
            form["data"][key] = value
        form["step"] += 1
        if form["step"] >= len(APARTMENT_STEPS):
            await finish_apartment_rent(update, context)
        else:
            await ask_apartment_step(message, context)
        return True

    if key == "listing_role":
        allowed = APARTMENT_STEPS[form["step"]][2]
        matched = None
        for opt in allowed:
            if normalize_button_text(text) in {normalize_button_text(opt), normalize_button_text(await localized(opt, language))}:
                matched = opt; break
        if not matched:
            await message.reply_text(await localized("لطفاً مالک یا مشاور املاک / واسطه را انتخاب کنید.", language)); return True
        form["data"][key] = "owner" if "مالک" in matched else "broker"
        if form["data"][key] == "broker":
            form["awaiting_agent_name"] = True
            await message.reply_text(await localized("نام و نام خانوادگی مشاور را وارد کنید (فقط برای مدیر اصلی):", language), reply_markup=form_keyboard([[await localized("❌ لغو ثبت", language)]], language))
            return True
        form["data"]["agent_name"] = ""
        form["data"]["agency_name"] = ""
        form["step"] += 1
        await ask_apartment_step(message, context)
        return True

    if key in APARTMENT_BOOL_FIELDS or key in {"furnished", "pets"}:
        allowed = APARTMENT_STEPS[form["step"]][2]
        matched = None
        for opt in allowed:
            if normalize_button_text(text) in {normalize_button_text(opt), normalize_button_text(await localized(opt, language))}:
                matched = opt; break
        if not matched:
            await message.reply_text(await localized("لطفاً یکی از گزینه‌های نمایش‌داده‌شده را انتخاب کنید.", language)); return True
        form["data"][key] = normalize_button_text(matched)
        form["step"] += 1
    elif key in APARTMENT_NUMERIC_FIELDS or key == "floor":
        normalized = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        if key == "floor":
            try: int(normalized)
            except ValueError:
                await message.reply_text(await localized("طبقه باید عدد صحیح باشد؛ برای زیرزمین عدد منفی و برای همکف ۰ وارد کنید.", language)); return True
        elif not normalized.isdigit():
            await message.reply_text(await localized("ورودی این مرحله باید فقط عدد صحیح و بدون علامت باشد.", language)); return True
        form["data"][key] = normalized
        form["step"] += 1
    else:
        form["data"][key] = text
        form["step"] += 1

    if form["step"] >= len(APARTMENT_STEPS):
        await finish_apartment_rent(update, context)
    else:
        await ask_apartment_step(message, context)
    return True

async def finish_apartment_rent(update, context):
    form = context.user_data.get("form")
    if not form:
        return
    data = form["data"]
    # Duplicate-property candidates are flagged for the main admin, not silently rejected.
    duplicate = False
    with connect_db() as conn:
        rows = conn.execute("SELECT id, user_id, data FROM submissions WHERE kind='rent_apartment_ad' AND status IN ('pending','approved','published')").fetchall()
    for row in rows:
        try: old = json.loads(row["data"])
        except Exception: continue
        if old.get("city", "").casefold() == data.get("city", "").casefold() and old.get("street", "").casefold() == data.get("street", "").casefold() and old.get("area") == data.get("area") and old.get("building_number") == data.get("building_number"):
            duplicate = True; data["possible_duplicate_of"] = row["id"]; break
    data["publication_date"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    data["views"] = 0
    submission_id = create_submission(update.effective_user.id, form["language"], form["kind"], data)
    language = form["language"]
    context.user_data.pop("form", None)
    await update.message.reply_text(await localized(f"آگهی شما با شناسه {submission_id} ثبت شد و پس از بررسی مدیر اصلی منتشر می‌شود.", language), reply_markup=main_keyboard(language))
    if duplicate:
        try: await context.bot.send_message(chat_id=ADMIN_ID, text=f"⚠️ احتمال آگهی تکراری: #{submission_id} شبیه آگهی #{data['possible_duplicate_of']} است.")
        except Exception: logger.exception("Could not alert admin about possible duplicate")
    await send_admin_review(context, submission_id)


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
            RENT_CATEGORY_PROMPTS.get(language, RENT_CATEGORY_PROMPTS["fa"]),
            reply_markup=submenu_keyboard(rent_category_options(language), language=language),
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
    ("office_document_type", "نوع سند/موقعیت اداری را انتخاب کنید:", ["📄 سند اداری", "📍 موقعیت اداری"]),
    ("office_property_type", "نوع ملک را انتخاب کنید:", ["🏢 آپارتمان", "🏛 مستغلات"]),
    ("area", "متراژ ملک را فقط با عدد وارد کنید:"),
    ("parking", "تعداد پارکینگ را انتخاب کنید:", count_options(6)),
    ("rooms", "تعداد اتاق را انتخاب کنید:", room_options()),
    ("elevator", "آسانسور دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("lobby", "لابی دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("city", "شهر را فقط با حروف وارد کنید:"),
    ("municipal_district", "منطقه شهرداری را فقط با عدد وارد کنید:"),
    ("street", "نام خیابان را فقط با حروف وارد کنید:"),
    ("alley", "نام کوچه یا خیابان فرعی را وارد کنید (عدد و حروف مجاز است):"),
    ("plaque", "شماره پلاک را فقط با عدد وارد کنید:"),
    ("deposit", "مبلغ رهن را فقط با عدد وارد کنید:"),
    ("rent", "مبلغ اجاره ماهانه را فقط با عدد وارد کنید:"),
    ("images", "در صورت تمایل حداکثر ۵ تصویر ملک را ارسال کنید و سپس «📷 پایان تصاویر» را بزنید."),
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
        keyboard = form_keyboard(
            [[KeyboardButton(await localized("📱 اشتراک‌گذاری شماره تلگرام", form["language"]), request_contact=True)],
             [await localized("❌ لغو ثبت", form["language"])]], form["language"]
        )
    elif key == "images":
        keyboard = form_keyboard([[await localized("📷 پایان تصاویر", form["language"])], [await localized("❌ لغو ثبت", form["language"])]], form["language"])
    elif options:
        rows = []
        for option_row in (options[0][i:i+5] for i in range(0, len(options[0]), 5)):
            rows.append([await localized(option, form["language"]) for option in option_row])
        rows.append([await localized("❌ لغو ثبت", form["language"])])
        keyboard = form_keyboard(rows, form["language"])
    else:
        keyboard = form_keyboard([], form["language"])
    if key != "contact":
        # Rebuild rows is difficult with an already built keyboard, so use a consistent compact keyboard.
        if options:
            rows = [[await localized(opt, form["language"]) for opt in options[0][i:i+5]] for i in range(0, len(options[0]), 5)]
        elif key == "images":
            rows = [[await localized("📷 پایان تصاویر", form["language"])]]
        else:
            rows = []
        rows.extend([[await localized(PREV_STEP_LABELS.get(form["language"], PREV_STEP_LABELS["fa"]), form["language"])], [await localized("❌ لغو ثبت", form["language"])]])
        keyboard = form_keyboard(rows, form["language"])
    await message.reply_text(await localized(prompt, form["language"]), reply_markup=keyboard)


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
    text = _strip_button_number((message.text or "").strip())
    language = form["language"]

    cancel_labels = {normalize_button_text(x) for x in CANCEL_FORM_BUTTONS}
    cancel_labels.add(normalize_button_text(await localized("❌ لغو ثبت", language)))
    if normalize_button_text(text) in cancel_labels:
        context.user_data.pop("form", None)
        await message.reply_text(await localized("ثبت آگهی لغو شد.", language), reply_markup=main_keyboard(language))
        return True
    previous_labels = {normalize_button_text(x) for x in PREV_STEP_LABELS.values()}
    previous_labels.add(normalize_button_text(await localized(PREV_STEP_LABELS.get(language, PREV_STEP_LABELS["fa"]), language)))
    if normalize_button_text(text) in previous_labels:
        if form["step"] > 0:
            form["step"] -= 1
            await ask_office_step(message, context)
        else:
            await message.reply_text(await localized("در اولین مرحله هستید.", language), reply_markup=main_keyboard(language))
        return True

    if message.contact:
        if OFFICE_STEPS[form["step"]][0] != "contact":
            await message.reply_text(await localized("لطفاً در مرحله درخواست‌شده پاسخ دهید.", language))
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
                + ("اکنون «📷 پایان تصاویر» را بفرستید یا تصویر بیشتری ارسال کنید." if len(form["images"]) >= 4 else f"حداقل {4-len(form['images'])} تصویر دیگر لازم است."),
                reply_markup=form_keyboard([[await localized("📷 پایان تصاویر", language)], [await localized("❌ لغو ثبت", language)]], language),
            )
            return True
        finish_labels = {"پایان تصاویر", normalize_button_text(await localized("📷 پایان تصاویر", language))}
        if normalize_button_text(text) in finish_labels:
            if len(form["images"]) < 4:
                await message.reply_text(await localized(f"حداقل ۴ تصویر لازم است. تاکنون {len(form['images'])} تصویر ارسال کرده‌اید.", language))
                return True
            form["step"] += 1
            await ask_office_step(message, context)
            return True
        await message.reply_text(await localized("لطفاً تصویر ملک ارسال کنید یا پس از ارسال حداقل ۴ تصویر، «📷 پایان تصاویر» را بفرستید.", language))
        return True

    if not text:
        await message.reply_text(await localized("لطفاً پاسخ را به‌صورت متن یا با دکمه مناسب ارسال کنید.", language))
        return True

    if key in {"office_document_type", "office_property_type", "elevator", "lobby", "parking", "rooms"}:
        allowed = OFFICE_STEPS[form["step"]][2]
        normalized_text = normalize_button_text(text)
        matched = None
        for option in allowed:
            shown = normalize_button_text(await localized(option, language))
            if normalized_text == shown or normalized_text == normalize_button_text(option):
                matched = option
                break
        if matched is None:
            await message.reply_text(await localized("لطفاً یکی از گزینه‌های نمایش‌داده‌شده را انتخاب کنید.", language))
            return True
        form["data"][key] = normalize_button_text(matched)
    elif key in {"area", "municipal_district", "plaque", "deposit", "rent"}:
        if not digits_only(text):
            await message.reply_text(await localized("ورودی این مرحله باید فقط عدد باشد. لطفاً دوباره وارد کنید.", language))
            return True
        form["data"][key] = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    elif key in {"city", "street"}:
        if not letters_only(text):
            await message.reply_text(await localized("لطفاً فقط حروف وارد کنید؛ از عدد و نشانه استفاده نکنید.", language))
            return True
        form["data"][key] = text
    elif key == "alley":
        if not any(ch.isalnum() or ch.isalpha() for ch in text):
            await message.reply_text(await localized("نام کوچه یا خیابان فرعی را با حروف یا عدد وارد کنید.", language))
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


# Field catalog for category-aware forms. Field order is deliberate; every form ends with
# a contact-sharing step and an explicit "finish and send to reviewer" action.
COMMON_LISTING_FIELDS = [
    ("title", "عنوان آگهی"), ("description", "توضیحات کامل ملک"),
    ("province", "استان"), ("city", "شهر"), ("district", "منطقه"),
    ("total_price", "قیمت کل (تومان)"), ("price_per_meter", "قیمت هر متر (در صورت اطلاع)"),
    ("negotiable", "قیمت قابل مذاکره است؟ (بله/خیر)"), ("payment_terms", "شرایط پرداخت"),
    ("delivery_status", "وضعیت تخلیه و تحویل"), ("viewing_time", "زمان مناسب بازدید"),
]
ROOM_TYPES = {"🏢 آپارتمان مسکونی", "🏡 ویلا و خانه مستقل", "🏢 دفتر کار و ملک اداری"}
BATHROOM_TYPES = {"🏡 ویلا و خانه مستقل", "🏭 ملک صنعتی، کارخانه و کارگاه", "🏬 مغازه و ملک تجاری"}
PARKING_TYPES = {"🏢 آپارتمان مسکونی", "🏡 ویلا و خانه مستقل", "🏢 دفتر کار و ملک اداری", "🏬 مغازه و ملک تجاری", "🏭 ملک صنعتی، کارخانه و کارگاه", "🏚 ملک کلنگی"}
TITLE_TYPES = {"🏢 آپارتمان مسکونی", "🏡 ویلا و خانه مستقل", "🏢 دفتر کار و ملک اداری", "🏬 مغازه و ملک تجاری", "🏭 ملک صنعتی، کارخانه و کارگاه", "🌳 زمین و باغ", "🏚 ملک کلنگی"}
RESIDENTIAL_AMENITIES = ["آسانسور", "انباری", "بالکن یا تراس", "استخر", "سونا و جکوزی", "حیاط و فضای سبز", "سیستم گرمایش و سرمایش", "نگهبانی و دوربین مداربسته", "روف‌گاردن", "لابی و لابی‌من"]
OFFICE_AMENITIES = ["برِ خیابان اصلی", "ویترین یا نمای تجاری", "تعداد طبقات", "تعداد واحدها", "تعداد اتاق و فضای تفکیک‌شده", "سرویس بهداشتی", "آشپزخانه یا آبدارخانه", "آسانسور", "پارکینگ", "انبار یا زیرزمین", "برق سه‌فاز", "سیستم تهویه مطبوع", "نوع فعالیت مناسب", "سند اداری یا تجاری", "امکان نصب تابلو", "سایر امکانات"]
INDUSTRIAL_FIELDS = ["نوع فعالیت صنعتی مجاز", "برق سه‌فاز و ظرفیت برق", "ظرفیت گاز صنعتی", "آب و فاضلاب صنعتی", "ارتفاع سقف سوله", "دهانه و عرض سالن", "جرثقیل سقفی و ظرفیت آن", "تعداد دروازه‌های ورود و خروج", "دسترسی کامیون و تریلی", "بارانداز و محل بارگیری", "دفتر اداری داخل مجموعه", "انبار و سالن تولید", "سیستم تهویه و اگزاست", "سیستم اطفای حریق", "مجوزهای صنعتی و بهره‌برداری", "پروانه بهره‌برداری", "وضعیت سند و کاربری صنعتی", "امکانات دیگر"]
LAND_FIELDS = ["نوع زمین: مسکونی، تجاری، صنعتی یا کشاورزی", "طول بر و عمق زمین", "عرض گذر و دسترسی خیابان", "تعداد برِ زمین", "وضعیت آب، برق، گاز و تلفن", "چاه آب و مجوز آن", "سهمیه یا حق‌آبه", "نوع درختان و تعداد آن‌ها", "سن درختان", "وضعیت سند و مالکیت", "کاربری و مجوز ساخت", "تراکم و سطح اشغال مجاز", "تعداد طبقات مجاز", "امکان تفکیک زمین", "شمالی یا جنوبی بودن زمین", "وضعیت دیوارکشی و محصور بودن", "دسترسی ماشین‌آلات و خودرو", "شیب زمین", "سایر مشخصات"]
OLD_BUILDING_FIELDS = ["متراژ بنای موجود", "سن بنا", "تعداد طبقات فعلی", "تعداد واحدهای موجود", "تعداد برِ زمین", "عرض گذر", "وضعیت تخریب بنا", "تراکم و تعداد طبقات مجاز ساخت", "امکان ساخت‌وساز مجدد", "وجود مستأجر", "شرایط و مهلت تخلیه", "کاربری فعلی", "سطح اشغال مجاز", "وضعیت انشعابات آب و برق و گاز", "وضعیت تخلیه ملک", "قیمت هر متر زمین", "سایر مشخصات"]
VILLA_FIELDS = ["نوع ویلا: مستقل، شهرکی یا باغ‌ویلا", "مساحت محوطه و حیاط", "مساحت زیربنای هر طبقه", "تعداد طبقات", "استخر سرپوشیده یا روباز", "سونا خشک و بخار و جکوزی", "حوضچه آب سرد", "آلاچیق و باربیکیو", "فضای سبز و محوطه‌سازی", "موتورخانه و تجهیزات تأسیسات", "سیستم تصفیه استخر", "پارکینگ مسقف یا روباز", "آب، برق، گاز و انشعابات", "چاه آب و مجوز", "نگهبانی و امنیت شهرک", "سند زمین و بنا", "سیستم هوشمندسازی ساختمان", "ژنراتور برق اضطراری", "سایر امکانات"]
CONSTRUCTION_FIELDS = ["نقش ثبت‌کننده: مالک، سازنده یا سرمایه‌گذار", "نوع ملک یا زمین موضوع مشارکت", "مساحت زمین", "متراژ بنای موجود", "عرض گذر و تعداد برِ زمین", "وضعیت سند و مالکیت", "کاربری و تراکم مجاز", "تعداد طبقات مجاز ساخت", "درصد سهم پیشنهادی مالک", "درصد سهم پیشنهادی سازنده", "میزان بلاعوض درخواستی یا پیشنهادی", "سابقه و نمونه پروژه‌های سازنده", "مجوزها و وضعیت شهرداری", "وضعیت تخلیه ملک", "شرایط اختصاصی توافق"]
INVESTMENT_FIELDS = ["نوع سرمایه‌گذاری: خرید، ساخت، مشارکت یا تکمیل پروژه", "نوع ملک و موقعیت پروژه", "ارزش کل پروژه", "مبلغ سرمایه موردنیاز", "حداقل مبلغ ورود سرمایه‌گذار", "میزان سرمایه تأمین‌شده تاکنون", "درصد سهم یا بازده پیشنهادی", "مدت سرمایه‌گذاری", "وضعیت مجوزها", "وضعیت سند و مالکیت", "روش خروج و تسویه سرمایه‌گذار", "تضمین‌ها و وثایق", "سابقه مجری یا سازنده", "ریسک‌ها و تعهدات سرمایه‌گذاری", "شرایط اختصاصی پروژه", "هزینه‌های باقی‌مانده پروژه", "گزارش کارشناسی و ارزیابی ملک", "تعداد شرکای موردنیاز"]
BUY_REQUEST_FIELDS = ["هدف خرید: سکونت، کسب‌وکار یا سرمایه‌گذاری", "خرید نقدی یا اقساطی", "میزان پیش‌پرداخت و شرایط اقساط", "آمادگی برای خرید فوری", "درخواست خرید با مشارکت یا معاوضه", "حداکثر قیمت هر متر", "امکان خرید ملک نیازمند بازسازی"]
RENT_REQUEST_FIELDS = ["حداکثر مبلغ اجاره ماهانه", "حداقل و حداکثر مبلغ ودیعه", "امکان تبدیل ودیعه به اجاره", "تاریخ شروع اجاره", "نوع قرارداد: بلندمدت", "نیاز به ملک مبله یا غیرمبله", "امکان تمدید قرارداد", "مناسب بودن برای خانواده یا مجرد", "مناسب بودن برای حیوان خانگی", "آمادگی برای پرداخت ودیعه بیشتر جهت اجاره کمتر"]


def build_form_fields(kind, category, menu_mode):
    """Build category-aware, approved real-estate forms. Private fields stay admin-only."""
    fields = []
    cat = (category or "").strip()
    residential = any(x in cat for x in ("آپارتمان", "ویلا", "خانه مستقل", "پنت‌هاوس", "باغ‌ویلا", "مسکونی"))
    office = any(x in cat for x in ("اداری", "دفتر کار", "دفتر", "office"))
    commercial = any(x in cat for x in ("تجاری", "مغازه", "واحد تجاری"))
    industrial = any(x in cat for x in ("صنعتی", "کارخانه", "کارگاه", "سوله", "انبار"))
    land = any(x in cat for x in ("زمین", "باغ", "کشاورزی"))
    old = "کلنگی" in cat
    portfolio = any(x in cat for x in ("مستغلات", "ساختمان", "سبد", "پرتفوی"))

    def add(key, prompt):
        fields.append((key, prompt))

    # Buy/rent listing forms: no title field; category itself is the listing type.
    if menu_mode in {"buy", "rent"}:
        add("province", "استان ملک")
        add("city", "شهر ملک")
        add("district", "منطقه یا محله (بدون نشانی دقیق)")
        add("area", "متراژ ملک به مترمربع")
        if menu_mode == "buy":
            add("total_price", "قیمت کل به تومان")
            add("price_per_meter", "قیمت هر مترمربع به تومان؛ در صورت نامشخص بودن بنویسید نامشخص")
            add("negotiable", "قیمت قابل مذاکره است؟ بله یا خیر")
        else:
            add("deposit", "مبلغ ودیعه/رهن به تومان؛ بدون ودیعه عدد صفر")
            add("rent", "اجاره ماهانه به تومان؛ بدون اجاره عدد صفر")
        if residential:
            add("rooms", "تعداد اتاق خواب")
            add("master_rooms", "تعداد اتاق مستر؛ اگر ندارد صفر")
            add("floor", "طبقه واحد؛ همکف صفر و زیرزمین عدد منفی")
            add("total_floors", "تعداد کل طبقات ساختمان")
            add("amenities", "امکانات ملک را انتخاب کنید؛ در پایان «پایان انتخاب امکانات» را بزنید")
            add("parking", "تعداد پارکینگ")
            add("building_age", "سن بنا")
        elif office or commercial:
            add("floor", "طبقه واحد؛ همکف صفر و زیرزمین عدد منفی")
            add("total_floors", "تعداد کل طبقات ساختمان")
            add("amenities", "امکانات ملک را انتخاب کنید؛ در پایان «پایان انتخاب امکانات» را بزنید")
            add("parking", "تعداد پارکینگ")
        elif industrial:
            for prompt in INDUSTRIAL_FIELDS:
                add("industrial_" + str(len(fields)), prompt)
        elif land:
            for prompt in LAND_FIELDS:
                add("land_" + str(len(fields)), prompt)
        elif old:
            for prompt in OLD_BUILDING_FIELDS:
                add("old_" + str(len(fields)), prompt)
        elif portfolio:
            add("building_type", "نوع ساختمان: مسکونی، تجاری، اداری یا مختلط")
            add("total_floors", "تعداد طبقات")
            add("occupancy", "وضعیت اشغال یا تخلیه")
        # سن بنا ممکن است قبلاً برای دسته‌های مسکونی یا ساختمان قدیمی اضافه شده باشد؛
        # فقط در صورت نبودن این فیلد، یک‌بار آن را اضافه کن.
        if not any(key == "building_age" or "سن بنا" in str(prompt) for key, prompt in fields):
            add("building_age", "سن بنا")
        if menu_mode != "rent":
            add("deed_status", "وضعیت سند")
        add("delivery_status", "وضعیت تخلیه و تحویل")
        add("description", "توضیحات تکمیلی و ویژگی‌های مهم ملک")
        add("images_choice", "📷 آیا تمایل به ارسال تصویر دارید؟")
        add("images", "تصاویر ملک؛ حداکثر ۵ تصویر؛ پس از ارسال پایان تصاویر را انتخاب کنید")
        add("viewing_time", "زمان‌های مناسب برای بازدید")
        add("contact", "شماره تماس خود را فقط با دکمه اشتراک‌گذاری تلگرام ارسال کنید؛ فقط مدیر اصلی می‌بیند")
        return fields

    # Requests: no property photos and no collection of the registrant's public contact details.
    if menu_mode == "buy_req":
        for key, prompt in [
            ("province", "استان‌های موردنظر"), ("city", "شهرها و محله‌های موردنظر"),
            ("min_area", "حداقل متراژ به مترمربع"), ("max_area", "حداکثر متراژ به مترمربع"),
            ("budget_min", "حداقل بودجه خرید به تومان؛ اگر محدودیتی ندارید صفر"),
            ("budget_max", "حداکثر بودجه خرید به تومان"),
            ("purchase_purpose", "هدف خرید: سکونت، کسب‌وکار یا سرمایه‌گذاری"),
            ("payment_type", "روش پرداخت: نقدی، اقساطی یا هر دو"),
            ("building_age", "حداکثر سن بنا یا سال ساخت موردنظر"),
            ("amenities", "امکانات ضروری موردنظر"), ("requirements_summary", "شرایط و توضیحات تکمیلی"),
            ("transaction_timing", "زمان تقریبی خرید"),
        ]: add(key, prompt)
        return fields

    if menu_mode == "rent_req":
        for key, prompt in [
            ("province", "استان‌های موردنظر"), ("city", "شهرها و محله‌های موردنظر"),
            ("min_area", "حداقل متراژ به مترمربع"), ("max_area", "حداکثر متراژ به مترمربع"),
            ("deposit_min", "حداقل ودیعه به تومان"), ("deposit_max", "حداکثر ودیعه به تومان"),
            ("rent_min", "حداقل اجاره ماهانه به تومان"), ("rent_max", "حداکثر اجاره ماهانه به تومان"),
            ("negotiation", "امکان تبدیل ودیعه به اجاره یا مذاکره بر سر مبلغ"),
            ("start_date", "تاریخ شروع اجاره"), ("furnished", "مبله یا غیرمبله"),
            ("contract_term", "مدت قرارداد؛ بلندمدت"), ("renewal", "امکان تمدید قرارداد"),
            ("occupants", "مناسب خانواده، مجرد یا هر دو"), ("pets", "شرایط نگهداری حیوان خانگی"),
            ("amenities", "امکانات ضروری موردنظر"), ("requirements_summary", "شرایط و توضیحات تکمیلی"),
        ]: add(key, prompt)
        return fields

    # Participation in construction has three distinct pathways selected by a submenu.
    if menu_mode == "construction_owner":
        for key, prompt in [
            ("property_type", "نوع ملک یا زمین"), ("province", "استان"), ("city", "شهر"),
            ("land_area", "متراژ زمین به مترمربع"), ("existing_built_area", "متراژ زیربنای موجود"),
            ("dimensions_frontage", "ابعاد زمین و عرض بر"), ("deed_status", "وضعیت سند"),
            ("permit_status", "وضعیت پروانه ساخت"), ("density_floors", "تراکم و تعداد طبقات مجاز"),
            ("occupancy", "وضعیت تخلیه یا سکونت ملک"), ("cash_component", "مبلغ بلاعوض موردنظر"),
            ("owner_share", "درصد مشارکت پیشنهادی مالک"), ("images", "تصاویر ملک یا زمین؛ ۱ تا ۵ تصویر"),
            ("description", "توضیحات و شرایط مالک"),
            ("contact", "شماره تماس را با دکمه اشتراک‌گذاری تلگرام ارسال کنید؛ فقط مدیر اصلی می‌بیند"),
        ]: add(key, prompt)
        return fields
    if menu_mode == "construction_builder":
        for key, prompt in [
            ("builder_name", "نام شخص یا شرکت سازنده"), ("province_city_scope", "استان و شهرهای مورد فعالیت"),
            ("experience", "سابقه ساخت‌وساز"), ("completed_projects", "تعداد پروژه‌های اجراشده"),
            ("acceptable_projects", "نوع پروژه‌های قابل قبول"), ("land_area_range", "حداقل و حداکثر متراژ زمین موردنظر"),
            ("max_floors", "حداکثر تعداد طبقات قابل ساخت"), ("proposed_share", "درصد مشارکت پیشنهادی"),
            ("cash_component", "امکان پرداخت بلاعوض و سقف مبلغ"), ("description", "توضیحات سازنده"),
            ("images", "تصاویر پروژه‌های قبلی؛ ۱ تا ۵ تصویر (در صورت وجود)"),
            ("contact", "شماره تماس را با دکمه اشتراک‌گذاری تلگرام ارسال کنید؛ فقط مدیر اصلی می‌بیند"),
        ]: add(key, prompt)
        return fields
    if menu_mode == "construction_partner":
        for key, prompt in [
            ("property_type", "نوع ملک یا پروژه"), ("province", "استان"), ("city", "شهر"),
            ("land_area", "متراژ زمین"), ("completed_area", "متراژ زیربنای اجراشده"),
            ("remaining_area", "متراژ زیربنای باقی‌مانده"), ("floors_units", "تعداد طبقات و واحدها"),
            ("construction_stage", "مرحله فعلی ساخت"), ("progress_percent", "درصد پیشرفت پروژه"),
            ("deed_status", "وضعیت سند"), ("permit_status", "وضعیت پروانه و مجوزها"),
            ("capital_needed", "میزان سرمایه موردنیاز برای تکمیل"), ("completion_cost", "برآورد هزینه تکمیل پروژه"),
            ("completion_time", "زمان تقریبی لازم برای تکمیل"), ("description", "توضیحات پروژه"),
            ("images", "تصاویر فعلی پروژه؛ ۱ تا ۵ تصویر"),
            ("contact", "شماره تماس را با دکمه اشتراک‌گذاری تلگرام ارسال کنید؛ فقط مدیر اصلی می‌بیند"),
        ]: add(key, prompt)
        return fields

    # Presale project-level and per-unit information are supported in a single structured submission.
    if menu_mode == "presale":
        for key, prompt in [
            ("project_name", "نام پروژه"), ("builder_name", "نام سازنده یا شرکت سازنده"),
            ("property_type", "نوع ملک: آپارتمان، ویلا، واحد تجاری، واحد اداری، ساختمان تجاری یا ساختمان اداری"),
            ("province", "استان"), ("city", "شهر"), ("land_area", "متراژ زمین پروژه"),
            ("total_built_area", "زیربنای کل پروژه"), ("total_floors", "تعداد کل طبقات"),
            ("deed_status", "وضعیت سند زمین"),
            ("project_images", "تصاویر کلی پروژه؛ ۱ تا ۵ تصویر"), ("project_description", "توضیحات کلی پروژه"),
            ("unit_count_to_add", "چند واحد می‌خواهید به این پروژه اضافه کنید؟ عدد وارد کنید"),
            ("contact", "شماره تماس سازنده را با دکمه اشتراک‌گذاری تلگرام ارسال کنید؛ فقط مدیر اصلی می‌بیند"),
        ]: add(key, prompt)
        return fields

    # Investment / other forms remain structured without asking for a standalone ad title.
    if menu_mode == "investment":
        for key, prompt in [
            ("province", "استان"), ("city", "شهر و موقعیت کلی پروژه"),
            ("investment_type", "نوع سرمایه‌گذاری: خرید، ساخت، مشارکت یا تکمیل پروژه"),
            ("project_value", "ارزش کل پروژه"), ("investment_amount", "مبلغ سرمایه موردنیاز"),
            ("minimum_investment", "حداقل مبلغ ورود سرمایه‌گذار"), ("funded_amount", "میزان سرمایه تأمین‌شده تاکنون"),
            ("proposed_share", "درصد سهم یا بازده پیشنهادی"), ("duration", "مدت سرمایه‌گذاری"),
            ("permit_status", "وضعیت مجوزها"), ("deed_status", "وضعیت سند و مالکیت"),
            ("exit_method", "روش خروج و تسویه سرمایه‌گذار"), ("guarantees", "تضمین‌ها و وثایق"),
            ("remaining_cost", "هزینه‌های باقی‌مانده پروژه"), ("description", "توضیحات و ریسک‌های پروژه"),
        ]: add(key, prompt)
        add("contact", "شماره تماس را با دکمه اشتراک‌گذاری تلگرام ارسال کنید؛ فقط مدیر اصلی می‌بیند")
        return fields

    # Fallback form for any legacy kind.
    for key, prompt in [("province", "استان"), ("city", "شهر و منطقه"), ("description", "توضیحات ضروری")]: add(key, prompt)
    add("contact", "شماره تماس را با دکمه اشتراک‌گذاری تلگرام ارسال کنید؛ فقط مدیر اصلی می‌بیند")
    return fields
async def begin_form(update, context, kind, language, category=None, menu_mode=None):
    context.user_data["awaiting_support"] = False
    context.user_data.pop("rent_menu", None)
    category = category or context.user_data.pop("selected_category", "")
    menu_mode = menu_mode or context.user_data.pop("selected_menu_mode", "")
    if not menu_mode:
        menu_mode = {"sell_ad":"buy", "rent_ad":"rent", "buy_req":"buy_req", "rent_req":"rent_req", "builder":"investment"}.get(kind, "buy")
    form_kind = {"buy":"sell_ad", "rent":"rent_ad", "buy_req":"buy_req", "rent_req":"rent_req", "investment":"builder", "construction":"builder", "construction_owner":"builder", "construction_builder":"builder", "construction_partner":"builder", "presale":"builder"}.get(menu_mode, kind)
    fields = build_form_fields(form_kind, category, menu_mode)
    # A request to buy/rent is a request, not a property listing: never ask its author for property photos.
    if menu_mode in {"buy_req", "rent_req"}:
        fields = [(key, prompt) for key, prompt in fields if key != "images"]
    context.user_data["form"] = {"kind": form_kind, "language": language, "step": 0, "data": {"property_type": category, "menu_mode": menu_mode, "source_language": language}, "mode": "complete", "fields": fields, "field_index": 0, "images": [], "awaiting_images": False}
    await ask_complete_form_step(update.message, context)

# Choice-first UI for all structured fields. Only geographic names, exact address,
# and genuinely descriptive fields remain free-text; monetary fields accept digits only.
PREV_STEP_LABELS = {
    "fa": "⬅️ مرحله قبل", "en": "⬅️ Previous Step", "az": "⬅️ Əvvəlki addım",
    "tr": "⬅️ Önceki adım", "ar": "⬅️ الخطوة السابقة", "zh": "⬅️ 上一步", "ru": "⬅️ Предыдущий шаг",
}

def _field_choice_options(key, prompt, selected_rooms=None):
    k = (key or "").lower()
    p = (prompt or "").lower()
    if any(x in k for x in ("negotiable", "negotiation", "renewal", "furnished", "pets", "permit_status", "deed_status", "delivery_status", "occupancy", "elevator", "lobby", "balcony", "terrace", "pool", "parking_available", "images_choice", "installments")) or any(x in p for x in ("بله یا خیر", "قابل مذاکره", "آسانسور", "استخر", "سونا", "جکوزی", "بالکن", "تراس", "مبله", "تمدید قرارداد", "حیوان خانگی", "پروانه ساخت", "وضعیت سند", "وضعیت تخلیه", "اقساطی")):
        if any(x in k for x in ("deed_status",)) or "وضعیت سند" in p:
            return ["شش‌دانگ", "تک‌برگ", "مشاع", "قولنامه‌ای", "در دست اقدام", "فاقد سند", "سایر"]
        if "permit_status" in k or "پروانه ساخت" in p:
            return ["دارد", "در حال اخذ", "ندارد", "نیاز ندارد", "نامشخص"]
        if "occupancy" in k or "تخلیه" in p:
            return ["تخلیه", "مالک ساکن است", "مستأجر دارد", "در حال تخلیه", "نامشخص"]
        if "furnished" in k or "مبله" in p:
            return ["مبله", "نیمه‌مبله", "غیرمبله"]
        if "pets" in k or "حیوان خانگی" in p:
            return ["مجاز است", "مجاز نیست", "با توافق"]
        if "renewal" in k:
            return ["بله", "خیر", "با توافق"]
        if "installments" in k or "اقساطی" in p:
            return ["بله", "خیر", "با توافق"]
        return ["بله", "خیر"]
    # Area fields are always free numeric input; never show range buttons.
    if "parking" in k or "تعداد پارکینگ" in p or "تعداد جای پارک" in p:
        return ["1", "2", "3", "4", "+5"]
    if k in {"rooms", "bedrooms"} or "تعداد اتاق" in p:
        return ["1", "2", "3", "4", "+5"]
    if "master_rooms" in k or "تعداد اتاق مستر" in p:
        return master_room_options(selected_rooms)
    if "total_floors" in k or "تعداد کل طبقات" in p:
        return ["1", "2", "3", "4", "5", "6", "+7"]
    if any(x in k for x in ("storage", "balcony_count", "total_floors", "units_per_floor", "completed_projects", "partners_needed", "unit_count_to_add")) or any(x in p for x in ("تعداد انباری", "تعداد بالکن", "تعداد طبقات", "تعداد واحد", "تعداد پروژه", "تعداد شرکا")):
        return [str(i) for i in range(0, 11)] + ["+10"]
    if k in {"floor", "unit_floor"} or "طبقه واحد" in p:
        return ["0", "2", "3", "4", "5", "6", "+7"]
    if "progress" in k or "درصد پیشرفت" in p:
        return ["۰٪", "۱۰٪", "۲۰٪", "۳۰٪", "۴۰٪", "۵۰٪", "۶۰٪", "۷۰٪", "۸۰٪", "۹۰٪", "۱۰۰٪"]
    if "stage" in k or "مرحله فعلی ساخت" in p:
        return ["پیش از شروع", "گودبرداری", "فونداسیون", "اسکلت", "سفت‌کاری", "نازک‌کاری", "تأسیسات", "پایان کار", "آماده تحویل"]
    if "payment_type" in k or "روش پرداخت" in p:
        return ["نقدی", "اقساطی", "نقدی یا اقساطی", "تهاتر", "توافقی"]
    if "purpose" in k or "هدف خرید" in p:
        return ["سکونت", "کسب‌وکار", "سرمایه‌گذاری", "مصرفی و سرمایه‌گذاری"]
    if "contract_term" in k or "مدت قرارداد" in p:
        return ["یک‌ساله", "دو‌ساله", "بلندمدت", "توافقی"]
    if "start_date" in k or "زمان تحویل" in p or "زمان تقریبی" in p:
        return ["فوری", "تا یک ماه", "۱ تا ۳ ماه", "۳ تا ۶ ماه", "بیش از ۶ ماه", "توافقی"]
    if "type" in k and any(x in k for x in ("property", "investment", "building")):
        return ["آپارتمان", "ویلا", "خانه مستقل", "زمین", "باغ", "واحد تجاری", "واحد اداری", "ساختمان تجاری", "ساختمان اداری", "کارخانه", "کارگاه", "سوله یا انبار", "مختلط", "سایر"]
    if "amenit" in k or "امکانات" in p:
        return ["آسانسور", "پارکینگ", "انباری", "بالکن یا تراس", "استخر", "سونا و جکوزی", "حیاط و فضای سبز", "روف‌گاردن", "لابی", "نگهبانی", "سیستم هوشمند", "سایر امکانات", "ندارد", "پایان انتخاب امکانات"]
    if "viewing" in k or "زمان‌های مناسب برای بازدید" in p:
        return ["همه‌روزه با هماهنگی", "روزهای کاری", "آخر هفته", "صبح‌ها", "بعدازظهرها", "فقط با هماهنگی قبلی"]
    if "building_age" in k or "سن بنا" in p:
        return ["نوساز تا ۵ سال", "۵ تا ۱۵ سال", "۱۵ تا ۲۰ سال", "بیشتر از ۲۰ سال"]
    if "images_choice" in k:
        return ["بله", "خیر"]
    return None

NUMERIC_ONLY_KEYS = {"area", "land_area", "existing_built_area", "completed_area", "remaining_area", "total_built_area", "total_price", "price_per_meter", "deposit", "rent", "deposit_min", "deposit_max", "rent_min", "rent_max", "budget_min", "budget_max", "project_value", "investment_amount", "minimum_investment", "funded_amount", "capital_needed", "completion_cost", "cash_component", "municipal_district", "progress_percent", "max_floors", "density_floors", "plaque", "building_number", "unit_number", "unit_count_to_add", "max_area", "min_area", "land_area_range"}

async def ask_complete_form_step(message, context):
    form = context.user_data.get("form")
    if not form: return
    fields = form["fields"]
    idx = form["step"]
    lang = form["language"]
    if idx >= len(fields):
        await message.reply_text(await localized("فرم تکمیل شده است. برای ارسال، دکمه «پایان و ارسال به ناظر» را بزنید.", lang), reply_markup=form_keyboard([["✅ پایان و ارسال به ناظر"], ["❌ لغو ثبت"]], lang))
        return
    key, prompt = fields[idx]
    if key == "images":
        if form.get("data", {}).get("images_submitted") != "yes":
            form["step"] += 1
            await ask_complete_form_step(message, context)
            return
        form["awaiting_images"] = True
        rows = [["📷 پایان تصاویر"], [await localized(PREV_STEP_LABELS.get(lang, PREV_STEP_LABELS["fa"]), lang)], ["❌ لغو ثبت"]]
        await message.reply_text("📝 " + await localized(prompt, lang) + f"\nتعداد تصاویر انتخاب‌شده: {len(form.get('images', []))}/5", reply_markup=form_keyboard(rows, lang))
        return
    if key == "video_note":
        form["awaiting_video"] = True
        await message.reply_text("ویدئوی ملک را ارسال کنید؛ اگر ویدئویی ندارید، «ندارد» را بنویسید. پس از ارسال، «پایان ویدئوها» را بزنید.", reply_markup=form_keyboard([["🎬 پایان ویدئوها"], ["❌ لغو ثبت"]], lang))
        return
    if key == "contact":
        # Telegram only offers request_contact in a private chat. Keep this as a real
        # contact-request button and do not wrap it in the generic text-button builder.
        contact_button = KeyboardButton(
            await localized("📱 اشتراک‌گذاری شماره تماس", lang),
            request_contact=True,
        )
        rows = [[contact_button], [await localized("❌ لغو ثبت", lang)]]
        await message.reply_text(
            "📝 " + await localized(prompt, lang),
            reply_markup=ReplyKeyboardMarkup(
                rows, resize_keyboard=True, one_time_keyboard=False, is_persistent=True
            ),
        )
        return
    choices = _field_choice_options(key, prompt, form.get("data", {}).get("rooms"))
    if choices:
        rows = []
        shown_choices = [await localized(x, lang) for x in choices]
        rows.extend([shown_choices[i:i+3] for i in range(0, len(shown_choices), 3)])
    else:
        rows = []
    rows.append([await localized(PREV_STEP_LABELS.get(lang, PREV_STEP_LABELS["fa"]), lang)])
    rows.append([await localized("❌ لغو ثبت", lang)])
    # Do not display a frightening total-step counter; show only the current question.
    await message.reply_text("📝 " + await localized(prompt, lang), reply_markup=form_keyboard(rows, lang))

async def submit_complete_form(update, context):
    form = context.user_data.get("form")
    if not form: return False
    data = form["data"]
    images = form.get("images", [])
    menu_mode = data.get("menu_mode", "")
    # Photos are required only for an actual property listing, never for a buyer/renter request.
    if menu_mode in {"buy_req", "rent_req"}:
        form["awaiting_images"] = False
        data.pop("images", None)
    elif form.get("awaiting_images"):
        if not images:
            await update.message.reply_text("برای آگهی ملک حداقل یک تصویر الزامی است.")
            return True
        data["images"] = images
        form["awaiting_images"] = False
    if "contact" in form.get("fields", [])[form["step"]:] and not data.get("contact_user_id"):
        await update.message.reply_text("ابتدا شماره تماس را با دکمه اشتراک‌گذاری شماره تلگرام ارسال کنید.")
        return True
    if form.get("mode") != "complete": return False
    submission_id = create_submission(update.effective_user.id, form["language"], form["kind"], data)
    context.user_data.pop("form", None)
    messages = {
        "fa": f"✅ فرم شما با کد پیگیری {submission_id} برای بررسی و تأیید به ناظر ارسال شد. تا تأیید مدیریت، منتشر نمی‌شود.",
        "en": f"✅ Form #{submission_id} was sent to the reviewer. It will not be published before admin approval.",
        "az": f"✅ Forma #{submission_id} yoxlanış üçün göndərildi.", "tr": f"✅ Form #{submission_id} incelemeye gönderildi.",
        "ar": f"✅ تم إرسال النموذج رقم {submission_id} للمراجعة.", "zh": f"✅ 表单 #{submission_id} 已提交审核。", "ru": f"✅ Форма #{submission_id} отправлена на проверку."
    }
    await update.message.reply_text(messages.get(form["language"], messages["fa"]), reply_markup=main_keyboard(form["language"]))
    await send_admin_review(context, submission_id)
    return True


# ==================== ADMIN REVIEW ====================

def review_keyboard(submission_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(numbered_button("✅ تأیید و انتخاب زبان انتشار"), callback_data=f"approve:{submission_id}")],
        [InlineKeyboardButton(numbered_button("❌ رد"), callback_data=f"reject:{submission_id}")],
    ])


async def render_submission(data, kind, language, source_language, admin_view=False):
    translated = await translate_submission_data(data, source_language, language)
    lines = [f"🏡 <b>{escape(KINDS.get(kind, KINDS['rent_ad']).get(language, KINDS.get(kind, KINDS['rent_ad'])['fa']))}</b>", ""]
    if kind == "rent_apartment_ad" and not admin_view:
        labels = {"area":"متراژ", "rooms":"تعداد اتاق خواب", "master_rooms":"تعداد اتاق مستر", "terrace":"تراس", "lobby":"لابی", "caretaker":"سرایدار مقیم", "elevator":"آسانسور", "parking":"پارکینگ", "parking_spaces":"تعداد جای پارک", "shared_pool":"امکانات آبی مشترک", "roof_garden":"روف‌گاردن", "floor":"طبقه", "building_age":"سن بنا", "furnished":"مبله بودن", "pets":"حیوان خانگی", "total_floors":"تعداد طبقات ساختمان", "city":"شهر", "municipal_district":"منطقه شهرداری", "street":"خیابان اصلی", "deposit":"رهن (تومان)", "rent":"اجاره ماهانه (تومان)", "details":"توضیحات", "listing_role":"نوع ثبت‌کننده", "publication_date":"تاریخ انتشار"}
        for key, label in labels.items():
            value = str(data.get(key, "")).strip()
            if key == "listing_role": value = "مالک" if value == "owner" else "مشاور املاک / واسطه"
            if value: lines.append(f"<b>{escape(label)}:</b> {escape(value)}")
        lines.append(f"<b>شناسه آگهی:</b> {submission_id if 'submission_id' in locals() else ''}")
        lines.append(f"<b>تعداد تصاویر:</b> {len(data.get('images', []))}")
        return "\n".join(lines)
    if kind == "rent_apartment_ad":
        labels = {
            "listing_role": "نوع ثبت‌کننده", "agent_name": "نام مشاور (فقط مدیر اصلی)", "agency_name": "دفتر املاک (فقط مدیر اصلی)",
            "area": "متراژ", "rooms": "تعداد اتاق خواب", "master_rooms": "تعداد اتاق مستر", "terrace": "تراس", "lobby": "لابی", "caretaker": "سرایدار مقیم", "elevator": "آسانسور", "parking": "پارکینگ", "parking_spaces": "تعداد جای پارک", "shared_pool": "امکانات آبی مشترک", "roof_garden": "روف‌گاردن", "floor": "طبقه", "building_age": "سن بنا", "furnished": "وضعیت مبله", "pets": "حیوان خانگی", "total_floors": "تعداد کل طبقات", "city": "شهر", "municipal_district": "منطقه شهرداری", "street": "خیابان اصلی", "alley": "کوچه (فقط مدیر اصلی)", "building_number": "پلاک (فقط مدیر اصلی)", "unit_number": "شماره واحد (فقط مدیر اصلی)", "deposit": "مبلغ رهن (تومان)", "rent": "اجاره ماهانه (تومان)", "details": "توضیحات", "contact": "شماره تماس (فقط مدیر اصلی)", "telegram_user_id": "شناسه تلگرام (فقط مدیر اصلی)", "telegram_username": "نام کاربری تلگرام (فقط مدیر اصلی)", "possible_duplicate_of": "احتمال تکراری بودن با آگهی", "publication_date": "تاریخ ثبت"
        }
        for key, label in labels.items():
            value = str(translated.get(key, "")).strip()
            if value:
                lines.append(f"<b>{escape(label)}:</b> {escape(value)}")
        lines.append(f"<b>تعداد تصاویر:</b> {len(data.get('images', []))}")
        for index, file_id in enumerate(data.get("images", []), start=1):
            lines.append(f"<b>شناسه تصویر {index}:</b> <code>{escape(file_id)}</code>")
    elif kind == "rent_office_ad":
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
        prompt_by_key = {}
        for menu_mode in ("buy", "rent", "buy_req", "rent_req", "investment", "construction"):
            for category in ("", "🏢 آپارتمان مسکونی", "🏡 ویلا و خانه مستقل", "🌳 زمین و باغ", "🏬 مغازه و ملک تجاری", "🏢 دفتر کار و ملک اداری", "🏭 ملک صنعتی، کارخانه و کارگاه", "🏗 سوله و انبار", "🏚 ملک کلنگی", "🏙 مستغلات و مجتمع تجاری"):
                try:
                    prompt_by_key.update({k: label for k, label in build_form_fields(kind, category, menu_mode)})
                except Exception:
                    pass
        private_keys = {"exact_address", "contact", "contact_user_id", "telegram_user_id", "telegram_username", "images", "videos", "map_location"}
        metadata_keys = {"source_language", "menu_mode", "contact_user_id", "telegram_user_id", "telegram_username"}
        for key, raw_value in translated.items():
            if key in metadata_keys:
                continue
            if key in {"property_type", "menu_mode", "source_language", "registrant_type"} and not raw_value:
                continue
            if not admin_view and key in private_keys:
                continue
            if key in {"images", "videos"}:
                continue
            value = str(raw_value).strip()
            if not value:
                continue
            label = prompt_by_key.get(key, key.replace("_", " "))
            if key == "property_type": label = "نوع ملک"
            if key == "location_summary": label = "موقعیت کلی"
            if key == "requirements_summary": label = "نیازها و شرایط ضروری"
            if key == "investment_amount": label = "مبلغ سرمایه‌گذاری / ارزش پروژه"
            if key == "menu_mode": label = "نوع فرایند"
            if key == "contact" and admin_view: label = "شماره تماس (محرمانه)"
            if key == "exact_address" and admin_view: label = "نشانی دقیق (محرمانه)"
            lines.append(f"<b>{escape(str(label))}:</b> {escape(value)}")
        lines.append(f"<b>تعداد تصاویر:</b> {len(data.get('images', []))} (حداکثر ۵)")
        if data.get("videos"):
            lines.append(f"<b>تعداد ویدئوها:</b> {len(data.get('videos', []))}")
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
            body = await render_submission(data, submission["kind"], language, source_language, admin_view=True)
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
    image_ids = data.get("images", [])
    if image_ids:
        try:
            if len(image_ids) == 1:
                await context.bot.send_photo(chat_id=ADMIN_ID, photo=image_ids[0], caption=f"تصویر پرونده #{submission_id}")
            else:
                from telegram import InputMediaPhoto
                media = [InputMediaPhoto(media=file_id) for file_id in image_ids[:5]]
                await context.bot.send_media_group(chat_id=ADMIN_ID, media=media)
        except Exception:
            logger.exception("Could not send submission photos to admin")
    for video_id in data.get("videos", []):
        try:
            await context.bot.send_video(chat_id=ADMIN_ID, video=video_id, caption=f"ویدئوی پرونده #{submission_id}")
        except Exception:
            logger.exception("Could not send submission video to admin")


# ==================== CHANNEL PUBLICATION ====================

def sanitize_publication_data(raw_data):
    """Return a publication-safe copy: never expose contact identifiers or exact address."""
    data = json.loads(json.dumps(raw_data, ensure_ascii=False))
    private_keys = {
        "contact", "phone", "phone_number", "mobile", "contact_user_id",
        "telegram_user_id", "telegram_username", "username", "user_id",
        "exact_address", "address", "alley", "building_number", "unit_number",
        "plaque", "building_plaque", "private_address", "contact_info",
    }
    # Preserve only broad location fields (city/area and street-level partial location).
    for key in list(data):
        if key.lower() in private_keys:
            data.pop(key, None)

    # Strip phone numbers and Telegram handles that may have been typed into free text.
    phone_pattern = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
    handle_pattern = re.compile(r"(?<!\w)@[A-Za-z0-9_]{4,}")
    free_text_keys = {"title", "description", "details", "additional_details", "notes", "conditions", "special_conditions", "payment_terms", "usage_type"}
    def clean(value, parent_key=""):
        if isinstance(value, str):
            if parent_key.lower() in free_text_keys:
                value = phone_pattern.sub("[اطلاعات تماس حذف شد]", value)
                value = handle_pattern.sub("[شناسه تماس حذف شد]", value)
            return value
        if isinstance(value, list):
            return [clean(item, parent_key) for item in value]
        if isinstance(value, dict):
            return {key: clean(item, key) for key, item in value.items() if key.lower() not in private_keys}
        return value
    return clean(data)


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
    # Public channels receive only sanitized data; the original submission remains unchanged in DB.
    data = sanitize_publication_data(json.loads(submission["data"]))
    message_text = await render_submission(data, submission["kind"], language, submission["language"])
    if submission["kind"] == "rent_apartment_ad":
        message_text = message_text.replace("<b>شناسه آگهی:</b> ", f"<b>شناسه آگهی:</b> {submission_id} ")
    message = await context.bot.send_message(
        chat_id=channel, text=message_text, parse_mode="HTML", disable_web_page_preview=True,
    )
    image_ids = data.get("images", [])
    if image_ids:
        if len(image_ids) == 1:
            await context.bot.send_photo(chat_id=channel, photo=image_ids[0], caption="تصاویر آگهی")
        else:
            from telegram import InputMediaPhoto
            media = [InputMediaPhoto(media=file_id) for file_id in image_ids[:5]]
            await context.bot.send_media_group(chat_id=channel, media=media)
    for video_id in data.get("videos", []):
        await context.bot.send_video(chat_id=channel, video=video_id, caption=message_text[:900])
    record_publication(submission_id, language, channel, "success", message_id=message.message_id)
    return True, "منتشر شد."


async def show_publication_languages(query, context, submission_id):
    selections = context.user_data.setdefault("publication_languages", {})
    selections.setdefault(submission_id, [])
    selected = selections[submission_id]
    keyboard = []
    for language, label in LANG_NAMES.items():
        mark = "✅" if language in selected else "▫️"
        keyboard.append([InlineKeyboardButton(numbered_button(f"{mark} {label}"), callback_data=f"pubtoggle:{submission_id}:{language}")])
    keyboard.append([
        InlineKeyboardButton(numbered_button("🚀 تأیید و انتشار"), callback_data=f"pubconfirm:{submission_id}"),
        InlineKeyboardButton(numbered_button("لغو"), callback_data=f"pubcancel:{submission_id}"),
    ])
    await query.edit_message_text(
        f"🌐 زبان یا زبان‌های انتشار ثبت #{submission_id} را انتخاب کنید.\n\nاطلاعات تماس، شناسه تلگرام و نشانی دقیق از کانال حذف می‌شود. شهر، منطقه و بخش غیرحساس نشانی می‌تواند نمایش داده شود.\n\nپس از انتخاب حداقل یک زبان، دکمه «تأیید و انتشار» را بزنید.",
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
        selected = selections.setdefault(submission_id, [])
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
        languages = list(selections.get(submission_id, []))
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
async def show_user_submissions(update, user_id, only_requests=False):
    sql = "SELECT id, kind, status, created_at FROM submissions WHERE user_id=?"
    if only_requests:
        sql += " AND kind IN ('buy_req','rent_req')"
    sql += " ORDER BY id DESC LIMIT 20"
    with connect_db() as conn:
        rows = conn.execute(sql, (user_id,)).fetchall()
    saved_user = get_user(user_id)
    language = saved_user["language"] if saved_user else "fa"
    if not rows:
        await update.message.reply_text(await localized("هنوز موردی ثبت نکرده‌اید.", language), reply_markup=main_keyboard(language))
        return
    heading = await localized("📋 ثبت‌های شما:", language)
    lines = [heading + "\n"]
    status_labels = {"pending": "در انتظار بررسی", "approved": "تأیید شده", "rejected": "رد شده", "published": "منتشر شده"}
    for row in rows:
        kind_label = KINDS.get(row["kind"], {}).get(language, KINDS.get(row["kind"], {}).get("fa", row["kind"]))
        status_label = await localized(status_labels.get(row["status"], row["status"]), language)
        lines.append(f"#{row['id']} — {kind_label} — {status_label}")
    await update.message.reply_text("\n".join(lines), reply_markup=main_keyboard(language))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user = update.effective_user
    if not user:
        return

    if not update.message.text:
        if context.user_data.get("form", {}).get("mode") == "complete":
            if await process_standard_form(update, context): return
        return

    text = _strip_button_number(update.message.text.strip())

    # The language-change control must work from the main menu, every submenu,
    # and every step of an active form.
    if text in LANGUAGE_CHANGE_BUTTONS or normalize_button_text(text.replace("🌐 ", "")) in {normalize_button_text(v.replace("🌐 ", "")) for v in LANGUAGE_BUTTONS.values()}:
        await update.message.reply_text(language_prompt(), reply_markup=language_keyboard())
        return

    # Handle language selection before any active form can consume the text.
    # This prevents a stale office-rent form from intercepting language buttons.
    language = parse_language(text)
    if language:
        await choose_language(update, context, language)
        return

    # Complete unified forms are handled after language selection below.

    saved_user = get_user(user.id)
    if not saved_user:
        await update.message.reply_text(language_prompt(), reply_markup=language_keyboard())
        return
    user_language = saved_user["language"]

    if context.user_data.get("form", {}).get("mode") == "complete":
        if await process_standard_form(update, context):
            return

    if text in BACK_BUTTONS:
        context.user_data.pop("form", None)
        context.user_data.pop("rent_menu", None)
        context.user_data.pop("rent_property_menu", None)
        context.user_data.pop("awaiting_support", None)
        await update.message.reply_text(await localized("به منوی اصلی بازگشتید.", user_language), reply_markup=main_keyboard(user_language))
        return

    if text in LANGUAGE_CHANGE_BUTTONS:
        context.user_data.pop("form", None)
        context.user_data.pop("awaiting_support", None)
        context.user_data.pop("rent_menu", None)
        await update.message.reply_text(language_prompt(), reply_markup=language_keyboard())
        return

    if text in SUPPORT_BUTTONS:
        context.user_data.pop("form", None)
        context.user_data["awaiting_support"] = True
        await update.message.reply_text(await localized("پیام خود را برای پشتیبانی ارسال کنید:", user_language), reply_markup=main_keyboard(user_language))
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
        category = RENT_CATEGORY_MAP.get(normalize_button_text(text))
        if not category:
            await update.message.reply_text(
                RENT_CATEGORY_PROMPTS.get(user_language, RENT_CATEGORY_PROMPTS["fa"]),
                reply_markup=submenu_keyboard(rent_category_options(user_language)),
            )
            return
        context.user_data.pop("rent_menu", None)
        if category == "اداری":
            await begin_office_rent_form(update, context, user_language)
        elif category == "مسکونی":
            context.user_data["rent_property_menu"] = True
            labels = {
                "fa": ["🏢 آپارتمان", "🏡 ویلا", "🏠 خانه مستقل"],
                "en": ["🏢 Apartment", "🏡 Villa", "🏠 Detached house"],
                "az": ["🏢 Mənzil", "🏡 Villa", "🏠 Müstəqil ev"],
                "tr": ["🏢 Daire", "🏡 Villa", "🏠 Müstakil ev"],
                "ar": ["🏢 شقة", "🏡 فيلا", "🏠 منزل مستقل"],
                "zh": ["🏢 公寓", "🏡 别墅", "🏠 独立住宅"],
                "ru": ["🏢 Квартира", "🏡 Вилла", "🏠 Отдельный дом"],
            }.get(user_language, ["🏢 آپارتمان", "🏡 ویلا", "🏠 خانه مستقل"])
            await update.message.reply_text(await localized("نوع ملک مسکونی را انتخاب کنید:", user_language), reply_markup=submenu_keyboard(labels, language=user_language))
        else:
            await update.message.reply_text(await localized("فرم این دسته هنوز آماده نیست.", user_language), reply_markup=main_keyboard(user_language))
        return

    if context.user_data.get("rent_property_menu"):
        normalized = normalize_button_text(text)
        if normalized in {normalize_button_text(await localized(x, user_language)) for x in ("🏢 آپارتمان", "🏢 Apartment", "🏢 Mənzil", "🏢 Daire", "🏢 شقة", "🏢 公寓", "🏢 Квартира")} or any(word in normalized.casefold() for word in ("apartment", "mənzil", "daire", "شقة", "公寓", "квартира", "آپارتمان")):
            context.user_data.pop("rent_property_menu", None)
            await begin_apartment_rent_form(update, context, user_language)
        else:
            context.user_data.pop("rent_property_menu", None)
            await update.message.reply_text(await localized("فرم اختصاصی ویلا و خانه مستقل هنوز آماده نیست. برای ادامه، گزینه آپارتمان را انتخاب کنید.", user_language), reply_markup=submenu_keyboard(["🏢 آپارتمان", "🏡 ویلا", "🏠 خانه مستقل"], language=user_language))
            context.user_data["rent_property_menu"] = True
        return

    # New complete menu navigation: each selected category opens the relevant form.
    action = None
    for canonical, menu_action in MAIN_ACTIONS.items():
        shown = await localized(canonical, user_language)
        if normalize_button_text(text) == normalize_button_text(shown) or normalize_button_text(text) == normalize_button_text(canonical):
            action = menu_action
            break
    if action:
        if action == "support":
            context.user_data["awaiting_support"] = True
            await update.message.reply_text(await localized("پیام خود را برای پشتیبانی ارسال کنید:", user_language), reply_markup=main_keyboard(user_language))
            return
        context.user_data["menu_mode"] = action
        options = SUBMENUS.get(action, [])
        translated_options = [await localized(option, user_language) for option in options]
        prompt = "نوع ملک یا موضوع موردنظر را انتخاب کنید:"
        await update.message.reply_text(await localized(prompt, user_language), reply_markup=submenu_keyboard(translated_options, language=user_language))
        return

    menu_mode = context.user_data.get("menu_mode")
    if menu_mode:
        options = SUBMENUS.get(menu_mode, [])
        selected = None
        for option in options:
            shown = await localized(option, user_language)
            if normalize_button_text(text) in {normalize_button_text(shown), normalize_button_text(option)}:
                selected = option
                break
        if selected:
            context.user_data.pop("menu_mode", None)
            kind = KIND_FOR_MENU.get(menu_mode, "builder")
            selected_norm = normalize_button_text(selected)
            effective_mode = menu_mode
            if menu_mode == "construction":
                if "مالک" in selected:
                    effective_mode = "construction_owner"
                elif "سازنده" in selected:
                    effective_mode = "construction_builder"
                elif "شریک" in selected or "نیمه" in selected or "پروژه" in selected:
                    effective_mode = "construction_partner"
                else:
                    effective_mode = "construction_partner"
            elif menu_mode == "presale":
                effective_mode = "presale"
            await begin_form(update, context, kind, user_language, category=selected, menu_mode=effective_mode)
            return
        await update.message.reply_text(await localized("لطفاً یکی از گزینه‌های همین فهرست را انتخاب کنید یا به منوی اصلی برگردید.", user_language), reply_markup=submenu_keyboard([await localized(x, user_language) for x in options], language=user_language))
        return

    kind = detect_kind(text)
    if kind:
        await begin_form(update, context, kind, user_language)
        return

    if await process_standard_form(update, context):
        return

    await update.message.reply_text(await localized("لطفاً از گزینه‌های منو استفاده کنید.", user_language), reply_markup=main_keyboard(user_language))


async def process_standard_form(update, context):
    form = context.user_data.get("form")
    if not form or form.get("mode") != "complete" or not update.message:
        return False
    language = form["language"]
    text = _strip_button_number((update.message.text or "").strip())
    if update.message.contact:
        contact = update.message.contact
        # Accept only the Telegram contact belonging to the current user.
        if not update.effective_user or not contact.user_id or contact.user_id != update.effective_user.id:
            button = KeyboardButton("📱 اشتراک‌گذاری شماره تماس", request_contact=True)
            await update.message.reply_text(
                "لطفاً فقط با دکمهٔ اشتراک‌گذاری شماره تماسِ حساب تلگرام خودتان را ارسال کنید.",
                reply_markup=ReplyKeyboardMarkup([[button], ["❌ لغو ثبت"]], resize_keyboard=True, is_persistent=True),
            )
            return True
        fields = form.get("fields", [])
        idx = form.get("step", 0)
        if idx >= len(fields) or fields[idx][0] != "contact":
            # Do not let an unexpected contact message corrupt another form step.
            return True
        form["data"]["contact"] = contact.phone_number
        form["data"]["contact_user_id"] = contact.user_id
        form["step"] += 1
        form["awaiting_contact"] = False
        await update.message.reply_text("شماره تماس تلگرام شما ثبت شد.")
        # Continue the actual form instead of jumping to the final-submit screen.
        await ask_complete_form_step(update.message, context)
        return True
    if update.message.photo and form.get("awaiting_images"):
        if len(form["images"]) >= 5:
            await update.message.reply_text("حداکثر ۵ تصویر قابل ثبت است. برای ادامه دکمه «📷 پایان تصاویر» را بزنید.")
            return True
        form["images"].append(update.message.photo[-1].file_id)
        await update.message.reply_text(f"تصویر {len(form['images'])} از ۵ ثبت شد.", reply_markup=form_keyboard([["📷 پایان تصاویر"], ["❌ لغو ثبت"]], language))
        return True
    if update.message.video and form.get("awaiting_video"):
        form.setdefault("videos", []).append(update.message.video.file_id)
        form["data"]["videos"] = form["videos"]
        await update.message.reply_text(f"ویدئو ثبت شد ({len(form['videos'])}). برای پایان، دکمه «🎬 پایان ویدئوها» را بزنید.", reply_markup=form_keyboard([["🎬 پایان ویدئوها"], ["❌ لغو ثبت"]], language))
        return True
    if not update.message.text:
        return False
    if normalize_button_text(text) in {normalize_button_text("❌ لغو ثبت"), normalize_button_text(await localized("❌ لغو ثبت", language))}:
        context.user_data.pop("form", None)
        await update.message.reply_text("ثبت لغو شد.", reply_markup=main_keyboard(language))
        return True
    previous_labels = {normalize_button_text(x) for x in PREV_STEP_LABELS.values()}
    previous_labels.add(normalize_button_text(await localized(PREV_STEP_LABELS.get(language, PREV_STEP_LABELS["fa"]), language)))
    if normalize_button_text(text) in previous_labels:
        if form["step"] > 0:
            form["step"] -= 1
            form["awaiting_images"] = False
            form["awaiting_video"] = False
            await ask_complete_form_step(update.message, context)
        else:
            await update.message.reply_text(await localized("در اولین مرحله هستید.", language), reply_markup=main_keyboard(language))
        return True
    if normalize_button_text(text) == normalize_button_text("📷 پایان تصاویر"):
        if not form.get("images"):
            await update.message.reply_text("برای آگهی حداقل یک تصویر الزامی است.")
            return True
        form["data"]["images"] = form["images"][:5]
        form["awaiting_images"] = False
        form["step"] += 1
        await ask_complete_form_step(update.message, context)
        return True
    if normalize_button_text(text) == normalize_button_text("🎬 پایان ویدئوها"):
        form["data"]["videos"] = form.get("videos", [])
        form["awaiting_video"] = False
        form["step"] += 1
        await ask_complete_form_step(update.message, context)
        return True
    if normalize_button_text(text) == normalize_button_text("✅ پایان و ارسال به ناظر"):
        return await submit_complete_form(update, context)
    fields = form["fields"]
    idx = form["step"]
    if idx >= len(fields):
        await update.message.reply_text("برای ارسال نهایی دکمه «پایان و ارسال به ناظر» را بزنید.", reply_markup=form_keyboard([["✅ پایان و ارسال به ناظر"]], language))
        return True
    key, prompt = fields[idx]
    if form.get("_awaiting_exact_area"):
        exact_key = form.pop("_awaiting_exact_area")
        normalized_area = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")).replace(",", "").replace("٬", "").replace(" ", "")
        if not normalized_area.isdigit():
            form["_awaiting_exact_area"] = exact_key
            await update.message.reply_text(await localized("متراژ دقیق باید فقط عدد باشد.", language))
            return True
        form["data"][exact_key] = normalized_area
        form["step"] += 1
        await ask_complete_form_step(update.message, context)
        return True
    choices = _field_choice_options(key, prompt, form.get("data", {}).get("rooms"))
    if choices:
        matched = None
        for option in choices:
            shown = normalize_button_text(await localized(option, language))
            if normalize_button_text(text) in {shown, normalize_button_text(option)}:
                matched = option
                break
        if matched is None:
            if "امکانات" in prompt or "amenit" in key.lower():
                amenity_rows = []
                shown_choices = [await localized(x, language) for x in choices if x != "پایان انتخاب امکانات"]
                amenity_rows.extend([shown_choices[i:i+3] for i in range(0, len(shown_choices), 3)])
                amenity_rows.append([await localized("پایان انتخاب امکانات", language)])
                amenity_rows.append([await localized(PREV_STEP_LABELS.get(language, PREV_STEP_LABELS["fa"]), language)])
                amenity_rows.append(["❌ لغو ثبت"])
            else:
                amenity_rows = [[await localized(x, language) for x in choices[i:i+3]] for i in range(0, len(choices), 3)]
                amenity_rows.extend([[await localized(PREV_STEP_LABELS.get(language, PREV_STEP_LABELS["fa"]), language)], ["❌ لغو ثبت"]])
            await update.message.reply_text(await localized("لطفاً یکی از گزینه‌های دکمه‌ای را انتخاب کنید.", language), reply_markup=form_keyboard(amenity_rows, language))
            return True
        if matched == "ورود دقیق متراژ":
            form["_awaiting_exact_area"] = key
            await update.message.reply_text(await localized("متراژ دقیق را فقط با عدد وارد کنید.", language), reply_markup=form_keyboard([[await localized(PREV_STEP_LABELS.get(language, PREV_STEP_LABELS["fa"]), language)], ["❌ لغو ثبت"]], language))
            return True
        if key == "images_choice":
            if matched == "بله":
                form["data"]["images_submitted"] = "yes"
                form["images"] = []
                form["step"] += 1
            else:
                form["data"]["images_submitted"] = "no"
                form["data"]["images"] = []
                # Skip the following images field entirely.
                form["step"] += 2
            await ask_complete_form_step(update.message, context)
            return True
        if matched == "پایان انتخاب امکانات":
            form["data"][key] = form.get("_amenity_selections", [])
            # If parking was not selected as an amenity, skip its count question.
            if key == "amenities" and form["step"] + 1 < len(form["fields"]):
                next_key, _ = form["fields"][form["step"] + 1]
                if next_key == "parking" and not any("پارکینگ" in str(x).lower() for x in form.get("_amenity_selections", [])):
                    form["data"]["parking"] = "ندارد"
                    form["step"] += 2
                else:
                    form["step"] += 1
            else:
                form["step"] += 1
            await ask_complete_form_step(update.message, context)
            return True
        elif "امکانات" in prompt or "amenit" in key.lower():
            selected = form.setdefault("_amenity_selections", [])
            if matched not in selected:
                selected.append(matched)
            # Keep the complete amenities menu visible after every selection.
            # Do not truncate it to the first three options; the user may select
            # several amenities before explicitly finishing.
            amenity_rows = []
            shown_choices = [await localized(x, language) for x in choices if x != "پایان انتخاب امکانات"]
            amenity_rows.extend([shown_choices[i:i+3] for i in range(0, len(shown_choices), 3)])
            amenity_rows.append([await localized("پایان انتخاب امکانات", language)])
            amenity_rows.append([await localized(PREV_STEP_LABELS.get(language, PREV_STEP_LABELS["fa"]), language)])
            amenity_rows.append(["❌ لغو ثبت"])
            await update.message.reply_text(await localized("امکانات دیگری انتخاب کنید یا «پایان انتخاب امکانات» را بزنید.", language), reply_markup=form_keyboard(amenity_rows, language))
            return True
        else:
            form["data"][key] = matched
        form["step"] += 1
        await ask_complete_form_step(update.message, context)
        return True
    if key in NUMERIC_ONLY_KEYS or key.endswith("_area") or key.endswith("_land_area"):
        normalized = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")).replace(",", "").replace("٬", "").replace(" ", "")
        if not normalized.isdigit():
            await update.message.reply_text(await localized("فقط عدد وارد کنید؛ حروف و واحد پول ننویسید.", language))
            return True
        form["data"][key] = normalized
        form["step"] += 1
        await ask_complete_form_step(update.message, context)
        return True
    if key == "images":
        await update.message.reply_text("لطفاً تصاویر ملک را ارسال کنید؛ حداقل یک و حداکثر ۵ تصویر. سپس «📷 پایان تصاویر» را بزنید.")
        return True
    if key == "contact":
        button = KeyboardButton("📱 اشتراک‌گذاری شماره تماس", request_contact=True)
        await update.message.reply_text(
            "شماره تماس باید با دکمهٔ اشتراک‌گذاری شماره تلگرام ارسال شود؛ واردکردن دستی پذیرفته نیست.",
            reply_markup=ReplyKeyboardMarkup([[button], ["❌ لغو ثبت"]], resize_keyboard=True, is_persistent=True),
        )
        return True
    if key == "video_note":
        if text.casefold() in {"ندارد", "no", "none", "нет", "لا يوجد", "没有"}:
            form["data"]["videos"] = []
        else:
            form["data"]["video_link"] = text
        form["awaiting_video"] = False
        form["step"] += 1
        await ask_complete_form_step(update.message, context)
        return True
    if key == "unit_count_to_add":
        normalized_count = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        if not normalized_count.isdigit() or not (1 <= int(normalized_count) <= 100):
            await update.message.reply_text("لطفاً تعداد واحدها را به‌صورت عددی بین ۱ تا ۱۰۰ وارد کنید.")
            return True
        count = int(normalized_count)
        form["data"][key] = count
        unit_fields = [
            ("area", "متراژ واحد به مترمربع"), ("floor", "طبقه واحد"),
            ("parking", "تعداد پارکینگ"), ("bedrooms", "تعداد اتاق خواب"),
            ("storage", "تعداد انباری"), ("balcony", "تعداد بالکن"),
            ("construction_stage", "مرحله فعلی ساخت"), ("progress_percent", "درصد پیشرفت پروژه"),
            ("handover_date", "زمان تحویل"), ("total_price", "قیمت کل واحد به تومان"),
            ("price_per_meter", "قیمت هر مترمربع به تومان"), ("payment_terms", "شرایط و مراحل پرداخت"),
            ("installments", "امکان پرداخت اقساطی و شرایط آن"), ("amenities", "امتیازات و امکانات پروژه"),
        ]
        repeated = []
        for unit_no in range(1, count + 1):
            for unit_key, unit_prompt in unit_fields:
                repeated.append((f"unit_{unit_no}_{unit_key}", f"🏢 واحد {unit_no} — {unit_prompt}"))
        insert_at = form["step"] + 1
        form["fields"][insert_at:insert_at] = repeated
        form["step"] += 1
        await ask_complete_form_step(update.message, context)
        return True
    form["data"][key] = text
    form["step"] += 1
    await ask_complete_form_step(update.message, context)
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
