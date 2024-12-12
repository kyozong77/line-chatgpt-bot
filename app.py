from flask import Flask, request, abort, jsonify
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.webhooks import MessageEvent, TextMessageContent, StickerMessageContent, ImageMessageContent
from linebot.v3.messaging import TextMessage, StickerMessage, ReplyMessageRequest
from linebot.v3.exceptions import InvalidSignatureError
import openai
from dotenv import load_dotenv
import os
import json
import time
from datetime import datetime
import pytz
from langdetect import detect
from deep_translator import GoogleTranslator
import redis
import requests
import logging
from logging.handlers import RotatingFileHandler
import signal
import functools
from threading import Thread

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

# 使用單例模式管理 LINE Bot API 客戶端
class LineBotApi:
    _instance = None
    _api_client = None
    _messaging_api = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if self._api_client is None:
            self._api_client = ApiClient(configuration)
            self._messaging_api = MessagingApi(self._api_client)

    def get_api(self):
        return self._messaging_api

    def __del__(self):
        if self._api_client:
            self._api_client.close()

def get_line_bot_api():
    return LineBotApi.get_instance().get_api()

# OpenAI 設定
if not os.getenv('OPENAI_API_KEY'):
    raise ValueError("OPENAI_API_KEY environment variable is not set")
openai.api_key = os.getenv('OPENAI_API_KEY')

# Redis 設定
redis_url = os.getenv('REDIS_URL')
if redis_url:
    # 使用 REDIS_URL（Zeabur 提供的格式）
    redis_client = redis.from_url(redis_url, decode_responses=True)
else:
    # 本地開發環境
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        password=os.getenv('REDIS_PASSWORD'),
        decode_responses=True
    )

# 全域變數
MAX_HISTORY = 10
MAX_RETRIES = 3
RETRY_DELAY = 1
DEFAULT_LANGUAGE = 'zh-tw'

# 用戶設定和對話歷史
user_settings = {}
conversation_history = {}

def get_weather(city):
    """獲取天氣信息"""
    api_key = os.getenv('OPENWEATHER_API_KEY')
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=zh_tw"
    
    try:
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200:
            temp = data['main']['temp']
            humidity = data['main']['humidity']
            desc = data['weather'][0]['description']
            return f"🌡️ 溫度: {temp}°C\n💧 濕度: {humidity}%\n🌤️ 天氣: {desc}"
    except Exception as e:
        logger.error(f"Weather API error: {str(e)}")
        return "抱歉，無法獲取天氣信息。"

def detect_language(text):
    """檢測文本語言"""
    try:
        return detect(text)
    except:
        return DEFAULT_LANGUAGE

def translate_text(text, target_lang='zh-TW'):
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        return translator.translate(text)
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return text

def save_conversation(user_id, message_data):
    """保存對話歷史到 Redis"""
    try:
        key = f"chat_history:{user_id}"
        redis_client.lpush(key, json.dumps(message_data))
        redis_client.ltrim(key, 0, MAX_HISTORY - 1)
    except Exception as e:
        logger.error(f"Redis save error: {str(e)}")

def get_conversation_history(user_id):
    """從 Redis 獲取對話歷史"""
    try:
        key = f"chat_history:{user_id}"
        history = redis_client.lrange(key, 0, -1)
        # 由於使用 lpush 存儲，需要反轉順序以獲得正確的時間順序
        return list(reversed([json.loads(item) for item in history]))
    except Exception as e:
        logger.error(f"Redis get error: {str(e)}")
        return []

def handle_command(text, user_id):
    """處理特殊命令"""
    if text.startswith('/'):
        parts = text.lower().split()
        command = parts[0]
        
        if command == '/lang':
            if len(parts) > 1:
                new_lang = parts[1]
                user_settings[user_id] = {'language': new_lang}
                return f"已將回應語言設置為: {new_lang}"
            return "請指定語言，例如：/lang en"
            
        elif command == '/search':
            if len(parts) > 1:
                keyword = ' '.join(parts[1:])
                history = get_conversation_history(user_id)
                results = []
                for item in history:
                    if keyword in item['user'] or keyword in item['assistant']:
                        results.append(f"Q: {item['user']}\nA: {item['assistant']}\n")
                if results:
                    return "搜尋結果：\n\n" + "\n".join(results)
                return "找不到相關對話。"
            return "請指定搜尋關鍵字，例如：/search 天氣"
            
        return "未知的命令。可用命令：\n/lang [語言代碼] - 設置語言\n/search [關鍵字] - 搜尋歷史對話"
    
    # 處理天氣查詢
    if text.startswith('天氣'):
        parts = text.split()
        if len(parts) > 1:
            city = ' '.join(parts[1:])
            return get_weather(city)
        return "請輸入城市名稱，例如：天氣 台北"
    
    return None

