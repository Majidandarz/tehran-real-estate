
import os
import json
import sqlite3
import logging
from datetime import datetime
from html import escape

from flask import Flask
from threading import Thread
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.constants import ParseMode
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

CHANNELS = {
    "fa": "@tehranrealstate",
    "en": "@tehranrealstate_eng",
    "az": "@tehranrealstate_az",
    "tr": "@tehranrealstate_tur",
    "ar": "@tehranrealstate_ara",
}

LANG_NAMES = {
    "fa": "فارسی",
    "en": "English",
    "az": "Azərbaycan dili",
    "tr": "Türkçe",
    "ar": "العربية",
}

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ==================== متن‌های چندزبانه ====================

T = {
    "fa": {
        "welcome": (
            "🏡✨ <b>به گروه بزرگ املاک تهران خوش آمدید!</b> ✨🏡\n\n"
            "🌟 مجموعه املاک تهران با بیش از <b>۲۰ سال سابقه فعالیت</b> "
            "و شبکه‌ای گسترده از مشاوران ملکی، در کنار شماست.\n\n"
            "🔑 خرید و فروش ملک | 🏢 اجاره | 💎 سرمایه‌گذاری ملکی\n\n"
            "🤝 هدف ما ارائه خدماتی شایسته، مطمئن و حرفه‌ای است.\n\n"
            "💠 <b>املاک تهران؛ همراه شما در مسیر انتخابی مطمئن.</b> 💠"
        ),
        "main": "منوی اصلی",
        "buyer": "🔎 متقاضی خرید یا اجاره",
        "seller": "🏠 فروشنده یا موجر",
        "invest": "💎 سرمایه‌گذاری ملکی و مشارکت در ساخت",
        "broker": "🤝 مشاور املاک",
        "support": "📞 پشتیبانی و ارتباط با مدیر",
        "change": "🌐 تغییر زبان",
        "back": "⬅️ بازگشت به منوی اصلی",
        "choose_lang": "زبان موردنظر را انتخاب کنید:",
        "lang_changed": "زبان تغییر کرد. مرحله فعلی شما حفظ شده است.",
        "buy_req": "🔎 ثبت تقاضای خرید",
        "rent_req": "🔑 ثبت تقاضای اجاره",
        "sell_ad": "🏡 ثبت آگهی فروش",
        "rent_ad": "🏠 ثبت آگهی اجاره",
        "prebuy": "💎 درخواست پیش‌خرید",
        "builder": "🏗️ سازنده آماده مشارکت هستم",
        "owner_build": "🏡 مالک ملک برای مشارکت در ساخت هستم",
        "broker_ad": "🏡 ثبت آگهی ملک",
        "leads": "📋 پیگیری مشتریان",
        "cooperate": "🤝 درخواست همکاری با مشاوران",
        "message_admin": "✉️ ارسال پیام به مدیر",
        "report": "⚠️ گزارش مشکل یا تخلف",
        "property_type": "نوع ملک را انتخاب کنید:",
        "residential": "مسکونی",
        "office": "اداری",
        "commercial": "تجاری",
        "agricultural": "زراعی",
        "industrial": "صنعتی",
        "city": "شهر و منطقه ملک را وارد کنید:",
        "area": "متراژ ملک را به مترمربع وارد کنید:",
        "price": "قیمت کل را وارد کنید. اگر توافقی است بنویسید «توافقی».",
        "details": "توضیحات آگهی را ارسال کنید:",
        "phone": "شماره تماس یا شناسه تلگرام برای پیگیری را وارد کنید:",
        "cancel": "❌ لغو فرم",
        "cancelled": "فرم لغو شد. اطلاعات مرحله‌ای این فرم پاک شد.",
        "submitted": "آگهی برای بررسی مدیر ارسال شد.",
        "request_submitted": "درخواست شما برای بررسی مدیر ارسال شد.",
        "admin_new": "📥 <b>آگهی جدید برای بررسی</b>",
        "approve": "✅ تأیید و انتشار",
        "reject": "❌ رد آگهی",
        "approved": "آگهی تأیید شد و برای انتشار ارسال گردید.",
        "rejected": "آگهی رد شد.",
        "not_found": "این آگهی پیدا نشد یا قبلاً بررسی شده است.",
        "unknown": "لطفاً یکی از گزینه‌های منو را انتخاب کنید یا /start را بزنید.",
        "admin_only": "این عملیات فقط برای مدیر اصلی مجاز است.",
        "ad_title": "آگهی املاک تهران",
        "type": "نوع ملک",
        "purpose": "نوع درخواست",
        "city_label": "شهر و منطقه",
        "area_label": "متراژ",
        "price_label": "قیمت",
        "details_label": "توضیحات",
        "phone_label": "راه ارتباطی",
        "language_label": "زبان انتشار",
        "buy_purpose": "تقاضای خرید",
        "rent_purpose": "تقاضای اجاره",
        "sell_purpose": "فروش",
        "rent_offer_purpose": "اجاره",
        "prebuy_purpose": "پیش‌خرید",
        "builder_purpose": "سازنده برای مشارکت",
        "owner_build_purpose": "مالک برای مشارکت در ساخت",
        "broker_purpose": "آگهی مشاور املاک",
        "menu_broker": "مشاور املاک",
        "menu_buyer": "متقاضی",
        "menu_seller": "فروشنده یا موجر",
        "menu_invest": "سرمایه‌گذاری",
        "menu_support": "پشتیبانی",
    },
    "en": {
        "welcome": (
            "🏡✨ <b>Welcome to Tehran Real Estate!</b> ✨🏡\n\n"
            "🌟 We provide real-estate services with extensive market experience "
            "and a broad network of property consultants.\n\n"
            "🔑 Buying and selling | 🏢 Renting | 💎 Property investment\n\n"
            "🤝 Our goal is to provide reliable and professional service."
        ),
        "main": "Main menu",
        "buyer": "🔎 Buyer or tenant",
        "seller": "🏠 Seller or landlord",
        "invest": "💎 Investment and development",
        "broker": "🤝 Real estate agent",
        "support": "📞 Support and contact admin",
        "change": "🌐 Change language",
        "back": "⬅️ Main menu",
        "choose_lang": "Choose your language:",
        "lang_changed": "Language changed. Your current form step is preserved.",
        "buy_req": "🔎 Submit a purchase request",
        "rent_req": "🔑 Submit a rental request",
        "sell_ad": "🏡 Create a sale listing",
        "rent_ad": "🏠 Create a rental listing",
        "prebuy": "💎 Pre-purchase request",
        "builder": "🏗️ Developer seeking a partnership",
        "owner_build": "🏡 Owner seeking a development partnership",
        "broker_ad": "🏡 Create a property listing",
        "leads": "📋 Follow up with clients",
        "cooperate": "🤝 Request agent cooperation",
        "message_admin": "✉️ Message the administrator",
        "report": "⚠️ Report a problem or violation",
        "property_type": "Choose property type:",
        "residential": "Residential",
        "office": "Office",
        "commercial": "Commercial",
        "agricultural": "Agricultural",
        "industrial": "Industrial",
        "city": "Enter the city and area:",
        "area": "Enter the area in square metres:",
        "price": "Enter the total price, or type “Negotiable”.",
        "details": "Enter the listing description:",
        "phone": "Enter a contact number or Telegram username:",
        "cancel": "❌ Cancel form",
        "cancelled": "Form cancelled and its draft data cleared.",
        "submitted": "Your listing has been sent to the administrator for review.",
        "request_submitted": "Your request has been sent to the administrator.",
        "admin_new": "📥 <b>New listing for review</b>",
        "approve": "✅ Approve and publish",
        "reject": "❌ Reject listing",
        "approved": "Listing approved and sent for publication.",
        "rejected": "Listing rejected.",
        "not_found": "Listing not found or already reviewed.",
        "unknown": "Choose a menu option or send /start.",
        "admin_only": "Only the main administrator can do this.",
        "ad_title": "Tehran Real Estate Listing",
        "type": "Property type",
        "purpose": "Request type",
        "city_label": "City and area",
        "area_label": "Area",
        "price_label": "Price",
        "details_label": "Description",
        "phone_label": "Contact",
        "language_label": "Publication language",
        "buy_purpose": "Purchase request",
        "rent_purpose": "Rental request",
        "sell_purpose": "For sale",
        "rent_offer_purpose": "For rent",
        "prebuy_purpose": "Pre-purchase",
        "builder_purpose": "Developer seeking partnership",
        "owner_build_purpose": "Owner seeking development partnership",
        "broker_purpose": "Agent listing",
        "menu_broker": "Real estate agent",
        "menu_buyer": "Buyer or tenant",
        "menu_seller": "Seller or landlord",
        "menu_invest": "Investment",
        "menu_support": "Support",
    },
    "az": {
        "welcome": (
            "🏡✨ <b>Tehran Daşınmaz Əmlaka xoş gəlmisiniz!</b> ✨🏡\n\n"
            "🔑 Alqı-satqı | 🏢 İcarə | 💎 Əmlak investisiyası\n\n"
            "🤝 Məqsədimiz sizə etibarlı və peşəkar xidmət göstərməkdir."
        ),
        "main": "Əsas menyu",
        "buyer": "🔎 Alıcı və ya kirayəçi",
        "seller": "🏠 Satıcı və ya ev sahibi",
        "invest": "💎 İnvestisiya və tikinti tərəfdaşlığı",
        "broker": "🤝 Əmlak məsləhətçisi",
        "support": "📞 Dəstək və rəhbərlə əlaqə",
        "change": "🌐 Dili dəyiş",
        "back": "⬅️ Əsas menyu",
        "choose_lang": "Dilinizi seçin:",
        "lang_changed": "Dil dəyişdirildi. Cari mərhələ saxlanıldı.",
        "buy_req": "🔎 Alış sorğusu",
        "rent_req": "🔑 İcarə sorğusu",
        "sell_ad": "🏡 Satış elanı yarat",
        "rent_ad": "🏠 İcarə elanı yarat",
        "prebuy": "💎 İlkin alış sorğusu",
        "builder": "🏗️ Tikinti tərəfdaşı axtarıram",
        "owner_build": "🏡 Tikinti tərəfdaşlığı üçün mülk sahibiyəm",
        "broker_ad": "🏡 Əmlak elanı yarat",
        "leads": "📋 Müştəriləri izləmək",
        "cooperate": "🤝 Əməkdaşlıq sorğusu",
        "message_admin": "✉️ Rəhbərə mesaj",
        "report": "⚠️ Problem və ya pozuntu bildir",
        "property_type": "Əmlak növünü seçin:",
        "residential": "Yaşayış",
        "office": "Ofis",
        "commercial": "Kommersiya",
        "agricultural": "Kənd təsərrüfatı",
        "industrial": "Sənaye",
        "city": "Şəhər və ərazini daxil edin:",
        "area": "Sahəni kvadratmetrlə daxil edin:",
        "price": "Ümumi qiyməti və ya “Razılaşma yolu ilə” yazın:",
        "details": "Elanın təsvirini daxil edin:",
        "phone": "Əlaqə nömrəsi və ya Telegram istifadəçi adını daxil edin:",
        "cancel": "❌ Formanı ləğv et",
        "cancelled": "Forma ləğv edildi və qaralama məlumatları silindi.",
        "submitted": "Elan administratora yoxlama üçün göndərildi.",
        "request_submitted": "Sorğunuz administratora göndərildi.",
        "admin_new": "📥 <b>Yoxlama üçün yeni elan</b>",
        "approve": "✅ Təsdiqlə və yayımla",
        "reject": "❌ Elanı rədd et",
        "approved": "Elan təsdiqləndi və yayıma göndərildi.",
        "rejected": "Elan rədd edildi.",
        "not_found": "Elan tapılmadı və ya artıq yoxlanılıb.",
        "unknown": "Menyu seçimlərindən istifadə edin və ya /start yazın.",
        "admin_only": "Bu əməliyyatı yalnız əsas administrator edə bilər.",
        "ad_title": "Tehran daşınmaz əmlak elanı",
        "type": "Əmlak növü",
        "purpose": "Sorğu növü",
        "city_label": "Şəhər və ərazi",
        "area_label": "Sahə",
        "price_label": "Qiymət",
        "details_label": "Təsvir",
        "phone_label": "Əlaqə",
        "language_label": "Yayım dili",
        "buy_purpose": "Alış sorğusu",
        "rent_purpose": "İcarə sorğusu",
        "sell_purpose": "Satış",
        "rent_offer_purpose": "İcarə",
        "prebuy_purpose": "İlkin alış",
        "builder_purpose": "Tikinti tərəfdaşı",
        "owner_build_purpose": "Tikinti üçün mülk sahibi",
        "broker_purpose": "Agent elanı",
        "menu_broker": "Əmlak məsləhətçisi",
        "menu_buyer": "Alıcı və ya kirayəçi",
        "menu_seller": "Satıcı və ya ev sahibi",
        "menu_invest": "İnvestisiya",
        "menu_support": "Dəstək",
    },
    "tr": {
        "welcome": (
            "🏡✨ <b>Tehran Gayrimenkul'e hoş geldiniz!</b> ✨🏡\n\n"
            "🔑 Alım-satım | 🏢 Kiralama | 💎 Gayrimenkul yatırımı\n\n"
            "🤝 Amacımız güvenilir ve profesyonel hizmet sunmaktır."
        ),
        "main": "Ana menü",
        "buyer": "🔎 Alıcı veya kiracı",
        "seller": "🏠 Satıcı veya ev sahibi",
        "invest": "💎 Yatırım ve inşaat ortaklığı",
        "broker": "🤝 Emlak danışmanı",
        "support": "📞 Destek ve yöneticiyle iletişim",
        "change": "🌐 Dili değiştir",
        "back": "⬅️ Ana menü",
        "choose_lang": "Dil seçin:",
        "lang_changed": "Dil değiştirildi. Mevcut form adımınız korundu.",
        "buy_req": "🔎 Satın alma talebi",
        "rent_req": "🔑 Kiralama talebi",
        "sell_ad": "🏡 Satılık ilanı oluştur",
        "rent_ad": "🏠 Kiralık ilanı oluştur",
        "prebuy": "💎 Ön satın alma talebi",
        "builder": "🏗️ İnşaat ortaklığı arayan geliştiriciyim",
        "owner_build": "🏡 İnşaat ortaklığı için mülk sahibiyim",
        "broker_ad": "🏡 Emlak ilanı oluştur",
        "leads": "📋 Müşteri takibi",
        "cooperate": "🤝 Danışmanlarla iş birliği talebi",
        "message_admin": "✉️ Yöneticiye mesaj gönder",
        "report": "⚠️ Sorun veya ihlal bildir",
        "property_type": "Gayrimenkul türünü seçin:",
        "residential": "Konut",
        "office": "Ofis",
        "commercial": "Ticari",
        "agricultural": "Tarım arazisi",
        "industrial": "Sanayi",
        "city": "Şehir ve bölgeyi girin:",
        "area": "Metrekare cinsinden alanı girin:",
        "price": "Toplam fiyatı veya “Pazarlık” yazın:",
        "details": "İlan açıklamasını girin:",
        "phone": "Telefon numarası veya Telegram kullanıcı adını girin:",
        "cancel": "❌ Formu iptal et",
        "cancelled": "Form iptal edildi ve taslak verileri silindi.",
        "submitted": "İlan yönetici incelemesine gönderildi.",
        "request_submitted": "Talebiniz yöneticiye gönderildi.",
        "admin_new": "📥 <b>İnceleme için yeni ilan</b>",
        "approve": "✅ Onayla ve yayımla",
        "reject": "❌ İlanı reddet",
        "approved": "İlan onaylandı ve yayıma gönderildi.",
        "rejected": "İlan reddedildi.",
        "not_found": "İlan bulunamadı veya daha önce incelendi.",
        "unknown": "Menüden bir seçenek seçin veya /start yazın.",
        "admin_only": "Bu işlemi yalnızca ana yönetici yapabilir.",
        "ad_title": "Tehran Gayrimenkul İlanı",
        "type": "Gayrimenkul türü",
        "purpose": "Talep türü",
        "city_label": "Şehir ve bölge",
        "area_label": "Alan",
        "price_label": "Fiyat",
        "details_label": "Açıklama",
        "phone_label": "İletişim",
        "language_label": "Yayın dili",
        "buy_purpose": "Satın alma talebi",
        "rent_purpose": "Kiralama talebi",
        "sell_purpose": "Satılık",
        "rent_offer_purpose": "Kiralık",
        "prebuy_purpose": "Ön satın alma",
        "builder_purpose": "İnşaat ortağı arayan geliştirici",
        "owner_build_purpose": "İnşaat ortaklığı için mülk sahibi",
        "broker_purpose": "Danışman ilanı",
        "menu_broker": "Emlak danışmanı",
        "menu_buyer": "Alıcı veya kiracı",
        "menu_seller": "Satıcı veya ev sahibi",
        "menu_invest": "Yatırım",
        "menu_support": "Destek",
    },
    "ar": {
        "welcome": (
            "🏡✨ <b>مرحباً بكم في عقارات طهران!</b> ✨🏡\n\n"
            "🔑 شراء وبيع العقارات | 🏢 الإيجار | 💎 الاستثمار العقاري\n\n"
            "🤝 هدفنا تقديم خدمات موثوقة واحترافية."
        ),
        "main": "القائمة الرئيسية",
        "buyer": "🔎 مشتري أو مستأجر",
        "seller": "🏠 بائع أو مالك",
        "invest": "💎 الاستثمار والشراكة في البناء",
        "broker": "🤝 وسيط عقاري",
        "support": "📞 الدعم والتواصل مع الإدارة",
        "change": "🌐 تغيير اللغة",
        "back": "⬅️ القائمة الرئيسية",
        "choose_lang": "اختر اللغة:",
        "lang_changed": "تم تغيير اللغة مع الحفاظ على مرحلة النموذج الحالية.",
        "buy_req": "🔎 طلب شراء",
        "rent_req": "🔑 طلب إيجار",
        "sell_ad": "🏡 إنشاء إعلان بيع",
        "rent_ad": "🏠 إنشاء إعلان إيجار",
        "prebuy": "💎 طلب شراء مسبق",
        "builder": "🏗️ مطور يبحث عن شراكة",
        "owner_build": "🏡 مالك عقار يبحث عن شراكة بناء",
        "broker_ad": "🏡 إنشاء إعلان عقاري",
        "leads": "📋 متابعة العملاء",
        "cooperate": "🤝 طلب التعاون مع الوسطاء",
        "message_admin": "✉️ إرسال رسالة إلى الإدارة",
        "report": "⚠️ الإبلاغ عن مشكلة أو مخالفة",
        "property_type": "اختر نوع العقار:",
        "residential": "سكني",
        "office": "مكتبي",
        "commercial": "تجاري",
        "agricultural": "زراعي",
        "industrial": "صناعي",
        "city": "أدخل المدينة والمنطقة:",
        "area": "أدخل المساحة بالمتر المربع:",
        "price": "أدخل السعر الإجمالي أو اكتب «قابل للتفاوض».",
        "details": "أدخل وصف الإعلان:",
        "phone": "أدخل رقم التواصل أو اسم مستخدم تيليجرام:",
        "cancel": "❌ إلغاء النموذج",
        "cancelled": "تم إلغاء النموذج ومسح بيانات المسودة.",
        "submitted": "تم إرسال الإعلان إلى الإدارة للمراجعة.",
        "request_submitted": "تم إرسال طلبك إلى الإدارة.",
        "admin_new": "📥 <b>إعلان جديد للمراجعة</b>",
        "approve": "✅ موافقة ونشر",
        "reject": "❌ رفض الإعلان",
        "approved": "تمت الموافقة على الإعلان وإرساله للنشر.",
        "rejected": "تم رفض الإعلان.",
        "not_found": "الإعلان غير موجود أو تمت مراجعته مسبقاً.",
        "unknown": "اختر أحد خيارات القائمة أو أرسل /start.",
        "admin_only": "هذه العملية متاحة للمدير الرئيسي فقط.",
        "ad_title": "إعلان عقاري - طهران",
        "type": "نوع العقار",
        "purpose": "نوع الطلب",
        "city_label": "المدينة والمنطقة",
        "area_label": "المساحة",
        "price_label": "السعر",
        "details_label": "الوصف",
        "phone_label": "التواصل",
        "language_label": "لغة النشر",
        "buy_purpose": "طلب شراء",
        "rent_purpose": "طلب إيجار",
        "sell_purpose": "للبيع",
        "rent_offer_purpose": "للإيجار",
        "prebuy_purpose": "شراء مسبق",
        "builder_purpose": "مطور يبحث عن شراكة",
        "owner_build_purpose": "مالك عقار لشراكة بناء",
        "broker_purpose": "إعلان وسيط",
        "menu_broker": "وسيط عقاري",
        "menu_buyer": "مشتري أو مستأجر",
        "menu_seller": "بائع أو مالك",
        "menu_invest": "استثمار",
        "menu_support": "الدعم",
    },
}

