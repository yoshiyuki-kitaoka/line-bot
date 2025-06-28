from flask import Flask, request, abort
import os
import requests
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from openai import OpenAI

print("🔥 起動したでぇ（これはmain.pyや）")

app = Flask(__name__)

# 環境変数
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GAS_BASE_URL = os.getenv("GAS_BASE_URL")

print("🔑 読み込んだAPIキー:", OPENAI_API_KEY)

# LINE Bot初期化
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# OpenAIクライアント初期化
client = OpenAI(api_key=OPENAI_API_KEY)

# --- Webhook受信エンドポイント ---
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ Invalid signature")
        abort(400)

    return "OK", 200

# --- メッセージ受信処理 ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    user_id = event.source.user_id
    question = "今日の問い"

    # OpenAIにフィードバックを依頼
    prompt = f"ユーザーの回答:「{user_message}」に対して、共感しつつ1～2文で優しく丁寧なフィードバックをしてください。"
    feedback = ""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたはユーザーの成長を応援するフィードバックコーチです。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7
        )
        feedback = response.choices[0].message.content.strip()
    except Exception as e:
        feedback = "（OpenAIの応答に失敗しました）"
        print("⚠️ OpenAIエラー:", e)

    # LINEに返信
    reply_text = f"📩 フィードバック：\n{feedback}"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

    # GASに記録
    try:
        payload = {
            "user_id": user_id,
            "question": question,
            "answer": user_message,
            "feedback": feedback
        }
        headers = {"Content-Type": "application/json"}
        res = requests.post(GAS_BASE_URL, json=payload, headers=headers)
        print(f"✅ GASに全データ送信完了: {res.text}")
    except Exception as e:
        print("⚠️ GAS連携エラー:", e)

# --- Flask起動（Render用）---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
