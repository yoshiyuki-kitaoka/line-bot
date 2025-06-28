# main.py
import os
import openai
from flask import Flask, request, abort
from dotenv import load_dotenv

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# .env 読み込み
load_dotenv()

app = Flask(__name__)

# 環境変数から読み込み
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# LINE APIとOpenAI API設定
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

@app.route("/callback", methods=["POST"])
def callback():
    # Webhookの署名検証
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# LINEからのメッセージイベントを処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text

    # OpenAIに問い合わせる
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # 必要に応じて gpt-4 に変更
        messages=[
            {"role": "system", "content": "あなたは親しみやすく自然な受け答えをするアシスタントです。"},
            {"role": "user", "content": user_text}
        ]
    )

    reply_text = response.choices[0].message["content"].strip()

    # LINEへ返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()