PROPERTY_KEYS = [
    "residential", "office", "commercial", "agricultural", "industrial"
]

PURPOSE_KEYS = {
    "buy_req": "buy_purpose",
    "rent_req": "rent_purpose",
    "sell_ad": "sell_purpose",
    "rent_ad": "rent_offer_purpose",
    "prebuy": "prebuy_purpose",
    "builder": "builder_purpose",
    "owner_build": "owner_build_purpose",
    "broker_ad": "broker_purpose",
}

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
                language TEXT NOT NULL DEFAULT 'fa'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                purpose TEXT NOT NULL,
                data_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                state_json TEXT NOT NULL
            )
        """)


def get_language(user_id):
    with db() as conn:
        row = conn.execute(
            "SELECT language FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
    return row["language"] if row else "fa"


def set_language(user_id, lang):
    if lang not in LANG_NAMES:
        return
    with db() as conn:
        conn.execute(
            """INSERT INTO users(user_id, language) VALUES(?, ?)
               ON CONFLICT(user_id) DO UPDATE SET language=excluded.language""",
            (user_id, lang),
        )


def get_state(user_id):
    with db() as conn:
        row = conn.execute(
            "SELECT state_json FROM user_states WHERE user_id=?", (user_id,)
        ).fetchone()
    if not row:
        return {"step": "menu"}
    try:
        return json.loads(row["state_json"])
    except Exception:
        return {"step": "menu"}


def save_state(user_id, state):
    with db() as conn:
        conn.execute(
            """INSERT INTO user_states(user_id, state_json) VALUES(?, ?)
               ON CONFLICT(user_id) DO UPDATE SET state_json=excluded.state_json""",
            (user_id, json.dumps(state, ensure_ascii=False)),
        )


def save_ad(user_id, lang, purpose, data):
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO ads(user_id, language, purpose, data_json, status, created_at)
               VALUES(?, ?, ?, ?, 'pending', ?)""",
            (
                user_id, lang, purpose,
                json.dumps(data, ensure_ascii=False),
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        return cur.lastrowid


def get_ad(ad_id):
    with db() as conn:
        return conn.execute("SELECT * FROM ads WHERE id=?", (ad_id,)).fetchone()


def set_ad_status(ad_id, status):
    with db() as conn:
        cur = conn.execute(
            "UPDATE ads SET status=? WHERE id=? AND status='pending'",
            (status, ad_id),
        )
        return cur.rowcount > 0


# ==================== منوها ====================

def keyboard(user_id, rows):
    lang = get_language(user_id)
    rows = [list(row) for row in rows]
    # دکمه تغییر زبان در تمام صفحه‌ها ثابت است.
    rows.append([T[lang]["change"]])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def main_keyboard(user_id):
    lang = get_language(user_id)
    t = T[lang]
    return keyboard(user_id, [
        [t["buyer"], t["seller"]],
        [t["invest"]],
        [t["broker"]],
        [t["support"]],
    ])


def language_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["فارسی", "English"],
            ["Azərbaycan dili", "Türkçe"],
            ["العربية"],
        ],
        resize_keyboard=True,
    )


