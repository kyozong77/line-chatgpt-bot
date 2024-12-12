FROM python:3.9-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 設置 Python 環境
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

# 安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf ~/.cache/pip/*

# 創建日誌目錄
RUN mkdir -p /app/logs && chmod 777 /app/logs

# 複製應用代碼
COPY . .

# 健康檢查（增加超時時間）
HEALTHCHECK --interval=30s --timeout=60s --start-period=30s --retries=5 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# 使用 gunicorn 運行應用
CMD ["sh", "-c", "gunicorn --config gunicorn.conf.py --timeout 120 app:app"]
