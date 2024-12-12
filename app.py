from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import TextMessage, ReplyMessageRequest
from linebot.v3.exceptions import InvalidSignatureError
from dotenv import load_dotenv
import openai
import os
import logging
from logging.handlers import RotatingFileHandler

# 載入環境變數
load_dotenv()

# 初始化 Flask
app = Flask(__name__)

# 設定日誌
logger = logging.getLogger('line_bot')
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('logs/line_bot.log', maxBytes=10000000, backupCount=5)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
logger.addHandler(handler)

# LINE Bot 設定
configuration = Configuration(access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 初始化 LINE Bot API
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)

# OpenAI 設定
openai.api_key = os.getenv('OPENAI_API_KEY')

def get_openai_response(message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": message}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return "抱歉，我現在無法回應，請稍後再試。"

@app.route("/callback", methods=['POST'])
def callback():
    # 獲取 X-Line-Signature header 值
    signature = request.headers['X-Line-Signature']

    # 獲取請求體文字
    body = request.get_data(as_text=True)
    logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    try:
        # 使用 OpenAI 生成回應
        response_text = get_openai_response(event.message.text)
        reply_message = TextMessage(text=response_text)
        
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[reply_message]
            )
        )
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")

@app.route("/health", methods=['GET'])
def health():
    return 'OK'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
