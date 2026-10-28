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

EMOJI_PREFIXES = ("🏢 ", "🏠 ", "🏭 ", "🏬 ", "📄 ", "📍 ", "🏛 ", "🔀 ", "✅ ", "❌ ", "📷 ", "📱 ", "⬅️ ", "🆘 ", "🌐 ")


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
    """Add a language-change control in the currently selected language."""
    result = [list(row) for row in rows]
    aliases = {normalize_button_text(label) for label in LANGUAGE_BUTTONS.values()}
    for row in result:
        row[:] = [item for item in row if normalize_button_text(str(item)) not in aliases]
    result.append([LANGUAGE_BUTTONS.get(language, LANGUAGE_BUTTONS["fa"])])
    return result


def language_keyboard():
    # Language picker itself is intentionally exempt from the persistent language button.
    return ReplyKeyboardMarkup(LANGUAGE_KEYBOARD, resize_keyboard=True, one_time_keyboard=True, is_persistent=True)


def main_keyboard(language):
    rows = with_language_button(MENU.get(language, MENU["fa"]), language)
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def submenu_keyboard(options, back_label=None, language="fa"):
    back_labels = {
        "fa": "⬅️ بازگشت به منوی اصلی", "en": "⬅️ Back to Main Menu",
        "az": "⬅️ Ana menyuya qayıt", "tr": "⬅️ Ana menüye dön",
        "ar": "⬅️ العودة إلى القائمة الرئيسية", "zh": "⬅️ 返回主菜单", "ru": "⬅️ Вернуться в главное меню",
    }
    rows = [[option] for option in options]
    rows.append([back_label or back_labels.get(language, back_labels["fa"])])
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
    context.user_data["language_picker_active"] = True
    await update.message.reply_text(language_prompt(), reply_markup=language_keyboard())


async def choose_language(update, context, language):
    user = update.effective_user
    if not user or not update.message:
        return
    save_user(user, language)
    context.user_data["language_picker_active"] = False
    form = context.user_data.get("form")
    if form:
        form["language"] = language
        if form.get("mode") == "office_rent":
            await ask_office_step(update.message, context)
        else:
            index = form.get("step", 0)
            if 0 <= index < len(FIELDS):
                field = FIELDS[index]
                await update.message.reply_text(f"📝 {FIELD_LABELS[language][field]}:", reply_markup=main_keyboard(language))
            else:
                context.user_data.pop("form", None)
                await update.message.reply_text(WELCOME[language], reply_markup=main_keyboard(language))
        return
    if context.user_data.get("rent_menu"):
        await update.message.reply_text(RENT_CATEGORY_PROMPTS[language], reply_markup=submenu_keyboard(rent_category_options(language), language=language))
        return
    if context.user_data.get("awaiting_support"):
        prompts = {"fa":"پیام خود را برای پشتیبانی ارسال کنید:","en":"Send your message to support:","az":"Dəstəyə mesajınızı göndərin:","tr":"Destek mesajınızı gönderin:","ar":"أرسل رسالتك إلى الدعم:","zh":"请发送您的客服消息：","ru":"Отправьте сообщение в службу поддержки:"}
        await update.message.reply_text(prompts[language], reply_markup=main_keyboard(language))
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
BACK_BUTTONS = {"⬅️ بازگشت به منوی اصلی", "⬅️ Back to Main Menu", "⬅️ Ana menüyə qayıt", "⬅️ Ana menüye dön", "⬅️ العودة إلى القائمة الرئيسية", "⬅️ 返回主菜单", "⬅️ Вернуться в главное меню"}
CHOICE_BACK = "⬅️ بازگشت"
OFFICE_CHOICE_BUTTONS = {"سند اداری", "موقعیت اداری", "آپارتمان", "مستغلات"}
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

