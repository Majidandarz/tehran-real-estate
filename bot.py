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

LANGUAGES = {
    "fa": "فارسی",
    "en": "English",
    "az": "Azərbaycan dili",
    "tr": "Türkçe",
    "ar": "العربية",
}

BACK = {
    "fa": "بازگشت به منوی اصلی",
    "en": "Back to main menu",
    "az": "Əsas menyuya qayıt",
    "tr": "Ana menüye dön",
    "ar": "العودة إلى القائمة الرئيسية",
}

CHANGE_LANGUAGE = {
    "fa": "تغییر زبان",
    "en": "Change language",
    "az": "Dili dəyiş",
    "tr": "Dili değiştir",
    "ar": "تغيير اللغة",
}

MAIN_MENU = {
    "fa": [
        "متقاضی خرید یا اجاره",
        "فروشنده یا موجر",
        "سرمایه‌گذاری ملکی و مشارکت در ساخت",
        "مشاور املاک",
        "پشتیبانی و ارتباط با مدیر",
    ],
    "en": [
        "Buy or rent request",
        "Seller or landlord",
        "Property investment and construction partnership",
        "Real estate agent",
        "Support and contact admin",
    ],
    "az": [
        "Alış və ya kirayə müraciəti",
        "Satıcı və ya kirayə verən",
        "Əmlak investisiyası və tikinti tərəfdaşlığı",
        "Əmlak agenti",
        "Dəstək və administratorla əlaqə",
    ],
    "tr": [
        "Satın alma veya kiralama talebi",
        "Satıcı veya kiraya veren",
        "Gayrimenkul yatırımı ve kat karşılığı inşaat",
        "Emlak danışmanı",
        "Destek ve yöneticiyle iletişim",
    ],
    "ar": [
        "طلب شراء أو استئجار",
        "بائع أو مؤجّر",
        "الاستثمار العقاري والشراكة في البناء",
        "وسيط عقاري",
        "الدعم والتواصل مع الإدارة",
    ],
}

SUBMENUS = {
    "fa": {
        "متقاضی خرید یا اجاره": [
            "ثبت تقاضای خرید",
            "ثبت تقاضای اجاره",
        ],
        "فروشنده یا موجر": [
            "ثبت آگهی فروش",
            "ثبت آگهی اجاره",
        ],
        "سرمایه‌گذاری ملکی و مشارکت در ساخت": [
            "درخواست پیش خرید",
            "سازنده آماده مشارکت هستم",
            "مالک ملک برای مشارکت در ساخت هستم",
        ],
        "مشاور املاک": [
            "ثبت آگهی ملک",
            "پیگیری مشتریان",
            "درخواست همکاری با مشاوران",
        ],
        "پشتیبانی و ارتباط با مدیر": [
            "ارسال پیام به مدیر",
            "گزارش مشکل یا تخلف",
        ],
    },
    "en": {
        "Buy or rent request": [
            "Submit purchase request",
            "Submit rental request",
        ],
        "Seller or landlord": [
            "Post property for sale",
            "Post property for rent",
        ],
        "Property investment and construction partnership": [
            "Pre-purchase request",
            "Builder seeking a partner",
            "Property owner seeking a construction partner",
        ],
        "Real estate agent": [
            "Post a property listing",
            "Follow up with clients",
            "Request cooperation with agents",
        ],
        "Support and contact admin": [
            "Send a message to admin",
            "Report a problem or violation",
        ],
    },
    "az": {
        "Alış və ya kirayə müraciəti": [
            "Alış müraciəti yarat",
            "Kirayə müraciəti yarat",
        ],
        "Satıcı və ya kirayə verən": [
            "Satış elanı yerləşdir",
            "Kirayə elanı yerləşdir",
        ],
        "Əmlak investisiyası və tikinti tərəfdaşlığı": [
            "Öncədən alış müraciəti",
            "Tikinti tərəfdaşı axtarıram",
            "Tikinti üçün tərəfdaş axtaran əmlak sahibi",
        ],
        "Əmlak agenti": [
            "Əmlak elanı yerləşdir",
            "Müştəriləri izləyin",
            "Agentlərlə əməkdaşlıq müraciəti",
        ],
        "Dəstək və administratorla əlaqə": [
            "Administratora mesaj göndər",
            "Problem və ya pozuntu barədə məlumat ver",
        ],
    },
    "tr": {
        "Satın alma veya kiralama talebi": [
            "Satın alma talebi oluştur",
            "Kiralama talebi oluştur",
        ],
        "Satıcı veya kiraya veren": [
            "Satılık ilanı ver",
            "Kiralık ilanı ver",
        ],
        "Gayrimenkul yatırımı ve kat karşılığı inşaat": [
            "Ön satın alma talebi",
            "İnşaat için ortak arıyorum",
            "İnşaat ortaklığı arayan mülk sahibi",
        ],
        "Emlak danışmanı": [
            "Emlak ilanı ver",
            "Müşteri takibi",
            "Danışmanlarla iş birliği talebi",
        ],
        "Destek ve yöneticiyle iletişim": [
            "Yöneticiye mesaj gönder",
            "Sorun veya ihlal bildir",
        ],
    },
    "ar": {
        "طلب شراء أو استئجار": [
            "تسجيل طلب شراء",
            "تسجيل طلب استئجار",
        ],
        "بائع أو مؤجّر": [
            "نشر إعلان للبيع",
            "نشر إعلان للإيجار",
        ],
        "الاستثمار العقاري والشراكة في البناء": [
            "طلب شراء مسبق",
            "مقاول يبحث عن شريك",
            "مالك عقار يبحث عن شريك للبناء",
        ],
        "وسيط عقاري": [
            "نشر إعلان عقاري",
            "متابعة العملاء",
            "طلب التعاون مع الوسطاء",
        ],
        "الدعم والتواصل مع الإدارة": [
            "إرسال رسالة إلى الإدارة",
            "الإبلاغ عن مشكلة أو مخالفة",
        ],
    },
}

