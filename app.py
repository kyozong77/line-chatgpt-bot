from flask import Flask, request, abort, jsonify

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
    TextMessageContent
)

import os
import openai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# LINE Bot configuration
configuration = Configuration(
    access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
)
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# OpenAI configuration
openai.api_key = os.getenv('OPENAI_API_KEY')

def get_openai_response(text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": text}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        app.logger.error(f"OpenAI API error: {e}")
        return "抱歉，我現在無法回應，請稍後再試。"

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers.get('X-Line-Signature')
    if not signature:
        abort(400, description='X-Line-Signature header is missing')

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
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
def handle_message(event):
    try:
        # Get response from OpenAI
        response_text = get_openai_response(event.message.text)
        
        # Reply to user
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=response_text)]
                )
            )
    except Exception as e:
        app.logger.error(f"Error handling message: {e}")

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

@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 400

@app.errorhandler(404)
def not_found(e):
    return jsonify(error="Not found"), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify(error="Internal server error"), 500

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
