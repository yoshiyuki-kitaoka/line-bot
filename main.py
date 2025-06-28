from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv
import os
import openai

# 環境変数読み込み
load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 各APIキーの設定
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

# Flaskアプリ起動
app = Flask(__name__)

# OpenAIとのやりとり関数
def get_openai_response(user_message):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # 必要があれば "gpt-4o" に変更
        messages=[
            {"role": "system", "content": "あなたは親しみやすく、フレンドリーなLINE Botです。"},
            {"role": "user", "content": user_message}
        ]
    )
    return response['choices'][0]['message']['content']

# LINE webhookの受け口
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# メッセージイベントの処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    reply_text = get_openai_response(user_text)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# ローカル実行用（Renderでは不要）
if __name__ == "__main__":
    app.run()