PROPERTY_TYPES = {
    "fa": ["مسکونی", "اداری", "تجاری", "زراعی", "صنعتی"],
    "en": ["Residential", "Office", "Commercial", "Agricultural", "Industrial"],
    "az": ["Yaşayış", "Ofis", "Kommersiya", "Kənd təsərrüfatı", "Sənaye"],
    "tr": ["Konut", "Ofis", "Ticari", "Tarım", "Sanayi"],
    "ar": ["سكني", "مكتبي", "تجاري", "زراعي", "صناعي"],
}

MESSAGES = {
    "fa": {
        "welcome": "به سامانه املاک تهران خوش آمدید.\nلطفاً زبان خود را انتخاب کنید:",
        "main": "منوی اصلی املاک تهران:",
        "choose_type": "نوع ملک را انتخاب کنید:",
        "city": "شهر و محدوده موردنظر را وارد کنید:",
        "budget": "بودجه یا قیمت موردنظر را وارد کنید:",
        "area": "متراژ ملک را وارد کنید:",
        "deposit": "مبلغ ودیعه را وارد کنید:",
        "rent": "مبلغ اجاره ماهانه را وارد کنید:",
        "description": "توضیحات تکمیلی را وارد کنید:",
        "contact": "شماره تماس را وارد کنید:",
        "project": "نوع پروژه یا ملک موردنظر را توضیح دهید:",
        "conditions": "شرایط موردنظر را بنویسید:",
        "name": "نام یا عنوان خود را وارد کنید:",
        "message": "پیام خود را بنویسید:",
        "topic": "موضوع را وارد کنید:",
        "details": "شرح موضوع را وارد کنید:",
        "saved": "اطلاعات شما با کد پیگیری {id} ثبت شد و برای بررسی به مدیر ارسال شد.",
        "admin": "درخواست جدید #{id}\nبخش: {category}\nکاربر: {user}\nشناسه: {uid}\n\n{data}\n\nتأیید: /approve_{id}\nرد: /reject_{id}",
        "approved": "درخواست شما با کد {id} تأیید شد.",
        "rejected": "درخواست شما با کد {id} رد شد.",
        "admin_only": "این دستور فقط برای مدیر اصلی فعال است.",
        "not_found": "درخواستی با این کد پیدا نشد.",
        "cancelled": "عملیات لغو شد.",
        "unknown": "لطفاً یکی از گزینه‌های منو را انتخاب کنید.",
        "language_saved": "زبان انتخابی شما ذخیره شد.",
        "help": "اطلاعات را مرحله‌به‌مرحله وارد کنید. برای بازگشت، دکمه منوی اصلی را بزنید.",
    },
    "en": {
        "welcome": "Welcome to Tehran Real Estate.\nPlease choose your language:",
        "main": "Tehran Real Estate main menu:",
        "choose_type": "Choose the property type:",
        "city": "Enter the city and preferred area:",
        "budget": "Enter your budget or desired price:",
        "area": "Enter the property area:",
        "deposit": "Enter the deposit amount:",
        "rent": "Enter the monthly rent:",
        "description": "Enter additional details:",
        "contact": "Enter your contact phone number:",
        "project": "Describe the project or property you want:",
        "conditions": "Enter your preferred conditions:",
        "name": "Enter your name or business name:",
        "message": "Write your message:",
        "topic": "Enter the subject:",
        "details": "Describe the issue:",
        "saved": "Your information was registered under reference #{id} and sent to the administrator.",
        "admin": "New submission #{id}\nSection: {category}\nUser: {user}\nID: {uid}\n\n{data}\n\nApprove: /approve_{id}\nReject: /reject_{id}",
        "approved": "Your submission #{id} has been approved.",
        "rejected": "Your submission #{id} has been rejected.",
        "admin_only": "This command is for the main administrator only.",
        "not_found": "No submission was found with this ID.",
        "cancelled": "Operation cancelled.",
        "unknown": "Please choose an option from the menu.",
        "language_saved": "Your language preference has been saved.",
        "help": "Enter the requested information step by step. Use the main menu button to return.",
    },
    "az": {
        "welcome": "Tehran Daşınmaz Əmlak sisteminə xoş gəlmisiniz.\nDil seçin:",
        "main": "Tehran Əmlak əsas menyusu:",
        "choose_type": "Əmlak növünü seçin:",
        "city": "Şəhər və ərazini daxil edin:",
        "budget": "Büdcəni və ya istənilən qiyməti daxil edin:",
        "area": "Əmlakın sahəsini daxil edin:",
        "deposit": "Depozit məbləğini daxil edin:",
        "rent": "Aylıq kirayə haqqını daxil edin:",
        "description": "Əlavə məlumatları daxil edin:",
        "contact": "Əlaqə nömrəsini daxil edin:",
        "project": "İstədiyiniz layihəni və ya əmlakı təsvir edin:",
        "conditions": "İstədiyiniz şərtləri yazın:",
        "name": "Adınızı və ya şirkət adını daxil edin:",
        "message": "Mesajınızı yazın:",
        "topic": "Mövzunu daxil edin:",
        "details": "Məsələni ətraflı təsvir edin:",
        "saved": "Məlumatınız #{id} nömrəsi ilə qeydə alındı və administratora göndərildi.",
        "admin": "Yeni müraciət #{id}\nBölmə: {category}\nİstifadəçi: {user}\nID: {uid}\n\n{data}\n\nTəsdiq: /approve_{id}\nRədd: /reject_{id}",
        "approved": "#{id} nömrəli müraciətiniz təsdiqləndi.",
        "rejected": "#{id} nömrəli müraciətiniz rədd edildi.",
        "admin_only": "Bu əmr yalnız əsas administrator üçündür.",
        "not_found": "Bu nömrə ilə müraciət tapılmadı.",
        "cancelled": "Əməliyyat ləğv edildi.",
        "unknown": "Zəhmət olmasa menyudan seçim edin.",
        "language_saved": "Dil seçiminiz yadda saxlanıldı.",
        "help": "Məlumatları addım-addım daxil edin. Geri qayıtmaq üçün əsas menyu düyməsini seçin.",
    },
    "tr": {
        "welcome": "Tehran Gayrimenkul sistemine hoş geldiniz.\nLütfen dilinizi seçin:",
        "main": "Tehran Gayrimenkul ana menüsü:",
        "choose_type": "Gayrimenkul türünü seçin:",
        "city": "Şehir ve tercih ettiğiniz bölgeyi girin:",
        "budget": "Bütçenizi veya istediğiniz fiyatı girin:",
        "area": "Gayrimenkulün alanını girin:",
        "deposit": "Depozito tutarını girin:",
        "rent": "Aylık kira tutarını girin:",
        "description": "Ek açıklamaları girin:",
        "contact": "Telefon numaranızı girin:",
        "project": "İstediğiniz projeyi veya mülkü açıklayın:",
        "conditions": "İstediğiniz koşulları yazın:",
        "name": "Adınızı veya işletme adınızı girin:",
        "message": "Mesajınızı yazın:",
        "topic": "Konuyu girin:",
        "details": "Konuyu ayrıntılı olarak açıklayın:",
        "saved": "Bilgileriniz #{id} takip numarasıyla kaydedildi ve yöneticiye gönderildi.",
        "admin": "Yeni başvuru #{id}\nBölüm: {category}\nKullanıcı: {user}\nID: {uid}\n\n{data}\n\nOnayla: /approve_{id}\nReddet: /reject_{id}",
        "approved": "#{id} numaralı başvurunuz onaylandı.",
        "rejected": "#{id} numaralı başvurunuz reddedildi.",
        "admin_only": "Bu komut yalnızca ana yönetici tarafından kullanılabilir.",
        "not_found": "Bu numarayla bir başvuru bulunamadı.",
        "cancelled": "İşlem iptal edildi.",
        "unknown": "Lütfen menüden bir seçenek seçin.",
        "language_saved": "Dil tercihiniz kaydedildi.",
        "help": "Bilgileri adım adım girin. Geri dönmek için ana menü düğmesini kullanın.",
    },
    "ar": {
        "welcome": "مرحباً بكم في نظام عقارات طهران.\nيرجى اختيار اللغة:",
        "main": "القائمة الرئيسية لعقارات طهران:",
        "choose_type": "اختر نوع العقار:",
        "city": "أدخل المدينة والمنطقة المطلوبة:",
        "budget": "أدخل الميزانية أو السعر المطلوب:",
        "area": "أدخل مساحة العقار:",
        "deposit": "أدخل مبلغ التأمين:",
        "rent": "أدخل الإيجار الشهري:",
        "description": "أدخل تفاصيل إضافية:",
        "contact": "أدخل رقم هاتف للتواصل:",
        "project": "صف المشروع أو العقار المطلوب:",
        "conditions": "اكتب الشروط المطلوبة:",
        "name": "أدخل اسمك أو اسم الشركة:",
        "message": "اكتب رسالتك:",
        "topic": "أدخل الموضوع:",
        "details": "اشرح التفاصيل:",
        "saved": "تم تسجيل معلوماتك برقم متابعة {id} وإرسالها إلى الإدارة.",
        "admin": "طلب جديد #{id}\nالقسم: {category}\nالمستخدم: {user}\nالمعرّف: {uid}\n\n{data}\n\nللموافقة: /approve_{id}\nللرفض: /reject_{id}",
        "approved": "تمت الموافقة على طلبك رقم {id}.",
        "rejected": "تم رفض طلبك رقم {id}.",
        "admin_only": "هذا الأمر مخصص للمسؤول الرئيسي فقط.",
        "not_found": "لم يتم العثور على طلب بهذا الرقم.",
        "cancelled": "تم إلغاء العملية.",
        "unknown": "يرجى اختيار أحد الخيارات من القائمة.",
        "language_saved": "تم حفظ اللغة المفضلة.",
        "help": "أدخل المعلومات خطوة بخطوة. للعودة، اضغط زر القائمة الرئيسية.",
    },
}