def get_openai_response(messages):
    try:
        # 設置超時和重試
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=250,
            presence_penalty=0.3,
            frequency_penalty=0.5,
            timeout=30,  # 30 秒超時
            request_timeout=30,  # 請求超時
        )
        return response.choices[0].message['content'].strip()
    except openai.error.Timeout:
        logger.error("OpenAI API timeout")
        return "抱歉，回應時間過長，請稍後再試。"
    except openai.error.APIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return "抱歉，API 發生錯誤，請稍後再試。"
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return "抱歉，我好像卡住了，等一下再聊吧！"

def get_gpt4_response(user_id, user_message, retry_count=0):
    try:
        # 檢查命令
        command_response = handle_command(user_message, user_id)
        if command_response:
            return command_response
        
        # 檢測語言
        detected_lang = detect_language(user_message)
        if detected_lang != 'zh':
            translated_message = translate_text(user_message)
            user_message = f"{user_message}\n(翻譯: {translated_message})"
        
        # 獲取歷史對話
        history = get_conversation_history(user_id)
        recent_history = history[-5:] if len(history) > 5 else history
        
        # 分析最近的對話主題
        recent_topics = []
        for chat in recent_history:
            # 提取關鍵詞或主題（這裡可以根據需要增加更複雜的分析）
            topics = chat['user'].split()[:3]  # 簡單取前三個詞作為主題
            recent_topics.extend(topics)
        
        # 構建對話
        messages = [
            {
                "role": "system",
                "content": f"""你是一個友善的對話夥伴，請注意：
- 使用自然的繁體中文聊天
- 最近聊過的話題：{', '.join(recent_topics)}
- 回應時要考慮上下文，適時提及之前聊過的內容
- 保持對話的連貫性，但不要過度正式"""
            }
        ]
        
        # 添加歷史對話
        for chat in recent_history:
            messages.append({"role": "user", "content": chat['user']})
            messages.append({"role": "assistant", "content": chat['assistant']})
        
        messages.append({"role": "user", "content": user_message})
        
        # 調用 API
        response = get_openai_response(messages)
        
        # 保存對話
        save_conversation(user_id, {
            'user': user_message,
            'assistant': response,
            'timestamp': datetime.now(pytz.utc).isoformat()
        })
        
        return response
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if retry_count < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
            return get_gpt4_response(user_id, user_message, retry_count + 1)
        return "抱歉，我好像卡住了，等一下再聊吧！"

def should_respond(message):
    """
    判斷是否需要回應用戶的消息
    """
    # 如果消息為空，不回應
    if not message or message.isspace():
        return False, ""
        
    # 如果是系統命令，直接回應
    if message.startswith('/'):
        return True, message
        
    # 如果是天氣查詢，直接回應
    if message.startswith('天氣'):
        return True, message
        
    # 其他情況都回應
    return True, message

def timeout(seconds=0, minutes=0, hours=0):
    """
    Add a signal-based timeout to any function.
    Usage:
    @timeout(seconds=5)
    def my_slow_function(...)
    Args:
    - seconds: The time limit, in seconds.
    - minutes: The time limit, in minutes.
    - hours: The time limit, in hours.
    """
    limit = seconds + 60 * minutes + 3600 * hours

    def decorator(func):
        def handler(signum, frame):
            raise TimeoutError("timed out after {} seconds".format(limit))

        def wrapper(*args, **kwargs):
            try:
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(limit)
                result = func(*args, **kwargs)
                signal.alarm(0)
                return result
            except TimeoutError as exc:
                raise exc
            finally:
                signal.signal(signal.SIGALRM, signal.SIG_IGN)

        return wrapper

    return decorator

