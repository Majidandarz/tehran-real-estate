
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


@app.get("/")
def health():
    return "Tehran Real Estate Bot is running", 200


def send_message(chat_id, text, keyboard=None):
    data = {"chat_id": chat_id, "text": text}
    if keyboard:
        data["reply_markup"] = keyboard
    requests.post(f"{API}/sendMessage", json=data, timeout=20)


def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if text == "/start":
        keyboard = {
            "keyboard": [
                [{"text": "خرید ملک"}, {"text": "اجاره ملک"}],
                [{"text": "ثبت آگهی"}, {"text": "درخواست مشاوره"}],
                [{"text": "راهنما"}]
            ],
            "resize_keyboard": True
        }
        send_message(
            chat_id,
            "به ربات املاک تهران خوش آمدید.\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید.",
            keyboard
        )
    elif text == "خرید ملک":
        send_message(chat_id, "برای خرید ملک، شهر و نوع ملک موردنظر را بنویسید.")
    elif text == "اجاره ملک":
        send_message(chat_id, "برای اجاره، شهر و نوع ملک موردنظر را بنویسید.")
    elif text == "ثبت آگهی":
        send_message(chat_id, "برای ثبت آگهی، نوع ملک و شهر را ارسال کنید.")
    elif text == "درخواست مشاوره":
        send_message(chat_id, "شهر و موضوع درخواست خود را بنویسید.")
    elif text == "راهنما" or text == "/help":
        send_message(chat_id, "از منوی ربات گزینه موردنظر را انتخاب کنید.")
    else:
        send_message(
            chat_id,
            "پیامتان دریافت شد. لطفاً از منوی ربات گزینه موردنظر را انتخاب کنید."
        )


def polling():
    offset = None
    while True:
        try:
            params = {"timeout": 25}
            if offset is not None:
                params["offset"] = offset

            response = requests.get(
                f"{API}/getUpdates", params=params, timeout=35
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
    threading.Thread(target=polling, daemon=True).start()
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