# Forms are described by logical field keys, so prompts follow the selected language.
FORM_SCHEMAS = {
    "buy": ["type", "city", "budget", "description", "contact"],
    "rent_request": ["type", "city", "budget", "description", "contact"],
    "sale": ["type", "city", "area", "budget", "description", "contact"],
    "rent_listing": ["type", "city", "area", "deposit", "rent", "description", "contact"],
    "prebuy": ["project", "city", "budget", "conditions", "contact"],
    "builder": ["name", "city", "project", "conditions", "contact"],
    "owner_partner": ["project", "city", "area", "conditions", "contact"],
    "agent_listing": ["type", "city", "budget", "description", "contact"],
    "client_followup": ["name", "details", "contact"],
    "agent_cooperation": ["name", "city", "conditions", "contact"],
    "admin_message": ["message", "contact"],
    "report": ["topic", "details", "contact"],
}

FIELD_LABELS = {
    "fa": {
        "type": "نوع ملک", "city": "شهر و محدوده", "budget": "بودجه/قیمت",
        "area": "متراژ", "deposit": "ودیعه", "rent": "اجاره ماهانه",
        "description": "توضیحات", "contact": "شماره تماس", "project": "پروژه/ملک",
        "conditions": "شرایط", "name": "نام", "message": "پیام",
        "topic": "موضوع", "details": "شرح",
    },
    "en": {
        "type": "Property type", "city": "City and area", "budget": "Budget/price",
        "area": "Property area", "deposit": "Deposit", "rent": "Monthly rent",
        "description": "Description", "contact": "Phone", "project": "Project/property",
        "conditions": "Conditions", "name": "Name", "message": "Message",
        "topic": "Subject", "details": "Details",
    },
    "az": {
        "type": "Əmlak növü", "city": "Şəhər və ərazi", "budget": "Büdcə/qiymət",
        "area": "Sahə", "deposit": "Depozit", "rent": "Aylıq kirayə",
        "description": "Təsvir", "contact": "Telefon", "project": "Layihə/əmlak",
        "conditions": "Şərtlər", "name": "Ad", "message": "Mesaj",
        "topic": "Mövzu", "details": "Təfərrüatlar",
    },
    "tr": {
        "type": "Gayrimenkul türü", "city": "Şehir ve bölge", "budget": "Bütçe/fiyat",
        "area": "Alan", "deposit": "Depozito", "rent": "Aylık kira",
        "description": "Açıklama", "contact": "Telefon", "project": "Proje/mülk",
        "conditions": "Koşullar", "name": "Ad", "message": "Mesaj",
        "topic": "Konu", "details": "Ayrıntılar",
    },
    "ar": {
        "type": "نوع العقار", "city": "المدينة والمنطقة", "budget": "الميزانية/السعر",
        "area": "المساحة", "deposit": "التأمين", "rent": "الإيجار الشهري",
        "description": "الوصف", "contact": "الهاتف", "project": "المشروع/العقار",
        "conditions": "الشروط", "name": "الاسم", "message": "الرسالة",
        "topic": "الموضوع", "details": "التفاصيل",
    },
}

