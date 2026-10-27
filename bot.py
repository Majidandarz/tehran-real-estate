import os
import json
import sqlite3
import logging
from datetime import datetime

from flask import Flask
from threading import Thread

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# =========================================================
# تنظیمات اصلی
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

ADMIN_ID = int(os.getenv("ADMIN_ID", "6245308636"))

CHANNEL_ID = os.getenv("CHANNEL_ID", "@tehranrealstate")

DB_PATH = os.getenv("DB_PATH", "realestate.db")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# =========================================================
# زبان‌ها
# =========================================================

LANGUAGES = {
    "fa": "🇮🇷 فارسی",
    "en": "🇬🇧 English",
    "az": "🇦🇿 Azərbaycan dili",
    "tr": "🇹🇷 Türkçe",
    "ar": "🇸🇦 العربية",
}

LANGUAGE_BUTTONS = {
    "fa": "🇮🇷 فارسی",
    "en": "🇬🇧 English",
    "az": "🇦🇿 Azərbaycan dili",
    "tr": "🇹🇷 Türkçe",
    "ar": "🇸🇦 العربية",
}

# =========================================================
# پیام خوش‌آمدگویی پنج‌زبانه
# =========================================================

WELCOME = {
    "fa": (
        "🏡✨ به گروه بزرگ املاک تهران خوش آمدید! ✨🏡\n\n"
        "🌟 مجموعه املاک تهران با بیش از ۲۰ سال سابقه فعالیت، "
        "گسترده‌ترین شبکه اطلاعات ملکی در ایران و بیش از "
        "۱۰۰۰ مشاور فعال در سراسر کشور، در کنار شماست.\n\n"
        "🔑 خرید و فروش ملک | 🏢 اجاره | 💎 سرمایه‌گذاری ملکی\n\n"
        "🤝 هدف پرسنل و مدیریت مجموعه، جلب رضایت شما مشتریان عزیز "
        "و ارائه خدماتی شایسته، مطمئن و حرفه‌ای است.\n\n"
        "🌹 امیدواریم تجربه‌ای رضایت‌بخش و همکاری ارزشمندی را "
        "در کنار ما داشته باشید.\n\n"
        "💠 املاک تهران؛ همراه شما در مسیر انتخابی مطمئن. 💠"
    ),
    "en": (
        "🏡✨ Welcome to Tehran Real Estate! ✨🏡\n\n"
        "🌟 With over 20 years of experience, an extensive "
        "property information network across Iran, and more than "
        "1,000 active real estate consultants nationwide, "
        "Tehran Real Estate is here to assist you.\n\n"
        "🔑 Buying & Selling | 🏢 Renting | 💎 Property Investment\n\n"
        "🤝 Our team and management are committed to customer "
        "satisfaction and providing professional, reliable services.\n\n"
        "🌹 We look forward to providing you with a valuable "
        "and satisfying experience.\n\n"
        "💠 Tehran Real Estate — Your partner in making "
        "confident property decisions. 💠"
    ),
    "az": (
        "🏡✨ Tehran Əmlakın böyük ailəsinə xoş gəlmisiniz! ✨🏡\n\n"
        "🌟 20 ildən artıq təcrübəsi, İran üzrə geniş əmlak "
        "məlumat şəbəkəsi və ölkə üzrə 1.000-dən çox fəal "
        "əmlak məsləhətçisi ilə Tehran Əmlak xidmətinizdədir.\n\n"
        "🔑 Alış və Satış | 🏢 İcarə | 💎 Əmlak İnvestisiyası\n\n"
        "🤝 Komandamız və rəhbərliyimiz müştəri məmnuniyyətini "
        "və etibarlı, peşəkar xidmət göstərilməsini əsas məqsəd sayır.\n\n"
        "🌹 Sizə məmnunedici və dəyərli təcrübə arzulayırıq.\n\n"
        "💠 Tehran Əmlak — düzgün seçim yolunda sizin tərəfdaşınız. 💠"
    ),
    "tr": (
        "🏡✨ Büyük Tehran Emlak ailesine hoş geldiniz! ✨🏡\n\n"
        "🌟 20 yılı aşkın deneyimi, İran genelindeki geniş "
        "gayrimenkul bilgi ağı ve ülke çapında 1.000'den fazla "
        "aktif danışmanıyla Tehran Emlak yanınızda.\n\n"
        "🔑 Alım Satım | 🏢 Kiralama | 💎 Gayrimenkul Yatırımı\n\n"
        "🤝 Ekibimizin ve yönetimimizin temel hedefi, "
        "müşteri memnuniyetini sağlamak ve güvenilir, profesyonel "
        "hizmet sunmaktır.\n\n"
        "🌹 Bizimle memnuniyet verici ve değerli bir deneyim "
        "yaşamanızı dileriz.\n\n"
        "💠 Tehran Emlak — Güvenli seçimlerinizde yanınızda. 💠"
    ),
    "ar": (
        "🏡✨ أهلاً وسهلاً بكم في مجموعة طهران العقارية الكبرى! ✨🏡\n\n"
        "🌟 بخبرة تزيد على 20 عاماً، وشبكة واسعة من المعلومات "
        "العقارية في إيران، وأكثر من 1,000 مستشار عقاري نشط "
        "في جميع أنحاء البلاد، نحن هنا لخدمتكم.\n\n"
        "🔑 شراء وبيع العقارات | 🏢 الإيجار | 💎 الاستثمار العقاري\n\n"
        "🤝 يسعى فريق العمل والإدارة إلى تحقيق رضا عملائنا الكرام "
        "وتقديم خدمات احترافية وموثوقة.\n\n"
        "🌹 نتمنى لكم تجربة مميزة ومرضية وتعاوناً مثمراً معنا.\n\n"
        "💠 طهران العقارية — شريككم نحو اختيار عقاري موثوق. 💠"
    ),
}

