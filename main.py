import os
from flask import Flask, request
import requests
from dotenv import load_dotenv
import json

load_dotenv()
GAS_BASE_URL = os.environ.get("GAS_BASE_URL")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello from Render LINE Bot!"

@app.route("/callback", methods=["POST"])
def callback():
    body = request.json
    print("LINE Webhook received:", json.dumps(body, indent=2, ensure_ascii=False))

    try:
        event = body['events'][0]
        reply_token = event['replyToken']
        user_message = event['message']['text']
    except Exception as e:
        print("Error parsing message:", e)
        return 'error', 400

    reply_text = f"受け取ったで〜「{user_message}」やな！"
    reply_to_line(reply_token, reply_text)
    return "OK", 200

def reply_to_line(reply_token, message):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}]
    }
    res = requests.post(url, headers=headers, json=data)
    print("LINE reply status:", res.status_code)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