# Maps each translated button to a logical action.
ACTIONS = {
    "fa": {
        "ثبت تقاضای خرید": "buy",
        "ثبت تقاضای اجاره": "rent_request",
        "ثبت آگهی فروش": "sale",
        "ثبت آگهی اجاره": "rent_listing",
        "درخواست پیش خرید": "prebuy",
        "سازنده آماده مشارکت هستم": "builder",
        "مالک ملک برای مشارکت در ساخت هستم": "owner_partner",
        "ثبت آگهی ملک": "agent_listing",
        "پیگیری مشتریان": "client_followup",
        "درخواست همکاری با مشاوران": "agent_cooperation",
        "ارسال پیام به مدیر": "admin_message",
        "گزارش مشکل یا تخلف": "report",
    },
    "en": {
        "Submit purchase request": "buy",
        "Submit rental request": "rent_request",
        "Post property for sale": "sale",
        "Post property for rent": "rent_listing",
        "Pre-purchase request": "prebuy",
        "Builder seeking a partner": "builder",
        "Property owner seeking a construction partner": "owner_partner",
        "Post a property listing": "agent_listing",
        "Follow up with clients": "client_followup",
        "Request cooperation with agents": "agent_cooperation",
        "Send a message to admin": "admin_message",
        "Report a problem or violation": "report",
    },
    "az": {
        "Alış müraciəti yarat": "buy",
        "Kirayə müraciəti yarat": "rent_request",
        "Satış elanı yerləşdir": "sale",
        "Kirayə elanı yerləşdir": "rent_listing",
        "Öncədən alış müraciəti": "prebuy",
        "Tikinti tərəfdaşı axtarıram": "builder",
        "Tikinti üçün tərəfdaş axtaran əmlak sahibi": "owner_partner",
        "Əmlak elanı yerləşdir": "agent_listing",
        "Müştəriləri izləyin": "client_followup",
        "Agentlərlə əməkdaşlıq müraciəti": "agent_cooperation",
        "Administratora mesaj göndər": "admin_message",
        "Problem və ya pozuntu barədə məlumat ver": "report",
    },
    "tr": {
        "Satın alma talebi oluştur": "buy",
        "Kiralama talebi oluştur": "rent_request",
        "Satılık ilanı ver": "sale",
        "Kiralık ilanı ver": "rent_listing",
        "Ön satın alma talebi": "prebuy",
        "İnşaat için ortak arıyorum": "builder",
        "İnşaat ortaklığı arayan mülk sahibi": "owner_partner",
        "Emlak ilanı ver": "agent_listing",
        "Müşteri takibi": "client_followup",
        "Danışmanlarla iş birliği talebi": "agent_cooperation",
        "Yöneticiye mesaj gönder": "admin_message",
        "Sorun veya ihlal bildir": "report",
    },
    "ar": {
        "تسجيل طلب شراء": "buy",
        "تسجيل طلب استئجار": "rent_request",
        "نشر إعلان للبيع": "sale",
        "نشر إعلان للإيجار": "rent_listing",
        "طلب شراء مسبق": "prebuy",
        "مقاول يبحث عن شريك": "builder",
        "مالك عقار يبحث عن شريك للبناء": "owner_partner",
        "نشر إعلان عقاري": "agent_listing",
        "متابعة العملاء": "client_followup",
        "طلب التعاون مع الوسطاء": "agent_cooperation",
        "إرسال رسالة إلى الإدارة": "admin_message",
        "الإبلاغ عن مشكلة أو مخالفة": "report",
    },
}