# 添加 Redis 隊列處理
def queue_message_processing(user_id, message, reply_token):
    try:
        task_data = {
            'user_id': user_id,
            'message': message,
            'reply_token': reply_token,
            'timestamp': time.time()
        }
        redis_client.lpush('message_queue', json.dumps(task_data))
        app.logger.info(f"Message queued for processing: {task_data}")
        return True
    except Exception as e:
        app.logger.error(f"Error queuing message: {str(e)}")
        return False

def process_message_queue():
    while True:
        try:
            # 從隊列中獲取消息
            task_data_raw = redis_client.brpop('message_queue', timeout=1)
            if not task_data_raw:
                continue

            task_data = json.loads(task_data_raw[1])
            user_id = task_data['user_id']
            message = task_data['message']
            reply_token = task_data['reply_token']
            
            # 檢查令牌是否過期（LINE token 30分鐘後過期）
            if time.time() - task_data['timestamp'] > 1700:  # 給點緩衝，設為1700秒
                app.logger.warning(f"Skipping expired token: {reply_token}")
                continue

            try:
                # 處理消息
                response = get_gpt4_response(user_id, message)
                
                # 發送回覆
                line_bot_api = get_line_bot_api()
                line_bot_api.push_message(
                    user_id,
                    TextMessage(text=response)
                )
                app.logger.info(f"Successfully processed and sent response to {user_id}")
                
            except Exception as e:
                app.logger.error(f"Error processing queued message: {str(e)}")
                try:
                    # 發送錯誤通知
                    line_bot_api = get_line_bot_api()
                    line_bot_api.push_message(
                        user_id,
                        TextMessage(text="抱歉，處理您的訊息時發生錯誤，請稍後再試。")
                    )
                except:
                    app.logger.error("Failed to send error message to user")
                    
        except Exception as e:
            app.logger.error(f"Queue processing error: {str(e)}")
            time.sleep(1)  # 避免過度消耗資源

@app.route("/callback", methods=['POST'])
def callback():
    # 獲取 X-Line-Signature header 值
    signature = request.headers['X-Line-Signature']

    # 獲取請求體的文本
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        # 驗證簽名
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    try:
        user_id = event.source.user_id
        text = event.message.text.strip()
        
        # 處理用戶消息並獲取回應
        response = process_user_message(text, user_id)
        
        # 發送回應
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                event.reply_token,
                {
                    "messages": [{"type": "text", "text": response}]
                }
            )
            
    except Exception as e:
        app.logger.error(f"Error handling message: {str(e)}")
        # 發送錯誤消息給用戶
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                event.reply_token,
                {
                    "messages": [{"type": "text", "text": "抱歉，處理您的消息時發生錯誤。請稍後再試。"}]
                }
            )

@handler.add(MessageEvent, message=StickerMessageContent)
def handle_sticker_message(event):
    try:
        line_bot_api = get_line_bot_api()
        reply_message_request = ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[StickerMessage(
                package_id="11537",
                sticker_id="52002734"
            )]
        )
        line_bot_api.reply_message(
            reply_message_request=reply_message_request
        )
    except Exception as e:
        logger.error(f"Error in handle_sticker: {str(e)}")
        try:
            line_bot_api = get_line_bot_api()
            error_message_request = ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="抱歉，我暫時無法處理您的請求。請稍後再試。")]
            )
            line_bot_api.reply_message(
                reply_message_request=error_message_request
            )
        except Exception as e2:
            logger.error(f"Failed to send error message: {str(e2)}")

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    try:
        line_bot_api = get_line_bot_api()
        reply_message_request = ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text="收到您的圖片了！")]
        )
        line_bot_api.reply_message(
            reply_message_request=reply_message_request
        )
    except Exception as e:
        logger.error(f"Error in handle_image: {str(e)}")
        try:
            line_bot_api = get_line_bot_api()
            error_message_request = ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="抱歉，我暫時無法處理您的請求。請稍後再試。")]
            )
            line_bot_api.reply_message(
                reply_message_request=error_message_request
            )
        except Exception as e2:
            logger.error(f"Failed to send error message: {str(e2)}")

# 全局錯誤處理
@app.errorhandler(Exception)
def handle_error(error):
    logger.error(f"Unhandled error: {str(error)}", exc_info=True)
    return 'Internal Server Error', 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