def language_from_text(text):
    values = {
        "فارسی": "fa",
        "English": "en",
        "Azərbaycan dili": "az",
        "Türkçe": "tr",
        "العربية": "ar",
    }
    return values.get(text.strip())


def submenu(user_id, menu):
    lang = get_language(user_id)
    t = T[lang]

    options = {
        "buyer": [[t["buy_req"]], [t["rent_req"]], [t["back"]]],
        "seller": [[t["sell_ad"]], [t["rent_ad"]], [t["back"]]],
        "invest": [
            [t["prebuy"]],
            [t["builder"]],
            [t["owner_build"]],
            [t["back"]],
        ],
        "broker": [
            [t["broker_ad"]],
            [t["leads"]],
            [t["cooperate"]],
            [t["back"]],
        ],
        "support": [
            [t["message_admin"]],
            [t["report"]],
            [t["back"]],
        ],
    }
    return keyboard(user_id, options.get(menu, [[t["back"]]]))


def language_selection_text(user_id):
    return T[get_language(user_id)]["choose_lang"]


def prompt_for_state(user_id, state):
    t = T[get_language(user_id)]
    step = state.get("step", "menu")
    if step == "property_type":
        return t["property_type"]
    if step == "city":
        return t["city"]
    if step == "area":
        return t["area"]
    if step == "price":
        return t["price"]
    if step == "details":
        return t["details"]
    if step == "phone":
        return t["phone"]
    if step == "support_message":
        return t["message_admin"]
    if step == "report_message":
        return t["report"]
    return t["main"]