# Language-specific type selection maps to the same logical form.
TYPE_TO_FORM = {}
for lang, types in PROPERTY_TYPES.items():
    for type_name in types:
        TYPE_TO_FORM[(lang, type_name)] = type_name

app = Flask(__name__)
state = {"status": "starting", "telegram_polling": False, "last_update_time": None}


def init_db():
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'fa'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                language TEXT NOT NULL,
                category TEXT NOT NULL,
                data TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
            )
        """)
        conn.commit()


def get_language(user_id, context):
    return context.user_data.get("language", "fa")


def save_language(user_id, language, context):
    context.user_data["language"] = language
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute(
            "INSERT INTO users(user_id, language) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET language=excluded.language",
            (user_id, language),
        )
        conn.commit()


def load_language(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        row = conn.execute(
            "SELECT language FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
    return row[0] if row else None


def keyboard(rows):
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="...",
    )


def language_keyboard():
    return keyboard([[LANGUAGES["fa"], LANGUAGES["en"]],
                     [LANGUAGES["az"], LANGUAGES["tr"]],
                     [LANGUAGES["ar"]]])


def language_code_from_button(text):
    for code, name in LANGUAGES.items():
        if text == name:
            return code
    return None


def main_keyboard(lang):
    rows = [[item] for item in MAIN_MENU[lang]]
    rows += [[CHANGE_LANGUAGE[lang]]]
    return keyboard(rows)


def submenu_keyboard(lang, main_item):
    items = SUBMENUS[lang].get(main_item, [])
    rows = [[item] for item in items]
    rows += [[BACK[lang]], [CHANGE_LANGUAGE[lang]]]
    return keyboard(rows)


def property_keyboard(lang):
    rows = [[item] for item in PROPERTY_TYPES[lang]]
    rows += [[BACK[lang]], [CHANGE_LANGUAGE[lang]]]
    return keyboard(rows)


async def show_language_menu(update, context, welcome=True):
    if welcome:
        await update.message.reply_text(
            "Welcome / خوش آمدید / Xoş gəlmisiniz / Hoş geldiniz / مرحباً\n"
            "Choose your language / زبان خود را انتخاب کنید:",
            reply_markup=language_keyboard(),
        )
    else:
        await update.message.reply_text(
            "Choose your language / زبان خود را انتخاب کنید:",
            reply_markup=language_keyboard(),
        )


async def show_main(update, context, text=None):
    lang = get_language(update.effective_user.id, context)
    await update.message.reply_text(
        text or MESSAGES[lang]["main"],
        reply_markup=main_keyboard(lang),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    saved = load_language(update.effective_user.id)
    if saved in LANGUAGES:
        context.user_data["language"] = saved
        await show_main(update, context, MESSAGES[saved]["main"])
    else:
        await show_language_menu(update, context, welcome=True)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("form", None)
    await show_main(update, context, MESSAGES[get_language(update.effective_user.id, context)]["cancelled"])


def save_submission(user, lang, category, answers):
    labels = FIELD_LABELS[lang]
    data = "\n".join(f"{labels.get(key, key)}: {value}" for key, value in answers.items())
    with sqlite3.connect(DATABASE_PATH) as conn:
        cur = conn.execute(
            """INSERT INTO submissions
            (created_at, user_id, username, language, category, data, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
            (
                datetime.now(timezone.utc).isoformat(),
                user.id,
                user.username,
                lang,
                category,
                data,
            ),
        )
        conn.commit()
        return cur.lastrowid, data


