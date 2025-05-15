from flask import Flask, request
import requests, json, os, time
from utils import send_message, delete_message, send_buttons

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = 6356015122
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

AUTH_FILE = "auth_users.json"
for file in [AUTH_FILE]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump([], f)

def load_auth_users():
    with open(AUTH_FILE, 'r') as f:
        return json.load(f)

def save_auth_users(users):
    with open(AUTH_FILE, 'w') as f:
        json.dump(users, f)

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "")
        
        # /auth button trigger
        if text == "/auth" and "reply_to_message" in msg and user_id == OWNER_ID:
            target = msg["reply_to_message"]["from"]["id"]
            send_buttons(chat_id, f"Authorize user {target}?", [
                {"text": "✅ Confirm Auth", "callback_data": f"confirm_auth:{target}"},
                {"text": "❌ Cancel", "callback_data": "cancel"}
            ])
        
        if text == "/unauth" and "reply_to_message" in msg and user_id == OWNER_ID:
            target = msg["reply_to_message"]["from"]["id"]
            send_buttons(chat_id, f"Unauthorize user {target}?", [
                {"text": "✅ Confirm Unauth", "callback_data": f"confirm_unauth:{target}"},
                {"text": "❌ Cancel", "callback_data": "cancel"}
            ])

    elif "callback_query" in data:
        query = data["callback_query"]
        user_id = query["from"]["id"]
        data_str = query["data"]
        chat_id = query["message"]["chat"]["id"]
        message_id = query["message"]["message_id"]

        auth_users = load_auth_users()

        if data_str.startswith("confirm_auth:") and user_id == OWNER_ID:
            target_id = int(data_str.split(":")[1])
            if target_id not in auth_users:
                auth_users.append(target_id)
                save_auth_users(auth_users)
                send_message(chat_id, f"✅ User {target_id} authorized.")
        elif data_str.startswith("confirm_unauth:") and user_id == OWNER_ID:
            target_id = int(data_str.split(":")[1])
            if target_id in auth_users:
                auth_users.remove(target_id)
                save_auth_users(auth_users)
                send_message(chat_id, f"❌ User {target_id} unauthorized.")
        elif data_str == "cancel":
            requests.post(f"{API_URL}editMessageText", json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": "Action cancelled."
            })

    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
