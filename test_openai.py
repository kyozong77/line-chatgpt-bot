from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

def test_openai():
    try:
        client = OpenAI()
        
        # 測試一個簡單的完成請求
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=10
        )
        
        print("Success!")
        print(completion.choices[0].message.content)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    test_openai()