def prompt_for(lang, key):
    msg = MESSAGES[lang]
    prompts = {
        "type": msg["choose_type"],
        "city": msg["city"],
        "budget": msg["budget"],
        "area": msg["area"],
        "deposit": msg["deposit"],
        "rent": msg["rent"],
        "description": msg["description"],
        "contact": msg["contact"],
        "project": msg["project"],
        "conditions": msg["conditions"],
        "name": msg["name"],
        "message": msg["message"],
        "topic": msg["topic"],
        "details": msg["details"],
    }
    return prompts[key]


async def begin_form(update, context, action, category):
    lang = get_language(update.effective_user.id, context)
    context.user_data["form"] = {
        "action": action,
        "category": category,
        "keys": FORM_SCHEMAS[action],
        "index": 0,
        "answers": {},
    }
    first_key = FORM_SCHEMAS[action][0]

    if first_key == "type":
        await update.message.reply_text(
            MESSAGES[lang]["choose_type"],
            reply_markup=property_keyboard(lang),
        )
    else:
        await update.message.reply_text(
            prompt_for(lang, first_key) + "\n\n" + BACK[lang],
            reply_markup=keyboard([[BACK[lang]], [CHANGE_LANGUAGE[lang]]]),
        )


async def notify_admin(context, submission_id, update, lang, category, data):
    user = update.effective_user
    message = MESSAGES[lang]["admin"].format(
        id=submission_id,
        category=category,
        user=user.full_name,
        uid=user.id,
        data=data,
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=message)
    except Exception:
        logger.exception("Could not notify admin")