# ==================== نمایش آگهی ====================

def render_ad(data, lang, include_original=False):
    t = T[lang]
    property_key = data.get("property_type", "residential")
    purpose_key = PURPOSE_KEYS.get(data.get("purpose", ""), "sell_purpose")

    lines = [
        f"🏡 <b>{escape(t['ad_title'])}</b>",
        "",
        f"🔹 <b>{escape(t['purpose'])}:</b> {escape(t[purpose_key])}",
        f"🏢 <b>{escape(t['type'])}:</b> {escape(t[property_key])}",
        f"📍 <b>{escape(t['city_label'])}:</b> {escape(data.get('city', ''))}",
        f"📐 <b>{escape(t['area_label'])}:</b> {escape(data.get('area', ''))}",
        f"💰 <b>{escape(t['price_label'])}:</b> {escape(data.get('price', ''))}",
        f"📝 <b>{escape(t['details_label'])}:</b> {escape(data.get('details', ''))}",
        f"📞 <b>{escape(t['phone_label'])}:</b> {escape(data.get('phone', ''))}",
    ]
    if include_original:
        original_lang = data.get("language", "fa")
        lines += [
            "",
            "⚠️ <b>توضیحات آزاد به‌صورت خودکار ترجمه نشده است.</b>",
            f"زبان اصلی آگهی: {LANG_NAMES.get(original_lang, original_lang)}",
        ]
    return "\n".join(lines)


