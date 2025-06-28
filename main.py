from flask import Flask, request, abort
import os
import requests
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton, MessageAction
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

# --- ユーザーの状態を管理する辞書 ---
# 本来はデータベースなどを使うべきですが、簡易的にメモリ上で管理します。
# アプリケーションが再起動するとリセットされる点に注意してください。
# キー: user_id, 値: 現在のユーザーの状態 (例: "waiting_for_reason", "normal")
user_states = {}

# --- 直前の質問を保存する辞書 ---
# キー: user_id, 値: 直前にユーザーに送った質問内容
last_questions = {}

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
    reply_token = event.reply_token

    # ユーザーの現在の状態を取得
    current_state = user_states.get(user_id, "normal")
    
    # 直前の質問内容を取得（理由記述に使うため）
    previous_question = last_questions.get(user_id, "（不明な質問）")

    # フィードバックと送信タイプを初期化
    feedback_text = ""
    send_type = "text" # GASに送るtypeを初期化

    # --- 状態に応じた処理 ---
    if current_state == "waiting_for_reason":
        # 理由記述を受け取った場合の処理
        print(f"🔄 ユーザー {user_id} は理由を記述中...")
        question_for_gas = previous_question # 直前の質問を記録する
        answer_for_gas = user_message # 理由が回答になる
        send_type = "reason" # GASにはtypeを"reason"として送信

        # OpenAIにフィードバックを依頼（理由記述用プロンプト）
        prompt = f"以下は、ユーザーが選択肢を選んだ理由です。共感しながらも視点を広げるフィードバックを80〜100文字でください。\n\n理由: {user_message}"
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたはユーザーの成長を応援するフィードバックコーチです。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=120, # 少し長めに設定
                temperature=0.7
            )
            feedback_text = response.choices[0].message.content.strip()
        except Exception as e:
            feedback_text = "（OpenAIでの理由フィードバック生成に失敗しました）"
            print("⚠️ OpenAI理由フィードバックエラー:", e)

        # 状態をリセット
        user_states[user_id] = "normal"
        del last_questions[user_id] # 直前の質問もクリア

    else:
        # 通常の質問回答を受け取った場合の処理（選択肢を含む質問を想定）
        print(f"💬 ユーザー {user_id} は通常のメッセージを送信: {user_message}")
        question_for_gas = "今日の問い" # 固定値。必要に応じて動的に変更してください
        answer_for_gas = user_message # 選択肢の番号、または通常の回答がここに入る

        # ここで、ユーザーのメッセージが「選択肢の番号」かどうかを判断する必要があります
        # 例: "1", "2", "3" のいずれか
        # 実際には「今日の問い」の質問タイプ (select/text) を知る必要がありますが、
        # ここでは簡易的にユーザーメッセージが数字かどうかで判断します。
        # より堅牢にするには、`sendDailyQuestions`関数で送った質問タイプを保持し、
        # ここでそのタイプを参照するように実装する必要があります。
        if user_message.isdigit() and 1 <= int(user_message) <= 3: # 選択肢が3つある場合
            send_type = "select" # GASにはtypeを"select"として送信
            # OpenAIにフィードバックを依頼（選択肢の番号に対するフィードバックはGAS側で行うため、ここでは行わない）
            feedback_text = "選択肢のフィードバックと理由の問いかけをします..." # 仮のメッセージ
        else:
            send_type = "text" # GASにはtypeを"text"として送信
            # OpenAIにフィードバックを依頼（一般的な記述式用プロンプト）
            prompt = f"ユーザーの回答:「{user_message}」に対して、共感しつつ1～2文で優しく丁寧なフィードバックをしてください。"
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
                feedback_text = response.choices[0].message.content.strip()
            except Exception as e:
                feedback_text = "（OpenAIの応答に失敗しました）"
                print("⚠️ OpenAIエラー:", e)
    
    # --- LINEに返信 ---
    # GASからのフィードバック（テキスト）を待つ
    line_reply_message = []

    # GASに記録し、フィードバックを受け取る
    try:
        payload = {
            "user_id": user_id,
            "question": question_for_gas,
            "answer": answer_for_gas,
            "type": send_type # ★ここが重要：GASにタイプを伝える
        }
        headers = {"Content-Type": "application/json"}
        res = requests.post(GAS_BASE_URL, json=payload, headers=headers)
        
        # GASからのJSONレスポンスをパース
        gas_response_json = res.json()
        if gas_response_json.get("status") == "success":
            feedback_text_from_gas = gas_response_json.get("feedback", "フィードバックなし")
            print(f"✅ GASからのフィードバック受信: {feedback_text_from_gas}")
            feedback_text = feedback_text_from_gas # GASからのフィードバックを優先
        else:
            print(f"❌ GASからのエラー応答: {gas_response_json.get('message', '不明なエラー')}")
            feedback_text = f"GASエラー: {gas_response_json.get('message', '不明なエラー')}"

    except Exception as e:
        print("⚠️ GAS連携エラー:", e)
        feedback_text = "（GASとの連携に失敗しました）"

    # LINEへの最終的な返信メッセージを構築
    line_reply_message.append(TextSendMessage(text=f"📩 フィードバック：\n{feedback_text}"))

    # もし「選択」タイプで、かつGASからのフィードバックに「理由の問いかけ」が含まれる場合、
    # ユーザーの状態を「理由待ち」に更新し、次のメッセージで理由を促す
    if send_type == "select" and "ちなみに、そう思った理由って何かありますか？" in feedback_text:
        user_states[user_id] = "waiting_for_reason"
        last_questions[user_id] = question_for_gas # 質問内容を保存
        line_reply_message.append(TextSendMessage(text="💡 よろしければ、そう思った理由を教えてくださいね！"))
        print(f"🔄 ユーザー {user_id} の状態を 'waiting_for_reason' に設定")
    
    # LINEに返信
    line_bot_api.reply_message(reply_token, line_reply_message)


# --- Flask起動（Render用）---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
