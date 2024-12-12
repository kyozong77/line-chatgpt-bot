import redis
import requests
import os
from dotenv import load_dotenv
import openai

def test_redis():
    try:
        r = redis.Redis(host='redis', port=6379, db=0)
        return r.ping()
    except Exception as e:
        return f"Redis connection failed: {str(e)}"

def test_line_api():
    try:
        token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        headers = {
            'Authorization': f'Bearer {token}'
        }
        response = requests.get('https://api.line.me/v2/bot/info', headers=headers)
        return response.status_code == 200
    except Exception as e:
        return f"LINE API connection failed: {str(e)}"

def test_openai():
    try:
        openai.api_key = os.getenv('OPENAI_API_KEY')
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt="Hello",
            max_tokens=5
        )
        return True
    except Exception as e:
        return f"OpenAI connection failed: {str(e)}"

def main():
    load_dotenv()
    
    print("Testing connections...")
    print(f"Redis: {test_redis()}")
    print(f"LINE API: {test_line_api()}")
    print(f"OpenAI: {test_openai()}")

if __name__ == "__main__":
    main()
