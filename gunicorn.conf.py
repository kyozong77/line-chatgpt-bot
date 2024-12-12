import os

# 基本配置
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
workers = 1
worker_class = "sync"
timeout = 120

# 日誌
accesslog = "-"
errorlog = "-"
loglevel = "info"

# 進程
daemon = False
preload_app = False
