import requests, os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

def send_message(chat_id, text):
    requests.post(f"{API_URL}sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def delete_message(chat_id, message_id):
    requests.post(f"{API_URL}deleteMessage", json={
        "chat_id": chat_id,
        "message_id": message_id
    })

def send_buttons(chat_id, text, buttons):
    inline_keyboard = [[button] for button in buttons]
    requests.post(f"{API_URL}sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {
            "inline_keyboard": inline_keyboard
        }
    })