async def finish_form(update, context, form):
    lang = get_language(update.effective_user.id, context)
    user = update.effective_user
    submission_id, data = save_submission(
        user, lang, form["category"], form["answers"]
    )
    await notify_admin(
        context, submission_id, update, lang, form["category"], data
    )
    context.user_data.pop("form", None)
    await update.message.reply_text(
        MESSAGES[lang]["saved"].format(id=submission_id),
        reply_markup=main_keyboard(lang),
    )


async def handle_form(update, context, text):
    form = context.user_data.get("form")
    if not form:
        return False

    lang = get_language(update.effective_user.id, context)
    if text == BACK[lang]:
        context.user_data.pop("form", None)
        await show_main(update, context)
        return True

    key = form["keys"][form["index"]]

    if key == "type" and text not in PROPERTY_TYPES[lang]:
        await update.message.reply_text(
            MESSAGES[lang]["choose_type"],
            reply_markup=property_keyboard(lang),
        )
        return True

    form["answers"][key] = text
    form["index"] += 1

    if form["index"] >= len(form["keys"]):
        await finish_form(update, context, form)
        return True

    next_key = form["keys"][form["index"]]
    if next_key == "type":
        await update.message.reply_text(
            MESSAGES[lang]["choose_type"],
            reply_markup=property_keyboard(lang),
        )
    else:
        await update.message.reply_text(
            prompt_for(lang, next_key) + "\n\n" + BACK[lang],
            reply_markup=keyboard([[BACK[lang]], [CHANGE_LANGUAGE[lang]]]),
        )
    return True


