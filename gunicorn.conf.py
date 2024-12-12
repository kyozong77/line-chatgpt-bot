import multiprocessing
import os
from gevent import monkey
monkey.patch_all()

# 從環境變量獲取端口
port = os.getenv('PORT', '8080')
bind = f"0.0.0.0:{port}"

# 減少工作進程數，提高穩定性
workers = 2
worker_class = "gevent"
worker_connections = 1000

# 增加超時時間
timeout = 120
graceful_timeout = 60
keepalive = 5

# 調整請求限制
max_requests = 500
max_requests_jitter = 100

# 日誌配置
accesslog = "-"  # 輸出到 stdout
errorlog = "-"   # 輸出到 stderr
loglevel = "info"
capture_output = True
enable_stdio_inheritance = True

# 進程名稱
proc_name = "line-bot"

# 預加載應用
preload_app = False  # 改為 False 以提高穩定性

# 守護進程模式
daemon = False

# 優雅重啟
graceful_timeout = 60

# 性能調優
backlog = 1024
keepalive = 5
threads = 1

# 錯誤處理
capture_output = True
enable_stdio_inheritance = True

# 環境變數
raw_env = [
    f"LINE_CHANNEL_SECRET={os.getenv('LINE_CHANNEL_SECRET', '')}",
    f"LINE_CHANNEL_ACCESS_TOKEN={os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')}",
    f"OPENAI_API_KEY={os.getenv('OPENAI_API_KEY', '')}",
    f"OPENWEATHER_API_KEY={os.getenv('OPENWEATHER_API_KEY', '')}",
    f"REDIS_HOST={os.getenv('REDIS_HOST', 'redis')}",
    f"REDIS_PORT={os.getenv('REDIS_PORT', '6379')}",
    f"REDIS_PASSWORD={os.getenv('REDIS_PASSWORD', '')}"
]