# =========================================================
# متن منوها و پیام‌ها
# =========================================================

TEXT = {
    "fa": {
        "choose_language": "🌐 لطفاً زبان موردنظر خود را انتخاب کنید:",
        "language_saved": "✅ زبان شما ذخیره شد.",
        "main_menu": "🏡 منوی اصلی املاک تهران\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        "buyer": "🔎 متقاضی خرید یا اجاره",
        "seller": "🏠 فروشنده یا موجر",
        "investment": "💎 سرمایه‌گذاری ملکی و مشارکت در ساخت",
        "agent": "🤝 مشاور املاک",
        "support": "📞 پشتیبانی و ارتباط با مدیر",
        "back": "🔙 بازگشت به منوی اصلی",
        "buy_request": "🔑 ثبت تقاضای خرید",
        "rent_request": "🏢 ثبت تقاضای اجاره",
        "sell_ad": "🏠 ثبت آگهی فروش",
        "rent_ad": "🔑 ثبت آگهی اجاره",
        "presale": "🏗 درخواست پیش‌خرید",
        "builder": "🏗 سازنده آماده مشارکت هستم",
        "owner_partner": "🏡 مالک ملک برای مشارکت در ساخت هستم",
        "agent_ads": "📝 ثبت آگهی ملک",
        "agent_customers": "👥 پیگیری مشتریان",
        "agent_cooperation": "🤝 درخواست همکاری با مشاوران",
        "contact_admin": "✉️ ارسال پیام به مدیر",
        "report": "🚨 گزارش مشکل یا تخلف",
        "types_title": "🏘 لطفاً نوع ملک را انتخاب کنید:",
        "residential": "🏡 مسکونی",
        "office": "🏢 اداری",
        "commercial": "🏬 تجاری",
        "agricultural": "🌾 زراعی",
        "industrial": "🏭 صنعتی",
        "ask_details": "📝 لطفاً اطلاعات ملک یا درخواست خود را در یک پیام ارسال کنید.\n\nبرای مثال: شهر، منطقه، متراژ، بودجه و توضیحات.",
        "ask_message": "✍️ لطفاً پیام خود را برای مدیر بنویسید:",
        "submitted": "✅ اطلاعات شما ثبت شد و برای بررسی ارسال گردید.",
        "admin_new": "📩 درخواست جدید از املاک تهران\n\nشناسه کاربر: {user_id}\nنام: {name}\nنوع درخواست: {kind}\nنوع ملک: {property_type}\n\nاطلاعات:\n{details}",
        "admin_message": "✉️ پیام جدید برای مدیر\n\nشناسه کاربر: {user_id}\nنام: {name}\n\n{details}",
        "admin_approved": "✅ آگهی شما تأیید و منتشر شد.",
        "admin_rejected": "❌ آگهی شما تأیید نشد. لطفاً برای بررسی بیشتر با پشتیبانی تماس بگیرید.",
        "not_admin": "⛔ این دستور فقط برای مدیر ربات فعال است.",
        "admin_commands": "دستورات مدیر:\n/requests - مشاهده درخواست‌های در انتظار\n",
        "pending_empty": "درخواست در انتظار بررسی وجود ندارد.",
        "unknown": "لطفاً از گزینه‌های منو استفاده کنید.",
        "cancel": "❌ عملیات لغو شد.",
        "admin_approve": "✅ تأیید",
        "admin_reject": "❌ رد",
        "approval_done": "عملیات انجام شد.",
        "ad_caption": "🏡 آگهی جدید املاک تهران\n\n{details}\n\n📞 برای اطلاعات بیشتر از طریق ربات اقدام کنید.",
    },
    "en": {
        "choose_language": "🌐 Please select your language:",
        "language_saved": "✅ Your language has been saved.",
        "main_menu": "🏡 Tehran Real Estate Main Menu\n\nPlease choose an option:",
        "buyer": "🔎 Buyer or Tenant",
        "seller": "🏠 Seller or Landlord",
        "investment": "💎 Property Investment & Development Partnership",
        "agent": "🤝 Real Estate Agent",
        "support": "📞 Support & Contact Management",
        "back": "🔙 Back to Main Menu",
        "buy_request": "🔑 Submit Purchase Request",
        "rent_request": "🏢 Submit Rental Request",
        "sell_ad": "🏠 Submit Property for Sale",
        "rent_ad": "🔑 Submit Property for Rent",
        "presale": "🏗 Pre-purchase Request",
        "builder": "🏗 I Am a Developer Seeking a Partnership",
        "owner_partner": "🏡 I Own Property for Development Partnership",
        "agent_ads": "📝 Submit Property Listing",
        "agent_customers": "👥 Manage Customer Leads",
        "agent_cooperation": "🤝 Request Cooperation with Agents",
        "contact_admin": "✉️ Message Management",
        "report": "🚨 Report a Problem or Violation",
        "types_title": "🏘 Please select the property type:",
        "residential": "🏡 Residential",
        "office": "🏢 Office",
        "commercial": "🏬 Commercial",
        "agricultural": "🌾 Agricultural",
        "industrial": "🏭 Industrial",
        "ask_details": "📝 Please send the property details or your request in one message.\n\nFor example: city, area, size, budget and description.",
        "ask_message": "✍️ Please write your message to management:",
        "submitted": "✅ Your information has been submitted for review.",
        "admin_new": "📩 New Request\n\nUser ID: {user_id}\nName: {name}\nRequest: {kind}\nProperty Type: {property_type}\n\nDetails:\n{details}",
        "admin_message": "✉️ New Message for Management\n\nUser ID: {user_id}\nName: {name}\n\n{details}",
        "admin_approved": "✅ Your listing has been approved and published.",
        "admin_rejected": "❌ Your listing was not approved. Please contact support.",
        "not_admin": "⛔ This command is for the bot administrator only.",
        "admin_commands": "Admin commands:\n/requests - View pending requests\n",
        "pending_empty": "There are no pending requests.",
        "unknown": "Please use the menu buttons.",
        "cancel": "❌ Operation cancelled.",
        "admin_approve": "✅ Approve",
        "admin_reject": "❌ Reject",
        "approval_done": "Action completed.",
        "ad_caption": "🏡 New Tehran Real Estate Listing\n\n{details}\n\n📞 Contact us through the bot for more information.",
    },
    "az": {
        "choose_language": "🌐 Zəhmət olmasa dilinizi seçin:",
        "language_saved": "✅ Diliniz yadda saxlanıldı.",
        "main_menu": "🏡 Tehran Əmlak — Əsas menyu\n\nZəhmət olmasa seçim edin:",
        "buyer": "🔎 Alıcı və ya Kirayəçi",
        "seller": "🏠 Satıcı və ya İcarəyə Verən",
        "investment": "💎 Əmlak İnvestisiyası və Tikinti Əməkdaşlığı",
        "agent": "🤝 Əmlak Məsləhətçisi",
        "support": "📞 Dəstək və Rəhbərliklə Əlaqə",
        "back": "🔙 Əsas menyuya qayıt",
        "buy_request": "🔑 Alış tələbi yarat",
        "rent_request": "🏢 İcarə tələbi yarat",
        "sell_ad": "🏠 Satış elanı yerləşdir",
        "rent_ad": "🔑 İcarə elanı yerləşdir",
        "presale": "🏗 İlkin alış müraciəti",
        "builder": "🏗 Əməkdaşlıq axtaran tikinti şirkətiyəm",
        "owner_partner": "🏡 Tikinti əməkdaşlığı üçün əmlak sahibiyəm",
        "agent_ads": "📝 Əmlak elanı yerləşdir",
        "agent_customers": "👥 Müştəriləri izləmək",
        "agent_cooperation": "🤝 Məsləhətçilərlə əməkdaşlıq",
        "contact_admin": "✉️ Rəhbərliyə mesaj göndər",
        "report": "🚨 Problem və ya pozuntu bildir",
        "types_title": "🏘 Əmlak növünü seçin:",
        "residential": "🏡 Yaşayış",
        "office": "🏢 Ofis",
        "commercial": "🏬 Kommersiya",
        "agricultural": "🌾 Kənd təsərrüfatı",
        "industrial": "🏭 Sənaye",
        "ask_details": "📝 Əmlak və ya müraciət məlumatlarını bir mesajda göndərin.\n\nMəsələn: şəhər, ərazi, sahə, büdcə və açıqlama.",
        "ask_message": "✍️ Rəhbərliyə mesajınızı yazın:",
        "submitted": "✅ Məlumatınız yoxlanılması üçün göndərildi.",
        "admin_new": "📩 Yeni müraciət\n\nİstifadəçi ID: {user_id}\nAd: {name}\nMüraciət: {kind}\nƏmlak növü: {property_type}\n\nMəlumat:\n{details}",
        "admin_message": "✉️ Rəhbərlik üçün yeni mesaj\n\nİstifadəçi ID: {user_id}\nAd: {name}\n\n{details}",
        "admin_approved": "✅ Elanınız təsdiqləndi və yayımlandı.",
        "admin_rejected": "❌ Elanınız təsdiqlənmədi. Dəstək xidməti ilə əlaqə saxlayın.",
        "not_admin": "⛔ Bu əmr yalnız bot rəhbəri üçündür.",
        "admin_commands": "Rəhbər əmrləri:\n/requests - Gözləyən müraciətlər\n",
        "pending_empty": "Yoxlanılmağı gözləyən müraciət yoxdur.",
        "unknown": "Zəhmət olmasa menyu düymələrindən istifadə edin.",
        "cancel": "❌ Əməliyyat ləğv edildi.",
        "admin_approve": "✅ Təsdiq et",
        "admin_reject": "❌ Rədd et",
        "approval_done": "Əməliyyat tamamlandı.",
        "ad_caption": "🏡 Yeni Tehran Əmlak elanı\n\n{details}\n\n📞 Ətraflı məlumat üçün botla əlaqə saxlayın.",
    },
    "tr": {
        "choose_language": "🌐 Lütfen dilinizi seçin:",
        "language_saved": "✅ Diliniz kaydedildi.",
        "main_menu": "🏡 Tehran Emlak Ana Menü\n\nLütfen bir seçenek belirleyin:",
        "buyer": "🔎 Alıcı veya Kiracı",
        "seller": "🏠 Satıcı veya Kiraya Veren",
        "investment": "💎 Gayrimenkul Yatırımı ve İnşaat Ortaklığı",
        "agent": "🤝 Emlak Danışmanı",
        "support": "📞 Destek ve Yönetimle İletişim",
        "back": "🔙 Ana Menüye Dön",
        "buy_request": "🔑 Satın Alma Talebi Oluştur",
        "rent_request": "🏢 Kiralama Talebi Oluştur",
        "sell_ad": "🏠 Satılık İlanı Ver",
        "rent_ad": "🔑 Kiralık İlanı Ver",
        "presale": "🏗 Ön Satın Alma Talebi",
        "builder": "🏗 Ortaklık Arayan İnşaat Firmasıyım",
        "owner_partner": "🏡 İnşaat Ortaklığı İçin Mülk Sahibiyim",
        "agent_ads": "📝 Emlak İlanı Ver",
        "agent_customers": "👥 Müşteri Takibi",
        "agent_cooperation": "🤝 Danışmanlarla İş Birliği Talebi",
        "contact_admin": "✉️ Yönetime Mesaj Gönder",
        "report": "🚨 Sorun veya İhlal Bildir",
        "types_title": "🏘 Lütfen mülk türünü seçin:",
        "residential": "🏡 Konut",
        "office": "🏢 Ofis",
        "commercial": "🏬 Ticari",
        "agricultural": "🌾 Tarımsal",
        "industrial": "🏭 Endüstriyel",
        "ask_details": "📝 Lütfen mülk bilgilerinizi veya talebinizi tek mesajla gönderin.\n\nÖrnek: şehir, bölge, metrekare, bütçe ve açıklama.",
        "ask_message": "✍️ Lütfen yönetime mesajınızı yazın:",
        "submitted": "✅ Bilgileriniz incelenmek üzere gönderildi.",
        "admin_new": "📩 Yeni Talep\n\nKullanıcı ID: {user_id}\nAd: {name}\nTalep: {kind}\nMülk Türü: {property_type}\n\nBilgiler:\n{details}",
        "admin_message": "✉️ Yönetime Yeni Mesaj\n\nKullanıcı ID: {user_id}\nAd: {name}\n\n{details}",
        "admin_approved": "✅ İlanınız onaylandı ve yayımlandı.",
        "admin_rejected": "❌ İlanınız onaylanmadı. Lütfen destekle iletişime geçin.",
        "not_admin": "⛔ Bu komut yalnızca bot yöneticisi içindir.",
        "admin_commands": "Yönetici komutları:\n/requests - Bekleyen talepler\n",
        "pending_empty": "İncelenmeyi bekleyen talep yok.",
        "unknown": "Lütfen menü düğmelerini kullanın.",
        "cancel": "❌ İşlem iptal edildi.",
        "admin_approve": "✅ Onayla",
        "admin_reject": "❌ Reddet",
        "approval_done": "İşlem tamamlandı.",
        "ad_caption": "🏡 Yeni Tehran Emlak İlanı\n\n{details}\n\n📞 Ayrıntılar için bot üzerinden iletişime geçin.",
    },
    "ar": {
        "choose_language": "🌐 يرجى اختيار لغتك:",
        "language_saved": "✅ تم حفظ لغتك.",
        "main_menu": "🏡 القائمة الرئيسية — طهران العقارية\n\nيرجى اختيار أحد الخيارات:",
        "buyer": "🔎 مشتري أو مستأجر",
        "seller": "🏠 بائع أو مؤجّر",
        "investment": "💎 الاستثمار العقاري والشراكة في البناء",
        "agent": "🤝 مستشار عقاري",
        "support": "📞 الدعم والتواصل مع الإدارة",
        "back": "🔙 العودة إلى القائمة الرئيسية",
        "buy_request": "🔑 تسجيل طلب شراء",
        "rent_request": "🏢 تسجيل طلب إيجار",
        "sell_ad": "🏠 نشر إعلان بيع",
        "rent_ad": "🔑 نشر إعلان إيجار",
        "presale": "🏗 طلب شراء مسبق",
        "builder": "🏗 أنا مطوّر عقاري وأبحث عن شراكة",
        "owner_partner": "🏡 أملك عقاراً للشراكة في البناء",
        "agent_ads": "📝 نشر إعلان عقاري",
        "agent_customers": "👥 متابعة العملاء",
        "agent_cooperation": "🤝 طلب التعاون مع المستشارين",
        "contact_admin": "✉️ إرسال رسالة إلى الإدارة",
        "report": "🚨 الإبلاغ عن مشكلة أو مخالفة",
        "types_title": "🏘 يرجى اختيار نوع العقار:",
        "residential": "🏡 سكني",
        "office": "🏢 إداري",
        "commercial": "🏬 تجاري",
        "agricultural": "🌾 زراعي",
        "industrial": "🏭 صناعي",
        "ask_details": "📝 يرجى إرسال تفاصيل العقار أو طلبك في رسالة واحدة.\n\nمثال: المدينة، المنطقة، المساحة، الميزانية والتفاصيل.",
        "ask_message": "✍️ يرجى كتابة رسالتك إلى الإدارة:",
        "submitted": "✅ تم إرسال معلوماتك للمراجعة.",
        "admin_new": "📩 طلب جديد\n\nمعرّف المستخدم: {user_id}\nالاسم: {name}\nنوع الطلب: {kind}\nنوع العقار: {property_type}\n\nالتفاصيل:\n{details}",
        "admin_message": "✉️ رسالة جديدة للإدارة\n\nمعرّف المستخدم: {user_id}\nالاسم: {name}\n\n{details}",
        "admin_approved": "✅ تمت الموافقة على إعلانك ونشره.",
        "admin_rejected": "❌ لم تتم الموافقة على إعلانك. يرجى التواصل مع الدعم.",
        "not_admin": "⛔ هذا الأمر مخصص لمدير الروبوت فقط.",
        "admin_commands": "أوامر المدير:\n/requests - الطلبات قيد المراجعة\n",
        "pending_empty": "لا توجد طلبات قيد المراجعة.",
        "unknown": "يرجى استخدام أزرار القائمة.",
        "cancel": "❌ تم إلغاء العملية.",
        "admin_approve": "✅ موافقة",
        "admin_reject": "❌ رفض",
        "approval_done": "تم تنفيذ العملية.",
        "ad_caption": "🏡 إعلان عقاري جديد من طهران العقارية\n\n{details}\n\n📞 تواصلوا معنا عبر الروبوت لمزيد من المعلومات.",
    },
}

