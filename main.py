from flask import Flask, request
import requests
import json
import os
import time
from datetime import datetime

app = Flask(__name__)

# === CONFIG ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Add this in Render env variables
OWNER_ID = 6356015122
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
AUTH_FILE = "auth_users.json"
USER_STORE = "user_messages.json"
STATS_FILE = "stats.json"
DELETE_EMOJIS = ["💀", "❌", "🔥"]
FLOOD_LIMIT = 4  # Messages in 5 seconds for flood detection

# === File Setup ===
for file in [AUTH_FILE, USER_STORE, STATS_FILE]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f) if file != STATS_FILE else json.dump({'warns': {}, 'bans': {}} , f)

def load_auth_users():
    with open(AUTH_FILE, 'r') as f:
        return json.load(f)

def save_auth_users(users):
    with open(AUTH_FILE, 'w') as f:
        json.dump(users, f)

def load_user_messages():
    with open(USER_STORE, 'r') as f:
        return json.load(f)

def save_user_messages(data):
    with open(USER_STORE, 'w') as f:
        json.dump(data, f)

def load_stats():
    with open(STATS_FILE, 'r') as f:
        return json.load(f)

def save_stats(data):
    with open(STATS_FILE, 'w') as f:
        json.dump(data, f)

def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API_URL}sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def delete_message(chat_id, message_id):
    requests.post(f"{TELEGRAM_API_URL}deleteMessage", json={
        "chat_id": chat_id,
        "message_id": message_id
    })

def unrestrict_user(chat_id, user_id):
    requests.post(f"{TELEGRAM_API_URL}unrestrictChatMember", json={
        "chat_id": chat_id,
        "user_id": user_id
    })

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    if 'message' in data:
        msg = data['message']
        user_id = str(msg['from']['id'])
        chat_id = msg['chat']['id']
        text = msg.get('text')
        message_id = msg['message_id']
        user_messages = load_user_messages()
        auth_users = load_auth_users()
        stats = load_stats()

        # === Flood Detection ===
        current_time = int(time.time())
        if user_id not in user_messages:
            user_messages[user_id] = []
        user_messages[user_id].append(current_time)
        user_messages[user_id] = [timestamp for timestamp in user_messages[user_id] if current_time - timestamp <= 5]
        
        # Flood control (4+ messages in 5s)
        if len(user_messages[user_id]) > FLOOD_LIMIT:
            delete_message(chat_id, message_id)
            send_message(chat_id, "Flooding detected! Please slow down.")
            return "ok", 200

        save_user_messages(user_messages)

        # === New Member Welcome ===
        if 'new_chat_members' in msg:
            new_user_id = str(msg['new_chat_members'][0]['id'])
            if new_user_id not in auth_users:
                # Restrict new user temporarily
                requests.post(f"{TELEGRAM_API_URL}restrictChatMember", json={
                    "chat_id": chat_id,
                    "user_id": new_user_id,
                    "permissions": {
                        "can_send_messages": False,
                        "can_send_media_messages": False,
                        "can_send_other_messages": False,
                        "can_add_web_page_previews": False
                    }
                })
                send_message(chat_id, f"Welcome new member! But {new_user_id} is restricted until authorized.")
        
        # === Auto-Link Deletion ===
        if text and "http" in text and user_id not in auth_users:
            delete_message(chat_id, message_id)
            send_message(chat_id, "Links are not allowed! Please refrain from sending links.")

        # === /warn Command ===
        if text.startswith("/warn") and (int(user_id) == OWNER_ID or int(user_id) in auth_users):
            target_user_id = str(msg['reply_to_message']['from']['id']) if 'reply_to_message' in msg else None
            if target_user_id:
                if target_user_id not in stats['warns']:
                    stats['warns'][target_user_id] = 0
                stats['warns'][target_user_id] += 1
                save_stats(stats)
                send_message(chat_id, f"User {target_user_id} warned. Total warnings: {stats['warns'][target_user_id]}")
                if stats['warns'][target_user_id] >= 3:
                    send_message(chat_id, f"User {target_user_id} has been banned for exceeding warning limit.")
                    requests.post(f"{TELEGRAM_API_URL}banChatMember", json={"chat_id": chat_id, "user_id": target_user_id})
                    stats['bans'][target_user_id] = stats['warns'].pop(target_user_id, None)
                    save_stats(stats)

        # === /ban Command ===
        if text.startswith("/ban") and (int(user_id) == OWNER_ID or int(user_id) in auth_users):
            target_user_id = str(msg['reply_to_message']['from']['id']) if 'reply_to_message' in msg else None
            if target_user_id:
                requests.post(f"{TELEGRAM_API_URL}banChatMember", json={"chat_id": chat_id, "user_id": target_user_id})
                send_message(chat_id, f"User {target_user_id} banned.")

        # === /unrestrict Command ===
        if text.startswith("/unrestrict") and (int(user_id) == OWNER_ID or int(user_id) in auth_users):
            target_user_id = str(msg['reply_to_message']['from']['id']) if 'reply_to_message' in msg else None
            if target_user_id:
                unrestrict_user(chat_id, target_user_id)
                send_message(chat_id, f"User {target_user_id} is now unrestricted.")

        # === /clean Command ===
        if text.startswith("/clean") and (int(user_id) == OWNER_ID or int(user_id) in auth_users):
            count = int(text.split()[1]) if len(text.split()) > 1 else 5
            for i in range(count):
                requests.post(f"{TELEGRAM_API_URL}deleteMessage", json={
                    "chat_id": chat_id,
                    "message_id": message_id - i
                })
            send_message(chat_id, f"Deleted last {count} messages.")

        # === /id Command ===
        if text == "/id":
            send_message(chat_id, f"User ID: {user_id}, Group ID: {chat_id}")

        # === /auth Command (Authorization) ===
        if text == "/auth" and int(user_id) == OWNER_ID:
            target_user_id = str(msg['reply_to_message']['from']['id']) if 'reply_to_message' in msg else None
            if target_user_id:
                auth_users.append(int(target_user_id))
                save_auth_users(auth_users)
                send_message(chat_id, f"User {target_user_id} is now authorized.")
        
        return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