async def send_admin_review(context, ad_id, user_id, data):
    lang = data.get("language", "fa")
    t = T[lang]

    # هر پنج نسخه برای بازبینی مدیر ارسال می‌شود.
    # فیلدهای ساختاریافته ترجمه شده‌اند؛ متن آزاد توضیحات، ترجمه خودکار ندارد.
    for target_lang in ["fa", "en", "az", "tr", "ar"]:
        caption = (
            f"{t['admin_new']}\n"
            f"🆔 شناسه آگهی: <code>{ad_id}</code>\n"
            f"👤 شناسه کاربر: <code>{user_id}</code>\n"
            f"🌐 زبان اصلی: {LANG_NAMES[lang]}\n"
            f"📣 کانال مقصد: {CHANNELS[lang]}\n\n"
            f"{render_ad(data, target_lang, include_original=True)}"
        )
        # جلوگیری از تکرار دکمه‌ها؛ دکمه‌ها فقط روی پیام نسخه فارسی هستند.
        markup = None
        if target_lang == "fa":
            markup = InlineKeyboardMarkup([[
                InlineKeyboardButton(t["approve"], callback_data=f"approve:{ad_id}"),
                InlineKeyboardButton(t["reject"], callback_data=f"reject:{ad_id}"),
            ]])
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
            )
        except Exception:
            log.exception("Could not send review message for ad %s", ad_id)


