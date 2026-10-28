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
    "fa": [["🏠 خرید ملک", "🔑 اجاره ملک"], ["📝 درخواست خرید", "📨 درخواست اجاره"], ["💼 سرمایه‌گذاری ملکی", "🏗 مشارکت در ساخت"], ["⭐ علاقه‌مندی‌ها", "📋 آگهی‌ها و درخواست‌های من"], ["🆘 پشتیبانی"]],
    "en": [["🏠 Buy Property", "🔑 Rent Property"], ["📝 Buy Request", "📨 Rental Request"], ["💼 Property Investment", "🏗 Joint Construction"], ["⭐ Favorites", "📋 My Listings & Requests"], ["🆘 Support"]],
    "az": [["🏠 Əmlak al", "🔑 Əmlak kirayələ"], ["📝 Alış sorğusu", "📨 İcarə sorğusu"], ["💼 Əmlaka investisiya", "🏗 Birgə tikinti"], ["⭐ Seçilmişlər", "📋 Elanlarım və sorğularım"], ["🆘 Dəstək"]],
    "tr": [["🏠 Gayrimenkul satın al", "🔑 Gayrimenkul kirala"], ["📝 Satın alma talebi", "📨 Kiralama talebi"], ["💼 Gayrimenkul yatırımı", "🏗 Kat karşılığı inşaat"], ["⭐ Favoriler", "📋 İlanlarım ve taleplerim"], ["🆘 Destek"]],
    "ar": [["🏠 شراء عقار", "🔑 استئجار عقار"], ["📝 طلب شراء", "📨 طلب إيجار"], ["💼 الاستثمار العقاري", "🏗 شراكة بناء"], ["⭐ المفضلة", "📋 إعلاناتي وطلباتي"], ["🆘 الدعم"]],
    "zh": [["🏠 购买房产", "🔑 租赁房产"], ["📝 求购需求", "📨 求租需求"], ["💼 房地产投资", "🏗 合作建设"], ["⭐ 收藏", "📋 我的房源与需求"], ["🆘 客服"]],
    "ru": [["🏠 Купить недвижимость", "🔑 Арендовать недвижимость"], ["📝 Запрос на покупку", "📨 Запрос на аренду"], ["💼 Инвестиции в недвижимость", "🏗 Совместное строительство"], ["⭐ Избранное", "📋 Мои объявления и запросы"], ["🆘 Поддержка"]],
}

