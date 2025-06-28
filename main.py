from flask import Flask, request, abort
import os
import openai
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

print("🔥 起動したでぇ（これはmain.pyや）")

# Flaskアプリ作成
app = Flask(__name__)

# 環境変数からトークン類を読み込み
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 各種初期化
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    print("=== 環境変数チェック ===")
    print("OPENAI_API_KEY:", "あり" if OPENAI_API_KEY else "なし")
    print("LINE_CHANNEL_ACCESS_TOKEN:", "あり" if LINE_CHANNEL_ACCESS_TOKEN else "なし")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ Invalid signature")
        abort(400)

    return "OK", 200

# メッセージイベントに応答
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text

    try:
        # OpenAIと連携
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは親しみやすく、自然な日本語で対話するAIアシスタントです。"},
                {"role": "user", "content": user_text}
            ]
        )

        reply_text = response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("❌ OpenAIエラー:", e)
        reply_text = "ごめんなさい、うまく応答できませんでした。"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# Flask起動（Render対応）
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