# ==================== دستورات ربات ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users(user_id, language) VALUES(?, 'fa')",
            (user.id,),
        )

    state = get_state(user.id)
    # فقط کاربر جدید به انتخاب زبان هدایت می‌شود.
    if not state.get("language_selected"):
        state["step"] = "choose_language"
        save_state(user.id, state)
        await update.message.reply_text(
            language_selection_text(user.id),
            reply_markup=language_keyboard(),
        )
        return

    await update.message.reply_text(
        T[get_language(user.id)]["welcome"],
        parse_mode=ParseMode.HTML,
        reply_markup=main_keyboard(user.id),
    )


async def show_main(update: Update, user_id):
    state = get_state(user_id)
    state["step"] = "menu"
    state.pop("form", None)
    save_state(user_id, state)
    lang = get_language(user_id)
    await update.message.reply_text(
        T[lang]["main"],
        reply_markup=main_keyboard(user_id),
    )


def action_for_text(user_id, text):
    t = T[get_language(user_id)]
    mapping = {
        t["buy_req"]: "buy_req",
        t["rent_req"]: "rent_req",
        t["sell_ad"]: "sell_ad",
        t["rent_ad"]: "rent_ad",
        t["prebuy"]: "prebuy",
        t["builder"]: "builder",
        t["owner_build"]: "owner_build",
        t["broker_ad"]: "broker_ad",
    }
    return mapping.get(text)


