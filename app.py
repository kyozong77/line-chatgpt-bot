from flask import Flask, request, abort, jsonify
import os
import openai
import dropbox
from datetime import datetime
from dropbox.files import WriteMode, CreateFolderError
from dropbox.exceptions import ApiError
import requests
from dotenv import load_dotenv

from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent
)

load_dotenv()

app = Flask(__name__)

# LINE Bot configuration
configuration = Configuration(
    access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
)
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# OpenAI configuration
openai.api_key = os.getenv('OPENAI_API_KEY')

# Dropbox configuration
DROPBOX_APP_KEY = os.getenv('DROPBOX_APP_KEY')
DROPBOX_APP_SECRET = os.getenv('DROPBOX_APP_SECRET')
DROPBOX_FOLDER = '/家庭相簿'
DROPBOX_SHARE_URL = 'https://www.dropbox.com/scl/fo/mreawj5sy70nj99fgz3wq/AFNjwBnR1TVitYnhLVpSuGU?rlkey=7dr1bsfas0idpn2l7tx2556ui&st=nvu968nl&dl=0'

# 初始化 Dropbox OAuth2 流程
dbx = dropbox.Dropbox(
    oauth2_refresh_token=os.getenv('DROPBOX_REFRESH_TOKEN'),
    app_key=DROPBOX_APP_KEY,
    app_secret=DROPBOX_APP_SECRET
)

def save_to_dropbox(image_content, filename):
    """將圖片保存到 Dropbox"""
    try:
        # 確保資料夾存在
        try:
            dbx.files_create_folder_v2(DROPBOX_FOLDER)
        except ApiError as e:
            if not isinstance(e.error, CreateFolderError) or \
               not e.error.is_path() or \
               not e.error.get_path().is_conflict():
                raise
        
        # 上傳文件
        file_path = f"{DROPBOX_FOLDER}/{filename}"
        dbx.files_upload(
            image_content,
            file_path,
            mode=WriteMode('overwrite')
        )
        return True
    except ApiError as e:
        app.logger.error(f"Dropbox API error: {e}")
        return False

def get_openai_response(text):
    """獲取 OpenAI 回應"""
    try:
        # 限制輸入文字長度
        if len(text) > 1000:
            text = text[:1000] + "..."
            
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """你是一個友善、幽默的聊天機器人。
                - 用輕鬆、自然的語氣交談
                - 回應要簡潔有趣
                - 可以適當使用表情符號
                - 避免過於正式或機械化的回答
                - 如果不確定的事情，要誠實說不知道
                - 注意保持對話的安全性和適當性"""},
                {"role": "user", "content": text}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        app.logger.error(f"OpenAI API error: {e}")
        return "抱歉，我現在無法回應，請稍後再試。"

def download_line_content(message_id):
    """下載 LINE 消息內容"""
    try:
        with ApiClient(configuration) as api_client:
            messaging_api = MessagingApi(api_client)
            message_content = messaging_api.get_message_content(message_id)
            return message_content.content
    except Exception as e:
        app.logger.error(f"Error downloading content: {e}")
        return None

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    if not signature:
        abort(400, description='X-Line-Signature header is missing')

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature")
        abort(400, description='Invalid signature')
    except Exception as e:
        app.logger.error(f"Webhook handling error: {e}")
        abort(500, description='Internal server error')

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    """處理文字消息"""
    try:
        text = event.message.text
        
        # 檢查是否是"存相簿"命令
        if text == "存相簿" and DROPBOX_SHARE_URL:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=f"這是您的相簿連結：\n{DROPBOX_SHARE_URL}")]
                    )
                )
            return

        # 檢查是否有人@機器人
        if '@' in text:
            # 移除 @ 和機器人名稱，只保留實際問題
            actual_text = text.split(' ', 1)[1] if ' ' in text else text
            response_text = get_openai_response(actual_text)
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=response_text)]
                    )
                )
    except Exception as e:
        app.logger.error(f"Error handling text message: {e}")
        try:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="抱歉，處理消息時發生錯誤。")]
                    )
                )
        except:
            pass

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    """處理圖片消息 - 不做任何動作"""
    pass

@app.route("/", methods=['GET'])
def home():
    return jsonify({
        "status": "running",
        "message": "LINE Bot is running!"
    })

@app.route("/health", methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "message": "OK"
    })

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
