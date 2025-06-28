from flask import Flask, request, abort
import os
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

print("🔥 起動したでぇ（これはmain.pyや）")

# Flaskアプリ作成
app = Flask(__name__)

# 環境変数からLINEのトークンとシークレットを読み込む
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# LINE APIクライアント初期化
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Webhook受け取りエンドポイント
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    print("=== 環境変数チェック ===")
    print("OPENAI_API_KEY:", "あり" if os.getenv("OPENAI_API_KEY") else "なし")
    print("LINE_CHANNEL_ACCESS_TOKEN:", "あり" if LINE_CHANNEL_ACCESS_TOKEN else "なし")
    print("PORT:", os.getenv("PORT", "不明"))

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ Invalid signature")
        abort(400)

    return "OK", 200

# メッセージイベント（テキスト）に反応
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    reply_text = f"あなたはこう言いました：{user_message}"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# Flaskアプリの起動（Render用）
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