async def handle_language_change(update, user_id, new_lang):
    set_language(user_id, new_lang)
    state = get_state(user_id)
    t = T[new_lang]

    if state.get("step") == "choose_language":
        state["step"] = "menu"
        state["language_selected"] = True
        save_state(user_id, state)
        await update.message.reply_text(
            t["welcome"],
            parse_mode=ParseMode.HTML,
            reply_markup=main_keyboard(user_id),
        )
        return

    save_state(user_id, state)
    step = state.get("step", "menu")

    if step == "menu":
        await update.message.reply_text(
            t["lang_changed"] + "\n\n" + t["main"],
            reply_markup=main_keyboard(user_id),
        )
    elif step in ("submenu_buyer", "submenu_seller", "submenu_invest",
                  "submenu_broker", "submenu_support"):
        menu = step.replace("submenu_", "")
        await update.message.reply_text(
            t["lang_changed"],
            reply_markup=submenu(user_id, menu),
        )
    elif step in ("property_type", "city", "area", "price", "details", "phone",
                  "support_message", "report_message"):
        await update.message.reply_text(
            t["lang_changed"] + "\n\n" + prompt_for_state(user_id, state),
            reply_markup=keyboard(user_id, [[t["cancel"]]]),
        )
    else:
        await update.message.reply_text(
            t["lang_changed"],
            reply_markup=main_keyboard(user_id),
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    text = update.message.text.strip()
    lang = get_language(user_id)
    t = T[lang]
    state = get_state(user_id)

    # تغییر زبان در هر مرحله، بدون پاک‌کردن مرحله و داده‌های فرم
    selected_lang = language_from_text(text)
    if selected_lang:
        await handle_language_change(update, user_id, selected_lang)
        return

    # دکمه تغییر زبان در تمام صفحه‌ها فعال است.
    if text == t["change"]:
        await update.message.reply_text(
            t["choose_lang"],
            reply_markup=language_keyboard(),
        )
        return

    if text == "/start":
        await start(update, context)
        return

    if text == t["cancel"]:
        save_state(user_id, {"step": "menu", "language_selected": True})
        await update.message.reply_text(
            t["cancelled"],
            reply_markup=main_keyboard(user_id),
        )
        return

    if text == t["back"]:
        await show_main(update, user_id)
        return

    step = state.get("step", "menu")

    # انتخاب زبان برای کاربر تازه
    if step == "choose_language":
        await update.message.reply_text(
            t["choose_lang"],
            reply_markup=language_keyboard(),
        )
        return

    # منوی اصلی
    main_actions = {
        t["buyer"]: ("submenu_buyer", "buyer"),
        t["seller"]: ("submenu_seller", "seller"),
        t["invest"]: ("submenu_invest", "invest"),
        t["broker"]: ("submenu_broker", "broker"),
        t["support"]: ("submenu_support", "support"),
    }
    if step == "menu" and text in main_actions:
        new_step, menu = main_actions[text]
        state["step"] = new_step
        save_state(user_id, state)
        await update.message.reply_text(
            t["main"],
            reply_markup=submenu(user_id, menu),
        )
        return

    # شروع فرم آگهی یا تقاضا
    action = action_for_text(user_id, text)
    if action:
        state["step"] = "property_type"
        state["form"] = {
            "purpose": action,
            "language": lang,
        }
        save_state(user_id, state)
        type_rows = [
            [t["residential"], t["office"]],
            [t["commercial"], t["agricultural"]],
            [t["industrial"]],
            [t["cancel"]],
        ]
        await update.message.reply_text(
            t["property_type"],
            reply_markup=keyboard(user_id, type_rows),
        )
        return

    # گزینه‌های زیرمنوی مشاور و پشتیبانی
    if step.startswith("submenu_"):
        if text == t["leads"] or text == t["cooperate"]:
            await update.message.reply_text(
                t["message_admin"],
                reply_markup=keyboard(user_id, [[t["cancel"]]]),
            )
            state["step"] = "support_message"
            save_state(user_id, state)
            return
        if text == t["message_admin"]:
            state["step"] = "support_message"
            save_state(user_id, state)
            await update.message.reply_text(
                t["message_admin"],
                reply_markup=keyboard(user_id, [[t["cancel"]]]),
            )
            return
        if text == t["report"]:
            state["step"] = "report_message"
            save_state(user_id, state)
            await update.message.reply_text(
                t["report"],
                reply_markup=keyboard(user_id, [[t["cancel"]]]),
            )
            return
        await update.message.reply_text(
            t["unknown"],
            reply_markup=main_keyboard(user_id),
        )
        return

    form = state.get("form", {})

    if step == "property_type":
        type_map = {
            t["residential"]: "residential",
            t["office"]: "office",
            t["commercial"]: "commercial",
            t["agricultural"]: "agricultural",
            t["industrial"]: "industrial",
        }
        if text not in type_map:
            await update.message.reply_text(t["property_type"])
            return
        form["property_type"] = type_map[text]
        state["form"] = form
        state["step"] = "city"
        save_state(user_id, state)
        await update.message.reply_text(
            t["city"],
            reply_markup=keyboard(user_id, [[t["cancel"]]]),
        )
        return

    if step == "city":
        form["city"] = text
        state["form"] = form
        state["step"] = "area"
        save_state(user_id, state)
        await update.message.reply_text(
            t["area"],
            reply_markup=keyboard(user_id, [[t["cancel"]]]),
        )
        return

    if step == "area":
        form["area"] = text
        state["form"] = form
        state["step"] = "price"
        save_state(user_id, state)
        await update.message.reply_text(
            t["price"],
            reply_markup=keyboard(user_id, [[t["cancel"]]]),
        )
        return

    if step == "price":
        form["price"] = text
        state["form"] = form
        state["step"] = "details"
        save_state(user_id, state)
        await update.message.reply_text(
            t["details"],
            reply_markup=keyboard(user_id, [[t["cancel"]]]),
        )
        return

    if step == "details":
        form["details"] = text
        state["form"] = form
        state["step"] = "phone"
        save_state(user_id, state)
        await update.message.reply_text(
            t["phone"],
            reply_markup=keyboard(user_id, [[t["cancel"]]]),
        )
        return

    if step == "phone":
        form["phone"] = text
        form["language"] = lang
        form["user_id"] = user_id

        ad_id = save_ad(user_id, lang, form.get("purpose", "sell_ad"), form)
        await send_admin_review(context, ad_id, user_id, form)

        save_state(user_id, {"step": "menu", "language_selected": True})
        await update.message.reply_text(
            t["submitted"],
            reply_markup=main_keyboard(user_id),
        )
        return

    if step in ("support_message", "report_message"):
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"پیام کاربر\nشناسه: {user_id}\n"
                    f"زبان: {LANG_NAMES[lang]}\n"
                    f"نوع: {step}\n\n{text}"
                ),
            )
            await update.message.reply_text(
                t["request_submitted"],
                reply_markup=main_keyboard(user_id),
            )
        except Exception:
            log.exception("Could not forward user message")
            await update.message.reply_text(t["unknown"])
        save_state(user_id, {"step": "menu", "language_selected": True})
        return

    await update.message.reply_text(
        t["unknown"],
        reply_markup=main_keyboard(user_id),
    )