async def admin_decision(update, context):
    user = update.effective_user
    if not user or user.id != ADMIN_ID:
        await update.message.reply_text("Admin only.")
        return

    command = update.message.text.strip()
    approve = command.startswith("/approve_")
    prefix = "/approve_" if approve else "/reject_"

    try:
        submission_id = int(command[len(prefix):].split("@")[0])
    except ValueError:
        await update.message.reply_text("Invalid reference number.")
        return

    with sqlite3.connect(DATABASE_PATH) as conn:
        row = conn.execute(
            "SELECT category, data, user_id, language FROM submissions WHERE id=?",
            (submission_id,),
        ).fetchone()

        if not row:
            await update.message.reply_text("Submission not found.")
            return

        category, data, owner_id, lang = row
        status = "approved" if approve else "rejected"
        conn.execute(
            "UPDATE submissions SET status=? WHERE id=?",
            (status, submission_id),
        )
        conn.commit()

    key = "approved" if approve else "rejected"
    try:
        await context.bot.send_message(
            chat_id=owner_id,
            text=MESSAGES.get(lang, MESSAGES["fa"])[key].format(id=submission_id),
        )
    except Exception:
        logger.exception("Could not notify submitter")

    await update.message.reply_text(f"Submission #{submission_id}: {status}")

    if approve and category in {
        "ثبت آگهی فروش", "ثبت آگهی اجاره", "ثبت آگهی ملک",
        "Post property for sale", "Post property for rent",
        "Post a property listing",
        "Satış elanı yerləşdir", "Kirayə elanı yerləşdir",
        "Əmlak elanı yerləşdir",
        "Satılık ilanı ver", "Kiralık ilanı ver", "Emlak ilanı ver",
        "نشر إعلان للبيع", "نشر إعلان للإيجار", "نشر إعلان عقاري",
    }:
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=f"Approved listing #{submission_id}\n\n{data}",
            )
        except Exception:
            logger.exception("Could not publish listing")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    state["last_update_time"] = int(datetime.now(timezone.utc).timestamp())
    user_id = update.effective_user.id

    # Select a language when the user first enters, or changes language.
    selected_lang = language_code_from_button(text)
    if selected_lang:
        save_language(user_id, selected_lang, context)
        context.user_data.pop("form", None)
        await update.message.reply_text(
            MESSAGES[selected_lang]["language_saved"],
            reply_markup=main_keyboard(selected_lang),
        )
        await update.message.reply_text(MESSAGES[selected_lang]["main"])
        return

    lang = get_language(user_id, context)

    if text == CHANGE_LANGUAGE[lang]:
        context.user_data.pop("form", None)
        await show_language_menu(update, context, welcome=False)
        return

    if text == BACK[lang]:
        context.user_data.pop("form", None)
        await show_main(update, context)
        return

    if await handle_form(update, context, text):
        return

    # Main menu selection
    if text in MAIN_MENU[lang]:
        context.user_data.pop("form", None)
        await update.message.reply_text(
            text,
            reply_markup=submenu_keyboard(lang, text),
        )
        return

    # A property type is only selected after the form begins.
    # Map submenu item to a logical form.
    action = ACTIONS[lang].get(text)
    if action:
        await begin_form(update, context, action, text)
        return

    # Keep the language selection accessible if the user sends an unknown message.
    await update.message.reply_text(
        MESSAGES[lang]["unknown"],
        reply_markup=main_keyboard(lang),
    )


@app.get("/")
def home():
    return jsonify({"service": "tehran-real-estate-bot", **state})


@app.get("/health")
def health():
    return jsonify({"status": "ok", **state})


def run_web_server():
    app.run(host="0.0.0.0", port=PORT, use_reloader=False)


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")

    init_db()
    threading.Thread(target=run_web_server, daemon=True).start()

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(
        MessageHandler(filters.Regex(r"^/approve_\d+(?:@\w+)?$"), admin_decision)
    )
    application.add_handler(
        MessageHandler(filters.Regex(r"^/reject_\d+(?:@\w+)?$"), admin_decision)
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    state["status"] = "running"
    state["telegram_polling"] = True
    logger.info("Starting Telegram polling.")
    application.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
