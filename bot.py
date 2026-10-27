
import os
import time
import threading
import requests
from flask import Flask

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured")

API = f"https://api.telegram.org/bot{TOKEN}"
app = Flask(__name__)

# منوی اصلی
MAIN_MENU = {
    "keyboard": [
        [{"text": "متقاضی خرید یا اجاره"}],
        [{"text": "فروشنده یا موجر"}],
        [{"text": "سرمایه‌گذاری ملکی و مشارکت در ساخت"}],
        [{"text": "مشاور املاک"}],
        [{"text": "پشتیبانی و ارتباط با مدیر"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True
}

MENUS = {
    "متقاضی خرید یا اجاره": {
        "keyboard": [
            [{"text": "ثبت درخواست خرید ملک"}],
            [{"text": "ثبت درخواست اجاره ملک"}],
            [{"text": "جست‌وجوی ملک برای خرید"}],
            [{"text": "جست‌وجوی ملک برای اجاره"}],
            [{"text": "بازگشت به منوی اصلی"}],
        ],
        "resize_keyboard": True
    },
    "فروشنده یا موجر": {
        "keyboard": [
            [{"text": "ثبت آگهی فروش"}],
            [{"text": "ثبت آگهی اجاره"}],
            [{"text": "پیگیری آگهی"}],
            [{"text": "بازگشت به منوی اصلی"}],
        ],
        "resize_keyboard": True
    },
    "سرمایه‌گذاری ملکی و مشارکت در ساخت": {
        "keyboard": [
            [{"text": "فرصت‌های سرمایه‌گذاری"}],
            [{"text": "ثبت درخواست سرمایه‌گذاری"}],
            [{"text": "مشارکت در ساخت"}],
            [{"text": "بازگشت به منوی اصلی"}],
        ],
        "resize_keyboard": True
    },
    "مشاور املاک": {
        "keyboard": [
            [{"text": "مدیریت آگهی‌ها"}],
            [{"text": "پیگیری مشتریان"}],
            [{"text": "همکاری با مشاوران"}],
            [{"text": "بازگشت به منوی اصلی"}],
        ],
        "resize_keyboard": True
    },
    "پشتیبانی و ارتباط با مدیر": {
        "keyboard": [
            [{"text": "ارسال پیام به مدیر"}],
            [{"text": "گزارش تخلف"}],
            [{"text": "پیگیری درخواست پشتیبانی"}],
            [{"text": "بازگشت به منوی اصلی"}],
        ],
        "resize_keyboard": True
    }
}

@app.get("/")
def health():
    return "Tehran Real Estate Bot is running", 200

def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if keyboard:
        data["reply_markup"] = keyboard

    try:
        response = requests.post(
            f"{API}/sendMessage",
            json=data,
            timeout=20
        )
        response.raise_for_status()
    except requests.RequestException as error:
        print("Send message error:", error)

def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if text in ("/start", "/menu", "بازگشت به منوی اصلی"):
        send_message(
            chat_id,
            "به سامانه املاک تهران خوش آمدید.\n"
            "لطفاً بخش موردنظر خود را انتخاب کنید.",
            MAIN_MENU
        )
        return

    if text in MENUS:
        send_message(
            chat_id,
            f"بخش «{text}» را انتخاب کردید.\n"
            "لطفاً گزینه موردنظر را انتخاب کنید.",
            MENUS[text]
        )
        return

    messages = {
        "ثبت درخواست خرید ملک":
            "درخواست خرید ملک انتخاب شد.\n"
            "برای ادامه، شهر و نوع ملک را بنویسید.",

        "ثبت درخواست اجاره ملک":
            "درخواست اجاره انتخاب شد.\n"
            "برای ادامه، شهر و نوع ملک را بنویسید.",

        "جست‌وجوی ملک برای خرید":
            "جست‌وجوی خرید انتخاب شد.\n"
            "شهر و نوع ملک موردنظر را بنویسید.",

        "جست‌وجوی ملک برای اجاره":
            "جست‌وجوی اجاره انتخاب شد.\n"
            "شهر و نوع ملک موردنظر را بنویسید.",

        "ثبت آگهی فروش":
            "ثبت آگهی فروش انتخاب شد.\n"
            "فرم کامل ثبت آگهی در مرحله بعد پیاده‌سازی می‌شود.",

        "ثبت آگهی اجاره":
            "ثبت آگهی اجاره انتخاب شد.\n"
            "فرم کامل ثبت آگهی در مرحله بعد پیاده‌سازی می‌شود.",

        "پیگیری آگهی":
            "برای پیگیری آگهی، کد آگهی را ارسال کنید.",

        "فرصت‌های سرمایه‌گذاری":
            "فرصت‌های تأییدشده سرمایه‌گذاری در این بخش نمایش داده خواهند شد.",

        "ثبت درخواست سرمایه‌گذاری":
            "برای شروع، شهر و مبلغ سرمایه‌گذاری موردنظر را بنویسید.",

        "مشارکت در ساخت":
            "برای مشارکت در ساخت، شهر و وضعیت خود را بنویسید: مالک یا سازنده.",

        "مدیریت آگهی‌ها":
            "بخش مدیریت آگهی‌ها انتخاب شد.",

        "پیگیری مشتریان":
            "بخش پیگیری مشتریان انتخاب شد.",

        "همکاری با مشاوران":
            "بخش همکاری با مشاوران انتخاب شد.",

        "ارسال پیام به مدیر":
            "پیام خود را در همین گفتگو ارسال کنید.",

        "گزارش تخلف":
            "توضیحات تخلف و در صورت امکان کد آگهی را ارسال کنید.",

        "پیگیری درخواست پشتیبانی":
            "کد درخواست پشتیبانی را ارسال کنید."
    }

    answer = messages.get(
        text,
        "پیام شما دریافت شد.\n"
        "برای انتخاب بخش‌های سامانه، دستور /menu را ارسال کنید."
    )
    send_message(chat_id, answer)

def polling():
    offset = None

    while True:
        try:
            params = {"timeout": 25}
            if offset is not None:
                params["offset"] = offset

            response = requests.get(
                f"{API}/getUpdates",
                params=params,
                timeout=35
            )
            response.raise_for_status()

            for update in response.json().get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message")

                if message:
                    handle_message(message)

        except Exception as error:
            print("Polling error:", error)
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(
        target=polling,
        daemon=True
    ).start()

    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
