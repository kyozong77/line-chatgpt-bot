import multiprocessing
import os
from gevent import monkey
monkey.patch_all()

# 從環境變量獲取端口
port = os.getenv('PORT', '8080')
bind = f"0.0.0.0:{port}"

# 工作進程數（根據 CPU 核心數調整）
workers = min(multiprocessing.cpu_count() + 1, 4)  # 最多 4 個進程

# 工作模式
worker_class = "gevent"
worker_connections = 1000

# 超時時間
timeout = 60
graceful_timeout = 30
keepalive = 2

# 最大請求數
max_requests = 1000
max_requests_jitter = 200

# 日誌配置
accesslog = "-"  # 輸出到 stdout
errorlog = "-"   # 輸出到 stderr
loglevel = "info"
capture_output = True
enable_stdio_inheritance = True

# 日誌格式（包含請求 ID）
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" request_id=%(U)s'

# 進程名稱
proc_name = "line-bot"

# 預加載應用
preload_app = True

# 守護進程模式
daemon = False

# 安全設置
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 優雅重啟
graceful_timeout = 30
timeout = 60

# 錯誤處理
capture_output = True
enable_stdio_inheritance = True

# 性能調優
backlog = 2048
max_requests = 1000
max_requests_jitter = 200
keepalive = 2
threads = 1

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
