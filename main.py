import os
import json
import requests
from flask import Flask, request
from dotenv import load_dotenv
import openai

# .env 読み込み
load_dotenv()
GAS_BASE_URL = os.environ.get("GAS_BASE_URL")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Flask アプリの初期化
app = Flask(__name__)

@app.route("/")
def index():
    return "Hello from Render LINE Bot!"

# ChatGPTの応答を生成する関数
def get_chatgpt_response(user_input):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは優しい関西弁で答えるアシスタントです。"},
                {"role": "user", "content": user_input}
            ]
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print("OpenAI Error:", e)
        return "すまん、ちょっと今うまく返されへんみたいや"

# LINEのWebhook受信
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

    # ChatGPTで返信を作成
    reply_text = get_chatgpt_response(user_message)
    reply_to_line(reply_token, reply_text)
    return "OK", 200

# LINEへ返信する関数
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

# 起動ポイント
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
