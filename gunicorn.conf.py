import os

# 基本配置
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
workers = 1
worker_class = "sync"
timeout = 120

# 日誌
accesslog = "-"
errorlog = "-"
loglevel = "debug"  # 改為 debug 以獲取更多信息

# 進程
daemon = False
preload_app = True

# 請求處理
forwarded_allow_ips = '*'
proxy_allow_ips = '*'