# Полный каталог категорий. Кнопки переводятся на язык пользователя при показе.
SUBMENUS = {
    "buy": ["🏢 آپارتمان مسکونی", "🏡 ویلا و خانه مستقل", "🌳 زمین و باغ", "🏬 مغازه و ملک تجاری", "🏢 دفتر کار و ملک اداری", "🏭 ملک صنعتی، کارخانه و کارگاه", "🏗 سوله و انبار", "🏚 ملک کلنگی", "🏗 پیش‌خرید و پروژه در حال ساخت", "💎 املاک لوکس و گران‌قیمت", "📈 ملک مناسب سرمایه‌گذاری", "🏙 مستغلات و مجتمع تجاری", "📦 مشاهده همه آگهی‌های خرید"],
    "rent": ["🏢 آپارتمان مسکونی", "🏡 ویلا و خانه مستقل", "🏬 مغازه و ملک تجاری", "🏢 دفتر کار و ملک اداری", "🏭 ملک صنعتی، کارخانه و کارگاه", "🏗 سوله و انبار", "💎 املاک لوکس"],
    "buy_req": ["🏢 آپارتمان مسکونی", "🏡 ویلا و خانه مستقل", "🌳 زمین و باغ", "🏬 مغازه و ملک تجاری", "🏢 دفتر کار و ملک اداری", "🏭 ملک صنعتی، کارخانه و کارگاه", "🏗 سوله و انبار", "🏚 ملک کلنگی", "🏗 پیش‌خرید و پروژه در حال ساخت", "💎 ملک لوکس و گران‌قیمت"],
    "rent_req": ["🏢 آپارتمان مسکونی", "🏡 ویلا و خانه مستقل", "🏬 مغازه و ملک تجاری", "🏢 دفتر کار و ملک اداری", "🏭 ملک صنعتی، کارخانه و کارگاه", "🏗 سوله و انبار", "💎 ملک لوکس"],
    "investment": ["🏠 خرید ملک برای اجاره‌دادن", "📈 خرید برای افزایش قیمت و فروش", "🏬 سرمایه‌گذاری در املاک تجاری", "💎 املاک لوکس و خاص", "🏗 پروژه‌های ساختمانی و در حال ساخت", "🏙 پروژه‌ها و سرمایه‌گذاری‌های بزرگ", "🤝 جذب شریک یا سرمایه‌گذار برای پروژه", "🌳 سرمایه‌گذاری در زمین و باغ"],
    "construction": ["🧑‍💼 مالک زمین/ملک دنبال سازنده", "🏗 سازنده دنبال زمین/ملک", "💰 سرمایه‌گذار دنبال پروژه مشارکتی", "🤝 دنبال شریک برای پروژه ساختمانی", "📋 معرفی پروژه‌های آماده مشارکت", "🧭 مشاوره و ارزیابی شرایط مشارکت", "🏙 پروژه‌های بزرگ و چندواحدی"],
    "favorites": ["⭐ مشاهده آگهی‌های ذخیره‌شده", "🔔 آگهی‌های جدید مشابه موارد ذخیره‌شده", "⚖️ مقایسه ملک‌های ذخیره‌شده", "🗑 حذف آگهی از ذخیره‌شده‌ها", "💲 پیگیری تغییر قیمت"],
}

MAIN_ACTIONS = {
    "🏠 خرید ملک":"buy", "🔑 اجاره ملک":"rent", "📝 درخواست خرید":"buy_req", "📨 درخواست اجاره":"rent_req",
    "💼 سرمایه‌گذاری ملکی":"investment", "🏗 مشارکت در ساخت":"construction", "⭐ علاقه‌مندی‌ها":"favorites",
    "📋 آگهی‌ها و درخواست‌های من":"my_items", "🆘 پشتیبانی":"support",
}
KIND_FOR_MENU = {"buy":"sell_ad", "rent":"rent_ad", "buy_req":"buy_req", "rent_req":"rent_req", "investment":"builder", "construction":"builder"}

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


def normalize_button_text(value):
    """Remove leading menu emoji so labels remain compatible with existing flows."""
    value = (value or "").strip()
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
    return ReplyKeyboardMarkup(LANGUAGE_KEYBOARD, resize_keyboard=True, one_time_keyboard=True, is_persistent=True)


def main_keyboard(language):
    rows = with_language_button(MENU.get(language, MENU["fa"]), language)
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


BACK_LABELS = {
    "fa": "⬅️ بازگشت به منوی اصلی", "en": "⬅️ Back to Main Menu",
    "az": "⬅️ Əsas menyuya qayıt", "tr": "⬅️ Ana menüye dön",
    "ar": "⬅️ العودة إلى القائمة الرئيسية", "zh": "⬅️ 返回主菜单", "ru": "⬅️ Вернуться в главное меню",
}

def submenu_keyboard(options, back_label=None, language="fa"):
    rows = [[option] for option in options]
    rows.append([back_label or BACK_LABELS.get(language, BACK_LABELS["fa"])])
    rows = with_language_button(rows, language)
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def form_keyboard(rows, language="fa"):
    return ReplyKeyboardMarkup(with_language_button(rows, language), resize_keyboard=True, is_persistent=True)


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