OFFICE_I18N = {
 "fa": {
  "prompts": ["نوع سند/موقعیت اداری را انتخاب کنید:","نوع ملک را انتخاب کنید:","متراژ ملک را فقط با عدد وارد کنید:","تعداد پارکینگ را فقط با عدد وارد کنید:","تعداد اتاق را فقط با عدد وارد کنید:","آسانسور دارد؟","لابی دارد؟","شهر را فقط با حروف وارد کنید:","منطقه شهرداری را فقط با عدد وارد کنید:","نام خیابان را فقط با حروف وارد کنید:","نام کوچه یا خیابان فرعی را وارد کنید (عدد و حروف مجاز است):","شماره پلاک را فقط با عدد وارد کنید:","مبلغ رهن را فقط با عدد وارد کنید:","مبلغ اجاره ماهانه را فقط با عدد وارد کنید:","حداقل ۴ تصویر ملک را ارسال کنید. پس از ارسال ۴ تصویر یا بیشتر، عبارت «📷 پایان تصاویر» را بفرستید.","برای ثبت شماره تماس، دکمه اشتراک‌گذاری شماره تلفن را بزنید."],
  "options": [["📄 سند اداری","📍 موقعیت اداری"],["🏢 آپارتمان","🏛 مستغلات"],[],[],[],["✅ دارد","❌ ندارد"],["✅ دارد","❌ ندارد"]],
  "cancel":"❌ لغو ثبت", "finish_images":"📷 پایان تصاویر", "share_contact":"📱 اشتراک‌گذاری شماره تلگرام"
 },
 "en": {
  "prompts": ["Choose the office document/status:","Choose the property type:","Enter the property area using numbers only:","Enter the number of parking spaces using numbers only:","Enter the number of rooms using numbers only:","Is there an elevator?","Is there a lobby?","Enter the city using letters only:","Enter the municipal district using numbers only:","Enter the street name using letters only:","Enter the alley or side street (letters and numbers are allowed):","Enter the building number using numbers only:","Enter the deposit amount using numbers only:","Enter the monthly rent using numbers only:","Send at least 4 property photos. After sending 4 or more, press ‘📷 Finish Photos’.","To provide your phone number, use the phone-sharing button."],
  "options": [["📄 Office deed","📍 Office location"],["🏢 Apartment","🏛 Commercial property"],[],[],[],["✅ Yes","❌ No"],["✅ Yes","❌ No"]], "cancel":"❌ Cancel Listing", "finish_images":"📷 Finish Photos", "share_contact":"📱 Share Telegram Phone"
 },
 "az": {
  "prompts": ["Ofis sənədini/statusunu seçin:","Əmlak növünü seçin:","Sahəni yalnız rəqəmlərlə daxil edin:","Dayanacaq yerlərinin sayını rəqəmlərlə daxil edin:","Otaqların sayını rəqəmlərlə daxil edin:","Lift var?","Lobbi var?","Şəhəri yalnız hərflərlə daxil edin:","Bələdiyyə rayonunu rəqəmlərlə daxil edin:","Küçə adını yalnız hərflərlə daxil edin:","Dalana və ya yan küçəyə adını daxil edin (rəqəm və hərflər olar):","Bina nömrəsini rəqəmlərlə daxil edin:","Depozit məbləğini rəqəmlərlə daxil edin:","Aylıq kirayəni rəqəmlərlə daxil edin:","Ən azı 4 əmlak şəkli göndərin. Sonra ‘📷 Şəkilləri bitir’ düyməsini seçin.","Telefon nömrəsini paylaşmaq üçün telefon paylaşma düyməsini seçin."],
  "options": [["📄 Ofis sənədi","📍 Ofis yeri"],["🏢 Mənzil","🏛 Kommersiya əmlakı"],[],[],[],["✅ Var","❌ Yoxdur"],["✅ Var","❌ Yoxdur"]], "cancel":"❌ Elanı ləğv et", "finish_images":"📷 Şəkilləri bitir", "share_contact":"📱 Telegram nömrəsini paylaş"
 },
 "tr": {
  "prompts": ["Ofis belge/durumunu seçin:","Gayrimenkul türünü seçin:","Alanı yalnız rakamlarla girin:","Otopark sayısını yalnız rakamlarla girin:","Oda sayısını yalnız rakamlarla girin:","Asansör var mı?","Lobi var mı?","Şehri yalnız harflerle girin:","Belediye bölgesini rakamlarla girin:","Sokak adını yalnız harflerle girin:","Ara sokak adını girin (harf ve rakam kullanılabilir):","Bina numarasını rakamlarla girin:","Depozito tutarını rakamlarla girin:","Aylık kirayı rakamlarla girin:","En az 4 mülk fotoğrafı gönderin. Ardından ‘📷 Fotoğrafları Bitir’ düğmesine basın.","Telefon numaranızı paylaşmak için telefon paylaşma düğmesini kullanın."],
  "options": [["📄 Ofis belgesi","📍 Ofis konumu"],["🏢 Daire","🏛 Ticari mülk"],[],[],[],["✅ Var","❌ Yok"],["✅ Var","❌ Yok"]], "cancel":"❌ İlanı iptal et", "finish_images":"📷 Fotoğrafları Bitir", "share_contact":"📱 Telegram telefonunu paylaş"
 },
 "ar": {
  "prompts": ["اختر مستند المكتب أو حالته:","اختر نوع العقار:","أدخل المساحة بالأرقام فقط:","أدخل عدد مواقف السيارات بالأرقام فقط:","أدخل عدد الغرف بالأرقام فقط:","هل يوجد مصعد؟","هل يوجد بهو؟","أدخل المدينة بالحروف فقط:","أدخل المنطقة البلدية بالأرقام فقط:","أدخل اسم الشارع بالحروف فقط:","أدخل اسم الزقاق أو الشارع الفرعي (الحروف والأرقام مسموحة):","أدخل رقم المبنى بالأرقام فقط:","أدخل مبلغ التأمين بالأرقام فقط:","أدخل الإيجار الشهري بالأرقام فقط:","أرسل 4 صور للعقار على الأقل، ثم اضغط «📷 إنهاء الصور».","لمشاركة رقم الهاتف، استخدم زر مشاركة الهاتف."],
  "options": [["📄 مستند مكتب","📍 موقع مكتب"],["🏢 شقة","🏛 عقار تجاري"],[],[],[],["✅ نعم","❌ لا"],["✅ نعم","❌ لا"]], "cancel":"❌ إلغاء الإعلان", "finish_images":"📷 إنهاء الصور", "share_contact":"📱 مشاركة رقم تلغرام"
 },
 "zh": {
  "prompts": ["请选择办公文件/位置类型：","请选择房产类型：","仅输入数字填写面积：","仅输入数字填写停车位数量：","仅输入数字填写房间数量：","是否有电梯？","是否有大堂？","仅使用字母填写城市：","仅输入数字填写市政区域：","仅使用字母填写街道名称：","填写巷道或支路名称（可使用字母和数字）：","仅输入数字填写门牌号：","仅输入数字填写押金金额：","仅输入数字填写月租金额：","请至少发送4张房产照片，然后点击‘📷 完成照片’。","请使用共享电话号码按钮提交联系电话。"],
  "options": [["📄 办公文件","📍 办公位置"],["🏢 公寓","🏛 商业房产"],[],[],[],["✅ 有","❌ 没有"],["✅ 有","❌ 没有"]], "cancel":"❌ 取消发布", "finish_images":"📷 完成照片", "share_contact":"📱 分享Telegram电话"
 },
 "ru": {
  "prompts": ["Выберите документ или статус офиса:","Выберите тип недвижимости:","Введите площадь только цифрами:","Введите количество парковочных мест только цифрами:","Введите количество комнат только цифрами:","Есть ли лифт?","Есть ли холл?","Введите город только буквами:","Введите муниципальный район только цифрами:","Введите название улицы только буквами:","Введите название переулка или боковой улицы (буквы и цифры допустимы):","Введите номер здания только цифрами:","Введите сумму залога только цифрами:","Введите ежемесячную арендную плату только цифрами:","Отправьте не менее 4 фотографий объекта, затем нажмите «📷 Завершить фотографии».","Чтобы указать номер телефона, используйте кнопку отправки контакта."],
  "options": [["📄 Документ офиса","📍 Местоположение офиса"],["🏢 Квартира","🏛 Коммерческая недвижимость"],[],[],[],["✅ Есть","❌ Нет"],["✅ Есть","❌ Нет"]], "cancel":"❌ Отменить объявление", "finish_images":"📷 Завершить фотографии", "share_contact":"📱 Поделиться номером Telegram"
 }
}

