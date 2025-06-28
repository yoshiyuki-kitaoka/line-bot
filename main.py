import os
import json
import requests
from flask import Flask, request
from dotenv import load_dotenv
import openai
from datetime import datetime

# .env 読み込み
load_dotenv()
GAS_BASE_URL = os.environ.get("GAS_BASE_URL")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
openai.api_key = os.environ.get("OPENAI_API_KEY")

# 環境変数チェックログ
print("✅ 環境変数確認")
print(f"GAS_BASE_URL: {GAS_BASE_URL}")
print(f"LINE_TOKEN存在: {'Yes' if LINE_CHANNEL_ACCESS_TOKEN else 'No'}")
print(f"OpenAI API Key存在: {'Yes' if openai.api_key else 'No'}")

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello from Render LINE Bot!"

# ChatGPTの応答を取得
def get_chatgpt_response(user_input):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは優しい関西弁で答えるアシスタントです。"},
                {"role": "user", "content": user_input}
            ]
        )
        print("✅ OpenAIからの返答取得成功")
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print("❌ OpenAI Error:", e)
        return "すまん、ちょっと今うまく返されへんみたいや"

# 回答ログをGASへ送信
def send_to_gas(user_id, q_id, question, selected_option, reason_text):
    try:
        data = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "q_id": q_id,
            "question_text": question,
            "selected_option": selected_option,
            "reason_text": reason_text
        }
        print("📤 GASへ送信:", data)
        res = requests.post(GAS_BASE_URL, json=data)
        print("✅ GAS送信ステータス:", res.status_code)
    except Exception as e:
        print("❌ GAS送信エラー:", e)

# LINEのWebhook受信
@app.route("/callback", methods=["POST"])
def callback():
    body = request.json
    print("📩 LINE Webhook 受信:", json.dumps(body, indent=2, ensure_ascii=False))

    try:
        event = body['events'][0]
        reply_token = event['replyToken']
        user_message = event['message']['text']
        user_id = event['source']['userId']
    except Exception as e:
        print("❌ メッセージ解析エラー:", e)
        return 'error', 400

    reply_text = get_chatgpt_response(user_message)
    reply_to_line(reply_token, reply_text)

    # 仮にログを記録するなら（ここは適宜調整）
    send_to_gas(user_id, "q1", user_message, "選択肢A", reply_text)
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
    print("📨 LINE返信ステータス:", res.status_code)

# 起動チェック
print("🔥 起動したでぇ（これはmain.pyや）")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