# ==================== تأیید یا رد توسط مدیر ====================

async def review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer(T["fa"]["admin_only"], show_alert=True)
        return

    try:
        action, ad_id_text = query.data.split(":", 1)
        ad_id = int(ad_id_text)
    except (ValueError, AttributeError):
        return

    row = get_ad(ad_id)
    if not row or row["status"] != "pending":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(T["fa"]["not_found"])
        return

    if action == "reject":
        if not set_ad_status(ad_id, "rejected"):
            await query.message.reply_text(T["fa"]["not_found"])
            return
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(T["fa"]["rejected"])
        try:
            await context.bot.send_message(
                chat_id=row["user_id"],
                text=T[get_language(row["user_id"])]["rejected"],
            )
        except Exception:
            log.exception("Could not notify user about rejection")
        return

    if action == "approve":
        data = json.loads(row["data_json"])
        lang = row["language"]
        channel = CHANNELS.get(lang)

        if not channel:
            await query.message.reply_text("کانال این زبان تنظیم نشده است.")
            return

        # ابتدا تلاش می‌کنیم منتشر کنیم؛ سپس وضعیت تأیید ثبت می‌شود.
        try:
            await context.bot.send_message(
                chat_id=channel,
                text=render_ad(data, lang),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception as exc:
            log.exception("Channel publication failed")
            await query.message.reply_text(
                "انتشار انجام نشد. دسترسی ربات به کانال و مدیر بودن آن را بررسی کن.\n"
                f"خطا: {str(exc)[:300]}"
            )
            return

        if not set_ad_status(ad_id, "approved"):
            await query.message.reply_text(T["fa"]["not_found"])
            return

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(T["fa"]["approved"])
        try:
            await context.bot.send_message(
                chat_id=row["user_id"],
                text=T[get_language(row["user_id"])]["approved"],
            )
        except Exception:
            log.exception("Could not notify user about approval")


# ==================== صفحه وضعیت ساده برای Render ====================

web_app = Flask(__name__)


@web_app.get("/")
def health():
    return "Tehran Real Estate Bot is running.", 200


def run_web():
    port = int(os.getenv("PORT", "10000"))
    web_app.run(host="0.0.0.0", port=port)


# ==================== اجرای برنامه ====================

def main():
    if not BOT_TOKEN:
        raise RuntimeError("متغیر محیطی BOT_TOKEN تنظیم نشده است.")

    init_db()

    Thread(target=run_web, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(review_callback, pattern=r"^(approve|reject):\d+$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    log.info("Bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