OFFICE_CANONICAL = {
 "office_document_type": {"📄 سند اداری":"سند اداری","📍 موقعیت اداری":"موقعیت اداری"},
 "office_property_type": {"🏢 آپارتمان":"آپارتمان","🏛 مستغلات":"مستغلات"},
 "elevator": {"دارد":"دارد","ندارد":"ندارد"}, "lobby": {"دارد":"دارد","ندارد":"ندارد"}
}

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
    language = form.get("language", "fa")
    key = OFFICE_STEPS[step][0]
    catalog = OFFICE_I18N.get(language, OFFICE_I18N["fa"])
    prompt = catalog["prompts"][step]
    if key == "contact":
        keyboard = form_keyboard([[KeyboardButton(catalog["share_contact"], request_contact=True)], [catalog["cancel"]]], language)
    elif key == "images":
        keyboard = form_keyboard([[catalog["finish_images"]], [catalog["cancel"]]], language)
    elif key in {"office_document_type", "office_property_type", "elevator", "lobby"}:
        keyboard = submenu_keyboard(catalog["options"][step], catalog["cancel"], language)
    else:
        keyboard = form_keyboard([[catalog["cancel"]]], language)
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

    catalog = OFFICE_I18N.get(language, OFFICE_I18N["fa"])
    if text in CANCEL_FORM_BUTTONS or normalize_button_text(text) == normalize_button_text(catalog["cancel"]):
        context.user_data.pop("form", None)
        confirmations = {"fa":"ثبت آگهی لغو شد.","en":"Listing cancelled.","az":"Elan ləğv edildi.","tr":"İlan iptal edildi.","ar":"تم إلغاء الإعلان.","zh":"已取消发布。","ru":"Объявление отменено."}
        await message.reply_text(confirmations[language], reply_markup=main_keyboard(language))
        return True

    if message.contact:
        if OFFICE_STEPS[form["step"]][0] != "contact":
            await message.reply_text({"fa":"لطفاً در مرحله درخواست‌شده پاسخ دهید.","en":"Please respond to the current step.","az":"Zəhmət olmasa cari mərhələyə cavab verin.","tr":"Lütfen mevcut adıma yanıt verin.","ar":"يرجى الرد على الخطوة الحالية.","zh":"请回答当前步骤。","ru":"Пожалуйста, ответьте на текущем этапе."}[language])
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
                {"fa":f"تصویر دریافت شد. تعداد تصاویر: {len(form['images'])}\n" + ("اکنون «📷 پایان تصاویر» را بفرستید یا تصویر بیشتری ارسال کنید." if len(form["images"]) >= 4 else f"حداقل {4-len(form['images'])} تصویر دیگر لازم است."),"en":f"Photo received. Total photos: {len(form['images'])}.\n" + ("Press ‘📷 Finish Photos’ or send more photos." if len(form["images"]) >= 4 else f"Please send {4-len(form['images'])} more photo(s)."),"az":f"Şəkil qəbul edildi. Cəmi: {len(form['images'])}.","tr":f"Fotoğraf alındı. Toplam fotoğraf: {len(form['images'])}.","ar":f"تم استلام الصورة. إجمالي الصور: {len(form['images'])}.","zh":f"已收到照片。照片总数：{len(form['images'])}。","ru":f"Фото получено. Всего фотографий: {len(form['images'])}."}[language],
                reply_markup=form_keyboard([[catalog["finish_images"]], [catalog["cancel"]]], language),
            )
            return True
        if normalize_button_text(text) == normalize_button_text(catalog["finish_images"]) or normalize_button_text(text) == "پایان تصاویر":
            if len(form["images"]) < 4:
                msgs = {"fa":f"حداقل ۴ تصویر لازم است. تاکنون {len(form['images'])} تصویر ارسال کرده‌اید.","en":f"At least 4 photos are required. You have sent {len(form['images'])}.","az":f"Ən azı 4 şəkil lazımdır. İndiyədək {len(form['images'])} şəkil göndərmisiniz.","tr":f"En az 4 fotoğraf gerekli. Şimdiye kadar {len(form['images'])} fotoğraf gönderdiniz.","ar":f"يلزم إرسال 4 صور على الأقل. أرسلت حتى الآن {len(form['images'])} صور.","zh":f"至少需要4张照片。您目前已发送{len(form['images'])}张。","ru":f"Нужно не менее 4 фотографий. Вы отправили {len(form['images'])}."}
                await message.reply_text(msgs[language])
                return True
            form["step"] += 1
            await ask_office_step(message, context)
            return True
        prompts = {"fa":"لطفاً تصویر ملک ارسال کنید یا پس از ارسال حداقل ۴ تصویر، «📷 پایان تصاویر» را بفرستید.","en":"Please send property photos, then press ‘📷 Finish Photos’ after at least 4 photos.","az":"Zəhmət olmasa əmlak şəkillərini göndərin və ən azı 4 şəkildən sonra ‘📷 Şəkilləri bitir’ seçin.","tr":"Lütfen mülk fotoğraflarını gönderin; en az 4 fotoğraftan sonra ‘📷 Fotoğrafları Bitir’ seçin.","ar":"يرجى إرسال صور العقار ثم اختيار «📷 إنهاء الصور» بعد إرسال 4 صور على الأقل.","zh":"请发送房产照片，至少发送4张后点击‘📷 完成照片’。","ru":"Отправьте фотографии объекта, затем нажмите «📷 Завершить фотографии» после 4 фото."}
        await message.reply_text(prompts[language])
        return True

    if not text:
        await message.reply_text({"fa":"لطفاً پاسخ را به‌صورت متن یا با دکمه مناسب ارسال کنید.","en":"Please reply with text or use the appropriate button.","az":"Zəhmət olmasa mətnlə cavab verin və ya uyğun düymədən istifadə edin.","tr":"Lütfen metinle yanıt verin veya uygun düğmeyi kullanın.","ar":"يرجى الرد بالنص أو استخدام الزر المناسب.","zh":"请发送文字回复或使用相应按钮。","ru":"Ответьте текстом или используйте соответствующую кнопку."}[language])
        return True

    if key in {"office_document_type", "office_property_type", "elevator", "lobby"}:
        allowed = catalog["options"][form["step"]]
        normalized_text = normalize_button_text(text)
        normalized_allowed = {normalize_button_text(option): option for option in allowed}
        if normalized_text not in normalized_allowed:
            await message.reply_text({"fa":"لطفاً یکی از گزینه‌های نمایش‌داده‌شده را انتخاب کنید.","en":"Please choose one of the displayed options.","az":"Zəhmət olmasa göstərilən seçimlərdən birini seçin.","tr":"Lütfen gösterilen seçeneklerden birini seçin.","ar":"يرجى اختيار أحد الخيارات المعروضة.","zh":"请选择显示的选项之一。","ru":"Выберите один из предложенных вариантов."}[language])
            return True
        selected = normalized_text
        canonical_map = {
            "office_document_type": {"Office deed":"سند اداری", "Office location":"موقعیت اداری", "Ofis sənədi":"سند اداری", "Ofis yeri":"موقعیت اداری", "Ofis belgesi":"سند اداری", "Ofis konumu":"موقعیت اداری", "مستند مكتب":"سند اداری", "موقع مكتب":"موقعیت اداری", "办公文件":"سند اداری", "办公位置":"موقعیت اداری", "Документ офиса":"سند اداری", "Местоположение офиса":"موقعیت اداری"},
            "office_property_type": {"Apartment":"آپارتمان", "Commercial property":"مستغلات", "Mənzil":"آپارتمان", "Kommersiya əmlakı":"مستغلات", "Daire":"آپارتمان", "Ticari mülk":"مستغلات", "شقة":"آپارتمان", "عقار تجاري":"مستغلات", "公寓":"آپارتمان", "商业房产":"مستغلات", "Квартира":"آپارتمان", "Коммерческая недвижимость":"مستغلات"},
            "elevator": {"Yes":"دارد", "Var":"دارد", "نعم":"دارد", "有":"دارد", "Есть":"دارد", "No":"ندارد", "Yoxdur":"ندارد", "لا":"ندارد", "没有":"ندارد", "Нет":"ندارد"},
            "lobby": {"Yes":"دارد", "Var":"دارد", "نعم":"دارد", "有":"دارد", "Есть":"دارد", "No":"ندارد", "Yoxdur":"ندارد", "لا":"ندارد", "没有":"ندارد", "Нет":"ندارد"},
        }
        value = canonical_map.get(key, {}).get(selected, selected)
        if key in {"elevator", "lobby"}:
            value = "دارد" if selected in {"دارد", "Yes", "Var", "نعم", "有", "Есть"} else "ندارد"
        form["data"][key] = value
    elif key in {"area", "parking", "rooms", "municipal_district", "plaque", "deposit", "rent"}:
        if not digits_only(text):
            await message.reply_text({"fa":"ورودی این مرحله باید فقط عدد باشد. لطفاً دوباره وارد کنید.","en":"This field accepts numbers only. Please try again.","az":"Bu sahəyə yalnız rəqəm daxil edin. Yenidən cəhd edin.","tr":"Bu alana yalnız rakam girin. Tekrar deneyin.","ar":"يجب إدخال أرقام فقط في هذه الخانة. حاول مرة أخرى.","zh":"此项只能输入数字，请重试。","ru":"В этом поле допустимы только цифры. Попробуйте снова."}[language])
            return True
        form["data"][key] = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    elif key in {"city", "street"}:
        if not letters_only(text):
            await message.reply_text({"fa":"لطفاً فقط حروف وارد کنید؛ از عدد و نشانه استفاده نکنید.","en":"Please use letters only; do not enter numbers or symbols.","az":"Yalnız hərflərdən istifadə edin; rəqəm və işarələr daxil etməyin.","tr":"Lütfen yalnız harf kullanın; rakam veya işaret girmeyin.","ar":"يرجى استخدام الحروف فقط دون أرقام أو رموز.","zh":"请仅输入字母，不要输入数字或符号。","ru":"Используйте только буквы, без цифр и символов."}[language])
            return True
        form["data"][key] = text
    elif key == "alley":
        if not any(ch.isalnum() or ch.isalpha() for ch in text):
            await message.reply_text({"fa":"نام کوچه یا خیابان فرعی را با حروف یا عدد وارد کنید.","en":"Enter the alley or side-street name using letters or numbers.","az":"Dalana və ya yan küçənin adını hərf və ya rəqəmlərlə daxil edin.","tr":"Ara sokak adını harf veya rakamlarla girin.","ar":"أدخل اسم الزقاق أو الشارع الفرعي باستخدام الحروف أو الأرقام.","zh":"请使用字母或数字填写巷道或支路名称。","ru":"Введите название переулка или боковой улицы буквами или цифрами."}[language])
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
            RENT_CATEGORY_PROMPTS.get(language, RENT_CATEGORY_PROMPTS["fa"]),
            reply_markup=submenu_keyboard(rent_category_options(language), language=language),
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
    *LANGUAGE_BUTTONS.values(),
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

    if not update.message.text:
        # Keep existing media/contact handling for the office-rent form.
        if context.user_data.get("form", {}).get("mode") == "office_rent":
            if update.message.contact or update.message.photo:
                if await process_office_rent(update, context):
                    return
        return

    text = update.message.text.strip()

    # The language-change control must work from the main menu, every submenu,
    # and every step of an active form.
    language_change_labels = {normalize_button_text(label) for label in LANGUAGE_BUTTONS.values()}
    if text in LANGUAGE_CHANGE_BUTTONS or normalize_button_text(text) in language_change_labels:
        context.user_data["language_picker_active"] = True
        await update.message.reply_text(language_prompt(), reply_markup=language_keyboard())
        return

    # A language label is treated as a selection only while the picker is active.
    language = parse_language(text) if context.user_data.get("language_picker_active") or not get_user(user.id) else None
    if language:
        await choose_language(update, context, language)
        return

    # Continue the existing office-rent flow for ordinary text messages.
    if context.user_data.get("form", {}).get("mode") == "office_rent":
        if await process_office_rent(update, context):
            return

    saved_user = get_user(user.id)
    if not saved_user:
        await update.message.reply_text(language_prompt(), reply_markup=language_keyboard())
        return
    user_language = saved_user["language"]

    if text in BACK_BUTTONS or normalize_button_text(text) in {"Back to Main Menu", "Ana menyuya qayıt", "Ana menüye dön", "العودة إلى القائمة الرئيسية", "返回主菜单", "Вернуться в главное меню"}:
        context.user_data.pop("form", None)
        context.user_data.pop("rent_menu", None)
        context.user_data.pop("awaiting_support", None)
        back_messages = {"fa":"به منوی اصلی بازگشتید.","en":"Returned to the main menu.","az":"Əsas menyuya qayıtdınız.","tr":"Ana menüye döndünüz.","ar":"تمت العودة إلى القائمة الرئيسية.","zh":"已返回主菜单。","ru":"Вы вернулись в главное меню."}
        await update.message.reply_text(back_messages[user_language], reply_markup=main_keyboard(user_language))
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
        category = RENT_CATEGORY_MAP.get(normalize_button_text(text))
        if not category:
            await update.message.reply_text(
                RENT_CATEGORY_PROMPTS.get(user_language, RENT_CATEGORY_PROMPTS["fa"]),
                reply_markup=submenu_keyboard(rent_category_options(user_language), language=user_language),
            )
            return
        context.user_data.pop("rent_menu", None)
        if category == "اداری":
            await begin_office_rent_form(update, context, user_language)
        else:
            category_label = RENT_CATEGORY_LABELS[user_language][category]
            category_label = normalize_button_text(category_label)
            messages = {
                "fa": f"بخش «{category_label}» انتخاب شد؛ فرم اختصاصی این دسته هنوز تعریف نشده است.",
                "en": f"The {category_label} category was selected; its dedicated form is not available yet.",
                "az": f"{category_label} kateqoriyası seçildi; bu kateqoriya üçün ayrıca forma hələ hazır deyil.",
                "tr": f"{category_label} kategorisi seçildi; bu kategoriye özel form henüz hazır değil.",
                "ar": f"تم اختيار فئة {category_label}؛ النموذج المخصص لها غير متاح بعد.",
                "zh": f"已选择{category_label}类别；该类别的专用表单尚未开放。",
                "ru": f"Выбрана категория «{category_label}»; специальная форма пока недоступна.",
            }
            await update.message.reply_text(messages[user_language], reply_markup=main_keyboard(user_language))
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

    if text in LANGUAGE_CHANGE_BUTTONS or normalize_button_text(text) in {normalize_button_text(x) for x in LANGUAGE_BUTTONS.values()}:
        context.user_data["language_picker_active"] = True
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
