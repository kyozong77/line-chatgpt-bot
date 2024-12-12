# LINE ChatGPT Bot

這是一個整合了 LINE Messaging API 和 ChatGPT API 的聊天機器人專案。

## 安裝步驟

1. 安裝所需套件：
   ```bash
   pip install -r requirements.txt
   ```

2. 設定環境變數：
   - 複製 `.env` 文件並填入你的 API 密鑰：
     - LINE_CHANNEL_SECRET：從 LINE Developers Console 獲取
     - LINE_CHANNEL_ACCESS_TOKEN：從 LINE Developers Console 獲取
     - OPENAI_API_KEY：從 OpenAI 網站獲取

3. 運行應用：
   ```bash
   python app.py
   ```

4. 使用 ngrok 或其他工具設定 HTTPS 網址，並在 LINE Developers Console 設定 Webhook URL：
   ```bash
   ngrok http 5000
   ```

## 功能

- 接收用戶在 LINE 上發送的訊息
- 使用 ChatGPT API 處理訊息
- 將 ChatGPT 的回應發送回 LINE

## 注意事項

- 請確保將 `.env` 文件加入 .gitignore
- 需要有穩定的網路連接
- 請注意 OpenAI API 的使用額度