# =========================================================
# منوها
# =========================================================

MAIN_MENU_KEYS = [
    "buyer",
    "seller",
    "investment",
    "agent",
    "support",
]

SUBMENU_KEYS = {
    "buyer": ["buy_request", "rent_request"],
    "seller": ["sell_ad", "rent_ad"],
    "investment": ["presale", "builder", "owner_partner"],
    "agent": ["agent_ads", "agent_customers", "agent_cooperation"],
    "support": ["contact_admin", "report"],
}

PROPERTY_TYPES = [
    "residential",
    "office",
    "commercial",
    "agricultural",
    "industrial",
]

# وضعیت‌های گفت‌وگو
LANGUAGE, PROPERTY_TYPE, DETAILS = range(3)

# =========================================================
# دیتابیس
# =========================================================

def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db_connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'fa',
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT,
                language TEXT NOT NULL,
                kind TEXT NOT NULL,
                property_type TEXT,
                details TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)


def get_user_language(user_id):
    with db_connect() as conn:
        row = conn.execute(
            "SELECT language FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    return row["language"] if row else None


def save_user_language(user_id, language):
    with db_connect() as conn:
        conn.execute("""
            INSERT INTO users (user_id, language, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET language = excluded.language
        """, (user_id, language, datetime.utcnow().isoformat()))


def save_request(user_id, name, language, kind, property_type, details):
    with db_connect() as conn:
        cursor = conn.execute("""
            INSERT INTO requests
            (user_id, name, language, kind, property_type, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            name,
            language,
            kind,
            property_type,
            details,
            datetime.utcnow().isoformat(),
        ))

        return cursor.lastrowid


def get_request(request_id):
    with db_connect() as conn:
        return conn.execute(
            "SELECT * FROM requests WHERE id = ?",
            (request_id,),
        ).fetchone()


def get_pending_requests():
    with db_connect() as conn:
        return conn.execute("""
            SELECT * FROM requests
            WHERE status = 'pending'
            ORDER BY id ASC
            LIMIT 20
        """).fetchall()


def set_request_status(request_id, status):
    with db_connect() as conn:
        conn.execute(
            "UPDATE requests SET status = ? WHERE id = ?",
            (status, request_id),
        )


# =========================================================
# ابزارهای منو
# =========================================================

def tr(language, key):
    language = language if language in TEXT else "fa"
    return TEXT[language].get(key, TEXT["fa"].get(key, key))


def make_keyboard(language, rows):
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        is_persistent=True,
    )


def main_keyboard(language):
    t = TEXT[language]
    return make_keyboard(language, [
        [t["buyer"]],
        [t["seller"]],
        [t["investment"]],
        [t["agent"]],
        [t["support"]],
    ])


def back_keyboard(language):
    return make_keyboard(language, [[TEXT[language]["back"]]])


def language_keyboard():
    return make_keyboard("fa", [
        [LANGUAGE_BUTTONS["fa"], LANGUAGE_BUTTONS["en"]],
        [LANGUAGE_BUTTONS["az"], LANGUAGE_BUTTONS["tr"]],
        [LANGUAGE_BUTTONS["ar"]],
    ])


def language_from_button(text):
    for code, label in LANGUAGE_BUTTONS.items():
        if text == label:
            return code
    return None


def key_from_button(language, text, keys):
    for key in keys:
        if TEXT[language].get(key) == text:
            return key
    return None


def main_menu_key(language, text):
    return key_from_button(language, text, MAIN_MENU_KEYS)


def submenu_key(language, section, text):
    return key_from_button(language, text, SUBMENU_KEYS[section])


def property_type_key(language, text):
    return key_from_button(language, text, PROPERTY_TYPES)


def submenu_keyboard(language, section):
    t = TEXT[language]
    rows = [[t[key]] for key in SUBMENU_KEYS[section]]
    rows.append([t["back"]])
    return make_keyboard(language, rows)


def property_keyboard(language):
    t = TEXT[language]
    rows = [[t[key]] for key in PROPERTY_TYPES]
    rows.append([t["back"]])
    return make_keyboard(language, rows)


# =========================================================
# شروع و انتخاب زبان
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return ConversationHandler.END

    context.user_data.clear()

    language = get_user_language(user.id)

    if language:
        await update.message.reply_text(
            TEXT[language]["main_menu"],
            reply_markup=main_keyboard(language),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        TEXT["fa"]["choose_language"],
        reply_markup=language_keyboard(),
    )
    return LANGUAGE


async def choose_language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return LANGUAGE

    language = language_from_button(update.message.text)

    if not language:
        await update.message.reply_text(
            TEXT["fa"]["choose_language"],
            reply_markup=language_keyboard(),
        )
        return LANGUAGE

    user = update.effective_user
    save_user_language(user.id, language)

    await update.message.reply_text(
        WELCOME[language],
        reply_markup=ReplyKeyboardRemove(),
    )

    await update.message.reply_text(
        TEXT[language]["main_menu"],
        reply_markup=main_keyboard(language),
    )

    return ConversationHandler.END


async def change_language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    await update.message.reply_text(
        TEXT["fa"]["choose_language"],
        reply_markup=language_keyboard(),
    )
    return LANGUAGE


# =========================================================
# شروع فرم درخواست یا آگهی
# =========================================================

async def begin_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    kind: str,
):
    user = update.effective_user
    language = get_user_language(user.id) or "fa"

    context.user_data["kind"] = kind
    context.user_data["language"] = language
    context.user_data["property_type"] = None

    await update.message.reply_text(
        tr(language, "types_title"),
        reply_markup=property_keyboard(language),
    )

    return PROPERTY_TYPE


async def select_property_type(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    language = context.user_data.get(
        "language",
        get_user_language(user.id) or "fa",
    )

    if update.message.text == TEXT[language]["back"]:
        await update.message.reply_text(
            TEXT[language]["main_menu"],
            reply_markup=main_keyboard(language),
        )
        context.user_data.clear()
        return ConversationHandler.END

    property_type = property_type_key(language, update.message.text)

    if not property_type:
        await update.message.reply_text(
            TEXT[language]["types_title"],
            reply_markup=property_keyboard(language),
        )
        return PROPERTY_TYPE

    context.user_data["property_type"] = property_type

    await update.message.reply_text(
        TEXT[language]["ask_details"],
        reply_markup=back_keyboard(language),
    )

    return DETAILS


async def receive_details(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    language = context.user_data.get(
        "language",
        get_user_language(user.id) or "fa",
    )

    if update.message.text == TEXT[language]["back"]:
        await update.message.reply_text(
            TEXT[language]["main_menu"],
            reply_markup=main_keyboard(language),
        )
        context.user_data.clear()
        return ConversationHandler.END

    details = update.message.text or ""

    if len(details.strip()) < 3:
        await update.message.reply_text(TEXT[language]["ask_details"])
        return DETAILS

    kind = context.user_data.get("kind", "request")
    property_type = context.user_data.get("property_type", "")
    name = user.full_name or ""

    request_id = save_request(
        user_id=user.id,
        name=name,
        language=language,
        kind=kind,
        property_type=property_type,
        details=details,
    )

    admin_text = TEXT["fa"]["admin_new"].format(
        user_id=user.id,
        name=name,
        kind=kind,
        property_type=TEXT["fa"].get(property_type, property_type),
        details=details,
    )

    keyboard = [
        [
            # شناسه درخواست در callback ذخیره می‌شود
            # و فقط مدیر می‌تواند تصمیم بگیرد.
        ]
    ]

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    admin_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                TEXT["fa"]["admin_approve"],
                callback_data=f"approve:{request_id}",
            ),
            InlineKeyboardButton(
                TEXT["fa"]["admin_reject"],
                callback_data=f"reject:{request_id}",
            ),
        ]
    ])

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=admin_keyboard,
        )
    except Exception:
        logger.exception("Could not notify administrator")

    await update.message.reply_text(
        TEXT[language]["submitted"],
        reply_markup=main_keyboard(language),
    )

    context.user_data.clear()
    return ConversationHandler.END


# =========================================================
# ارسال پیام به مدیر
# =========================================================

async def begin_admin_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    language = get_user_language(user.id) or "fa"

    context.user_data["kind"] = "admin_message"
    context.user_data["language"] = language
    context.user_data["property_type"] = ""

    await update.message.reply_text(
        TEXT[language]["ask_message"],
        reply_markup=back_keyboard(language),
    )

    return DETAILS


# =========================================================
# مدیریت منوی اصلی
# =========================================================

async def handle_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    language = get_user_language(user.id) or "fa"
    text = update.message.text
    t = TEXT[language]

    if text == t["back"]:
        context.user_data.clear()
        await update.message.reply_text(
            t["main_menu"],
            reply_markup=main_keyboard(language),
        )
        return

    section = main_menu_key(language, text)

    if section:
        context.user_data["section"] = section

        await update.message.reply_text(
            t["main_menu"],
            reply_markup=submenu_keyboard(language, section),
        )
        return

    section = context.user_data.get("section")

    if section:
        action = submenu_key(language, section, text)

        if action:
            if action in ("buy_request", "rent_request"):
                await begin_request(update, context, action)
                return

            if action in ("sell_ad", "rent_ad", "agent_ads"):
                await begin_request(update, context, action)
                return

            if action in ("presale", "builder", "owner_partner"):
                await begin_request(update, context, action)
                return

            if action == "contact_admin":
                await begin_admin_message(update, context)
                return

            if action == "report":
                await begin_request(update, context, "report")
                return

            if action in ("agent_customers", "agent_cooperation"):
                await update.message.reply_text(
                    t["ask_details"],
                    reply_markup=back_keyboard(language),
                )
                context.user_data["kind"] = action
                context.user_data["property_type"] = ""
                return

    await update.message.reply_text(
        t["unknown"],
        reply_markup=main_keyboard(language),
    )


# =========================================================
# تأیید یا رد توسط مدیر
# =========================================================

async def admin_decision(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    if not query:
        return

    user = update.effective_user

    if user.id != ADMIN_ID:
        await query.answer("Not authorized", show_alert=True)
        return

    await query.answer()

    try:
        action, request_id_text = query.data.split(":", 1)
        request_id = int(request_id_text)
    except (ValueError, AttributeError):
        await query.edit_message_text("Invalid request.")
        return

    row = get_request(request_id)

    if not row or row["status"] != "pending":
        await query.edit_message_text("This request has already been processed.")
        return

    language = row["language"]

    if action == "approve":
        set_request_status(request_id, "approved")

        try:
            await context.bot.send_message(
                chat_id=row["user_id"],
                text=TEXT[language]["admin_approved"],
            )
        except Exception:
            logger.exception("Could not notify user")

        # فقط آگهی‌ها در کانال منتشر می‌شوند؛ درخواست خرید/اجاره منتشر نمی‌شود.
        publishable = row["kind"] in (
            "sell_ad",
            "rent_ad",
            "agent_ads",
        )

        if publishable:
            try:
                caption = TEXT["fa"]["ad_caption"].format(
                    details=row["details"]
                )
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=caption,
                )
            except Exception:
                logger.exception("Could not publish listing")

        await query.edit_message_text(
            f"✅ درخواست شماره {request_id} تأیید شد."
        )

    elif action == "reject":
        set_request_status(request_id, "rejected")

        try:
            await context.bot.send_message(
                chat_id=row["user_id"],
                text=TEXT[language]["admin_rejected"],
            )
        except Exception:
            logger.exception("Could not notify user")

        await query.edit_message_text(
            f"❌ درخواست شماره {request_id} رد شد."
        )


# =========================================================
# دستورات مدیر
# =========================================================

async def admin_requests(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    if user.id != ADMIN_ID:
        language = get_user_language(user.id) or "fa"
        await update.message.reply_text(TEXT[language]["not_admin"])
        return

    rows = get_pending_requests()

    if not rows:
        await update.message.reply_text(TEXT["fa"]["pending_empty"])
        return

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    for row in rows:
        message = TEXT["fa"]["admin_new"].format(
            user_id=row["user_id"],
            name=row["name"] or "",
            kind=row["kind"],
            property_type=row["property_type"] or "",
            details=row["details"],
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    TEXT["fa"]["admin_approve"],
                    callback_data=f"approve:{row['id']}",
                ),
                InlineKeyboardButton(
                    TEXT["fa"]["admin_reject"],
                    callback_data=f"reject:{row['id']}",
                ),
            ]
        ])

        await update.message.reply_text(
            message,
            reply_markup=keyboard,
        )


async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    user = update.effective_user
    language = get_user_language(user.id) or "fa"

    await update.message.reply_text(
        TEXT[language]["cancel"],
        reply_markup=main_keyboard(language),
    )

    return ConversationHandler.END


# =========================================================
# وب‌سرور ساده برای Render
# =========================================================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Tehran Real Estate Bot is running.", 200


@web_app.route("/health")
def health():
    return {"status": "ok"}, 200


def run_web_server():
    port = int(os.getenv("PORT", "10000"))
    web_app.run(
        host="0.0.0.0",
        port=port,
        use_reloader=False,
    )


# =========================================================
# اجرای ربات
# =========================================================

def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing. Set BOT_TOKEN in Render Environment."
        )

    init_db()

    Thread(
        target=run_web_server,
        daemon=True,
    ).start()

    application = Application.builder().token(BOT_TOKEN).build()

    language_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("language", change_language),
        ],
        states={
            LANGUAGE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    choose_language,
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,
    )

    request_conversation = ConversationHandler(
        entry_points=[],
        states={
            PROPERTY_TYPE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    select_property_type,
                )
            ],
            DETAILS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_details,
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,
    )

    application.add_handler(language_conversation)
    application.add_handler(request_conversation)

    application.add_handler(CommandHandler("requests", admin_requests))
    application.add_handler(CommandHandler("cancel", cancel))

    from telegram.ext import CallbackQueryHandler
    application.add_handler(
        CallbackQueryHandler(admin_decision, pattern=r"^(approve|reject):\d+$")
    )

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu)
    )

    logger.info("Tehran Real Estate Bot started.")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