APARTMENT_STEPS = [
    ("listing_role", "ثبت‌کننده ملک هستید یا مشاور املاک / واسطه؟", ["👤 مالک", "🏢 مشاور املاک / واسطه"]),
    ("area", "متراژ آپارتمان را فقط با عدد وارد کنید:"),
    ("rooms", "تعداد اتاق خواب را وارد کنید:"),
    ("master_rooms", "تعداد اتاق مستر را وارد کنید:"),
    ("terrace", "آپارتمان تراس دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("lobby", "ساختمان لابی دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("caretaker", "ساختمان سرایدار مقیم دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("elevator", "ساختمان آسانسور دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("parking", "آپارتمان پارکینگ دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("shared_pool", "ساختمان امکانات آبی مشترک دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("roof_garden", "ساختمان روف‌گاردن دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("floor", "طبقه واحد را وارد کنید (زیرزمین با عدد منفی و همکف با ۰):"),
    ("construction_year", "سال ساخت را فقط با عدد وارد کنید:"),
    ("furnished", "وضعیت مبله بودن آپارتمان را انتخاب کنید:", ["مبله", "غیرمبله"]),
    ("pets", "وضعیت نگهداری حیوان خانگی را انتخاب کنید:", ["مجاز است", "مجاز نیست"]),
    ("total_units", "تعداد کل واحدهای ساختمان را وارد کنید:"),
    ("total_floors", "تعداد کل طبقات ساختمان را وارد کنید:"),
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

APARTMENT_NUMERIC_FIELDS = {"area", "rooms", "master_rooms", "construction_year", "total_units", "total_floors", "municipal_district", "building_number", "unit_number", "deposit", "rent"}
APARTMENT_BOOL_FIELDS = {"terrace", "lobby", "caretaker", "elevator", "parking", "shared_pool", "roof_garden"}

async def begin_apartment_rent_form(update, context, language):
    context.user_data["form"] = {"kind": "rent_apartment_ad", "language": language, "step": 0, "data": {}, "mode": "apartment_rent", "images": []}
    await ask_apartment_step(update.message, context)

async def ask_apartment_step(message, context):
    form = context.user_data.get("form")
    if not form or form.get("mode") != "apartment_rent":
        return
    key, prompt, *options = APARTMENT_STEPS[form["step"]]
    language = form["language"]
    if key == "contact":
        rows = [[KeyboardButton(await localized("📱 اشتراک‌گذاری شماره تلگرام", language), request_contact=True)], [await localized("❌ لغو ثبت", language)]]
    elif key == "images_choice":
        rows = [[await localized("بله", language), await localized("خیر", language)], [await localized("❌ لغو ثبت", language)]]
    elif options:
        rows = [[await localized(opt, language) for opt in options[0]], [await localized("❌ لغو ثبت", language)]]
    else:
        rows = [[await localized("❌ لغو ثبت", language)]]
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
    text = (message.text or "").strip()
    cancel = normalize_button_text(await localized("❌ لغو ثبت", language))
    if normalize_button_text(text) in {normalize_button_text(x) for x in CANCEL_FORM_BUTTONS} | {cancel}:
        context.user_data.pop("form", None)
        await message.reply_text(await localized("ثبت آگهی لغو شد.", language), reply_markup=main_keyboard(language))
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
        if key == "parking" and matched.startswith("❌"):
            form["data"]["parking_spaces"] = "0"
        elif key == "parking" and matched.startswith("✅"):
            form["dynamic_parking_count"] = True
            await message.reply_text(await localized("تعداد جای پارک را فقط با عدد وارد کنید:", language), reply_markup=form_keyboard([[await localized("❌ لغو ثبت", language)]], language))
            return True
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
    ("parking", "تعداد پارکینگ را فقط با عدد وارد کنید:"),
    ("rooms", "تعداد اتاق را فقط با عدد وارد کنید:"),
    ("elevator", "آسانسور دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("lobby", "لابی دارد؟", ["✅ دارد", "❌ ندارد"]),
    ("city", "شهر را فقط با حروف وارد کنید:"),
    ("municipal_district", "منطقه شهرداری را فقط با عدد وارد کنید:"),
    ("street", "نام خیابان را فقط با حروف وارد کنید:"),
    ("alley", "نام کوچه یا خیابان فرعی را وارد کنید (عدد و حروف مجاز است):"),
    ("plaque", "شماره پلاک را فقط با عدد وارد کنید:"),
    ("deposit", "مبلغ رهن را فقط با عدد وارد کنید:"),
    ("rent", "مبلغ اجاره ماهانه را فقط با عدد وارد کنید:"),
    ("images", "حداقل ۴ تصویر ملک را ارسال کنید. پس از ارسال ۴ تصویر یا بیشتر، عبارت «📷 پایان تصاویر» را بفرستید."),
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
        localized_options = [await localized(option, form["language"]) for option in options[0]]
        keyboard = submenu_keyboard(localized_options, await localized("❌ لغو ثبت", form["language"]), form["language"])
    else:
        keyboard = form_keyboard([[await localized("❌ لغو ثبت", form["language"])]], form["language"])
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
    text = (message.text or "").strip()
    language = form["language"]

    cancel_labels = {normalize_button_text(x) for x in CANCEL_FORM_BUTTONS}
    cancel_labels.add(normalize_button_text(await localized("❌ لغو ثبت", language)))
    if normalize_button_text(text) in cancel_labels:
        context.user_data.pop("form", None)
        await message.reply_text(await localized("ثبت آگهی لغو شد.", language), reply_markup=main_keyboard(language))
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

    if key in {"office_document_type", "office_property_type", "elevator", "lobby"}:
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
    elif key in {"area", "parking", "rooms", "municipal_district", "plaque", "deposit", "rent"}:
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
    ("exact_address", "نشانی دقیق ملک (فقط برای مدیریت؛ در آگهی عمومی نمایش داده نمی‌شود)"),
    ("map_location", "موقعیت ملک روی نقشه یا مختصات/لینک نقشه"),
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
    # Each item is (stable key, Persian prompt). Existing languages/channels remain unchanged.
    is_listing = menu_mode in {"buy", "rent", "investment", "construction"}
    fields = []
    if menu_mode in {"buy", "rent"}:
        fields.extend(COMMON_LISTING_FIELDS)
        fields.append(("property_usage", "نوع کاربری ملک"))
        if category in ROOM_TYPES: fields.append(("rooms", "تعداد اتاق/خواب"))
        if category in BATHROOM_TYPES: fields.append(("bathrooms", "تعداد سرویس‌های بهداشتی"))
        if category in PARKING_TYPES: fields.append(("parking", "تعداد جای پارک یا ظرفیت پارکینگ"))
        if category in {"🏚 ملک کلنگی", "🌳 زمین و باغ", "🏭 ملک صنعتی، کارخانه و کارگاه", "🏗 سوله و انبار", "🏙 مستغلات و مجتمع تجاری", "🏡 ویلا و خانه مستقل"}:
            fields.extend([("land_area", "مساحت زمین"), ("building_area", "مساحت زیربنا")])
        if menu_mode == "buy" and category in TITLE_TYPES:
            fields.extend([("document_status", "وضعیت سند و مالکیت"), ("ownership_status", "وضعیت مالکیت")])
        if category == "🏡 ویلا و خانه مستقل": fields.extend([(f"villa_{i}", x) for i, x in enumerate(VILLA_FIELDS)])
        elif category == "🌳 زمین و باغ": fields.extend([(f"land_{i}", x) for i, x in enumerate(LAND_FIELDS)])
        elif category == "🏚 ملک کلنگی": fields.extend([(f"old_{i}", x) for i, x in enumerate(OLD_BUILDING_FIELDS)])
        elif category in {"🏭 ملک صنعتی، کارخانه و کارگاه", "🏗 سوله و انبار"}: fields.extend([(f"industrial_{i}", x) for i, x in enumerate(INDUSTRIAL_FIELDS)])
        elif category in {"🏢 دفتر کار و ملک اداری", "🏬 مغازه و ملک تجاری", "🏙 مستغلات و مجتمع تجاری"}:
            fields.extend([(f"office_{i}", x) for i, x in enumerate(OFFICE_AMENITIES)])
        elif category == "🏢 آپارتمان مسکونی": fields.extend([(f"amenity_{i}", x) for i, x in enumerate(RESIDENTIAL_AMENITIES)])
    elif menu_mode == "buy_req":
        fields = [("property_type", "نوع ملک موردنیاز"), ("province", "استان"), ("city", "شهر"), ("district", "مناطق موردنظر"), ("budget_min", "حداقل بودجه"), ("budget_max", "حداکثر بودجه"), ("area_min", "حداقل متراژ"), ("area_max", "حداکثر متراژ"), ("essential_amenities", "امکانات ضروری ملک"), ("transaction_timing", "زمان موردنظر برای معامله"), ("specific_conditions", "توضیحات و شرایط اختصاصی"), ("urgency", "میزان فوریت درخواست"), ("payment_terms", "شرایط پرداخت"), ("nearby_areas", "امکان دریافت پیشنهاد از مناطق نزدیک؟ (بله/خیر)")] + [(f"buyreq_{i}", x) for i, x in enumerate(BUY_REQUEST_FIELDS)]
    elif menu_mode == "rent_req":
        fields = [("property_type", "نوع ملک موردنیاز"), ("province", "استان"), ("city", "شهر"), ("district", "مناطق موردنظر"), ("budget_min", "حداقل بودجه"), ("budget_max", "حداکثر بودجه"), ("area_min", "حداقل متراژ"), ("area_max", "حداکثر متراژ"), ("essential_amenities", "امکانات ضروری ملک"), ("transaction_timing", "زمان موردنظر برای معامله"), ("specific_conditions", "توضیحات و شرایط اختصاصی"), ("urgency", "میزان فوریت درخواست"), ("payment_terms", "شرایط پرداخت"), ("nearby_areas", "امکان دریافت پیشنهاد از مناطق نزدیک؟ (بله/خیر)")] + [(f"rentreq_{i}", x) for i, x in enumerate(RENT_REQUEST_FIELDS)]
    elif menu_mode == "investment":
        fields = [("title", "عنوان فرصت سرمایه‌گذاری"), ("province", "استان"), ("city", "شهر و موقعیت پروژه"), ("exact_address", "نشانی دقیق محرمانه برای مدیریت"), ("description", "شرح پروژه")] + [(f"investment_{i}", x) for i, x in enumerate(INVESTMENT_FIELDS)]
    elif menu_mode == "construction":
        fields = [("title", "عنوان پروژه مشارکت"), ("province", "استان"), ("city", "شهر و منطقه"), ("exact_address", "نشانی دقیق محرمانه برای مدیریت"), ("description", "شرح پروژه")] + [(f"construction_{i}", x) for i, x in enumerate(CONSTRUCTION_FIELDS)]
    else:
        fields = [("title", "عنوان"), ("description", "توضیحات"), ("province", "استان"), ("city", "شهر و منطقه")]
    # Common request metadata and media are appended after category-specific fields.
    if is_listing:
        fields.extend([("images", "تصاویر ملک (حداکثر ۵ تصویر؛ هر تصویر را جداگانه ارسال کنید، سپس دکمه پایان تصاویر را بزنید)"), ("video_note", "ویدئو یا لینک ویدئوی ملک (در صورت نداشتن بنویسید: ندارد)")])
    fields.extend([("registrant_type", "نوع حساب ثبت‌کننده: مالک، مشاور یا آژانس"), ("contact", "شماره تماس را با دکمه اشتراک‌گذاری شماره تلگرام ارسال کنید")])
    return fields

async def begin_form(update, context, kind, language, category=None, menu_mode=None):
    context.user_data["awaiting_support"] = False
    context.user_data.pop("rent_menu", None)
    category = category or context.user_data.pop("selected_category", "")
    menu_mode = menu_mode or context.user_data.pop("selected_menu_mode", "")
    if not menu_mode:
        menu_mode = {"sell_ad":"buy", "rent_ad":"rent", "buy_req":"buy_req", "rent_req":"rent_req", "builder":"investment"}.get(kind, "buy")
    form_kind = {"buy":"sell_ad", "rent":"rent_ad", "buy_req":"buy_req", "rent_req":"rent_req", "investment":"builder", "construction":"builder"}.get(menu_mode, kind)
    fields = build_form_fields(form_kind, category, menu_mode)
    context.user_data["form"] = {"kind": form_kind, "language": language, "step": 0, "data": {"property_type": category, "menu_mode": menu_mode, "source_language": language}, "mode": "complete", "fields": fields, "field_index": 0, "images": [], "awaiting_images": False}
    await ask_complete_form_step(update.message, context)

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
        form["awaiting_images"] = True
        rows = [["📷 پایان تصاویر"], ["❌ لغو ثبت"]]
        await message.reply_text("📝 " + await localized(prompt, lang) + f"\nتعداد تصاویر ثبت‌شده: {len(form.get('images', []))}/5", reply_markup=form_keyboard(rows, lang))
        return
    if key == "video_note":
        form["awaiting_video"] = True
        await message.reply_text("ویدئوی ملک را ارسال کنید؛ اگر ویدئویی ندارید، «ندارد» را بنویسید. پس از ارسال، «پایان ویدئوها» را بزنید.", reply_markup=form_keyboard([["🎬 پایان ویدئوها"], ["❌ لغو ثبت"]], lang))
        return
    if key == "contact":
        contact_button = KeyboardButton(await localized("📱 اشتراک‌گذاری شماره تماس", lang), request_contact=True)
        rows = [[contact_button], ["❌ لغو ثبت"]]
        await message.reply_text("📝 " + await localized(prompt, lang), reply_markup=ReplyKeyboardMarkup(with_language_button(rows, lang), resize_keyboard=True, is_persistent=True))
        return
    rows = [["❌ لغو ثبت"]]
    if idx == len(fields)-1: rows.insert(0, ["✅ پایان و ارسال به ناظر"])
    await message.reply_text(f"📝 {idx+1}/{len(fields)} — " + await localized(prompt, lang), reply_markup=form_keyboard(rows, lang))

async def submit_complete_form(update, context):
    form = context.user_data.get("form")
    if not form: return False
    data = form["data"]
    images = form.get("images", [])
    if form.get("awaiting_images"):
        if not images:
            await update.message.reply_text("برای آگهی حداقل یک تصویر الزامی است.")
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
        [InlineKeyboardButton("✅ تأیید و انتخاب زبان انتشار", callback_data=f"approve:{submission_id}")],
        [InlineKeyboardButton("❌ رد", callback_data=f"reject:{submission_id}")],
    ])


async def render_submission(data, kind, language, source_language, admin_view=False):
    translated = await translate_submission_data(data, source_language, language)
    lines = [f"🏡 <b>{escape(KINDS.get(kind, KINDS['rent_ad']).get(language, KINDS.get(kind, KINDS['rent_ad'])['fa']))}</b>", ""]
    if kind == "rent_apartment_ad" and not admin_view:
        labels = {"area":"متراژ", "rooms":"تعداد اتاق خواب", "master_rooms":"تعداد اتاق مستر", "terrace":"تراس", "lobby":"لابی", "caretaker":"سرایدار مقیم", "elevator":"آسانسور", "parking":"پارکینگ", "parking_spaces":"تعداد جای پارک", "shared_pool":"امکانات آبی مشترک", "roof_garden":"روف‌گاردن", "floor":"طبقه", "construction_year":"سال ساخت", "furnished":"مبله بودن", "pets":"حیوان خانگی", "total_units":"تعداد واحدهای ساختمان", "total_floors":"تعداد طبقات ساختمان", "city":"شهر", "municipal_district":"منطقه شهرداری", "street":"خیابان اصلی", "deposit":"رهن (تومان)", "rent":"اجاره ماهانه (تومان)", "details":"توضیحات", "listing_role":"نوع ثبت‌کننده", "publication_date":"تاریخ انتشار"}
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
            "area": "متراژ", "rooms": "تعداد اتاق خواب", "master_rooms": "تعداد اتاق مستر", "terrace": "تراس", "lobby": "لابی", "caretaker": "سرایدار مقیم", "elevator": "آسانسور", "parking": "پارکینگ", "parking_spaces": "تعداد جای پارک", "shared_pool": "امکانات آبی مشترک", "roof_garden": "روف‌گاردن", "floor": "طبقه", "construction_year": "سال ساخت", "furnished": "وضعیت مبله", "pets": "حیوان خانگی", "total_units": "تعداد کل واحدها", "total_floors": "تعداد کل طبقات", "city": "شهر", "municipal_district": "منطقه شهرداری", "street": "خیابان اصلی", "alley": "کوچه (فقط مدیر اصلی)", "building_number": "پلاک (فقط مدیر اصلی)", "unit_number": "شماره واحد (فقط مدیر اصلی)", "deposit": "مبلغ رهن (تومان)", "rent": "اجاره ماهانه (تومان)", "details": "توضیحات", "contact": "شماره تماس (فقط مدیر اصلی)", "telegram_user_id": "شناسه تلگرام (فقط مدیر اصلی)", "telegram_username": "نام کاربری تلگرام (فقط مدیر اصلی)", "possible_duplicate_of": "احتمال تکراری بودن با آگهی", "publication_date": "تاریخ ثبت"
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
        keyboard.append([InlineKeyboardButton(f"{mark} {label}", callback_data=f"pubtoggle:{submission_id}:{language}")])
    keyboard.append([
        InlineKeyboardButton("🚀 تأیید و انتشار", callback_data=f"pubconfirm:{submission_id}"),
        InlineKeyboardButton("لغو", callback_data=f"pubcancel:{submission_id}"),
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

    text = update.message.text.strip()

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
        if action == "my_items":
            await show_user_submissions(update, user.id)
            return
        if action == "support":
            context.user_data["awaiting_support"] = True
            await update.message.reply_text(await localized("پیام خود را برای پشتیبانی ارسال کنید:", user_language), reply_markup=main_keyboard(user_language))
            return
        if action == "favorites":
            context.user_data["menu_mode"] = "favorites"
        else:
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
            if menu_mode == "favorites":
                await update.message.reply_text(await localized("امکانات ذخیره‌سازی هنوز در این نسخه فعال نیستند.", user_language), reply_markup=main_keyboard(user_language))
                return
            if menu_mode == "favorites":
                await update.message.reply_text(await localized("بخش علاقه‌مندی‌ها در حال آماده‌سازی است.", user_language), reply_markup=main_keyboard(user_language))
                return
            kind = KIND_FOR_MENU.get(menu_mode, "builder")
            await begin_form(update, context, kind, user_language, category=selected, menu_mode=menu_mode)
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
    text = (update.message.text or "").strip()
    if update.message.contact:
        contact = update.message.contact
        if not update.effective_user or not contact.user_id or contact.user_id != update.effective_user.id:
            await update.message.reply_text("لطفاً شماره تماس متعلق به حساب تلگرام خودتان را با دکمه اشتراک‌گذاری ارسال کنید.")
            return True
        form["data"]["contact"] = contact.phone_number
        form["data"]["contact_user_id"] = contact.user_id
        form["step"] += 1
        await update.message.reply_text("شماره تماس ثبت شد. برای ارسال نهایی، دکمه «پایان و ارسال به ناظر» را بزنید.", reply_markup=form_keyboard([["✅ پایان و ارسال به ناظر"], ["❌ لغو ثبت"]], language))
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
    if key == "images":
        await update.message.reply_text("لطفاً تصاویر ملک را ارسال کنید؛ حداقل یک و حداکثر ۵ تصویر. سپس «📷 پایان تصاویر» را بزنید.")
        return True
    if key == "contact":
        await update.message.reply_text("شماره تماس باید با دکمه اشتراک‌گذاری شماره تلگرام ارسال شود؛ واردکردن دستی پذیرفته نیست.")
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
