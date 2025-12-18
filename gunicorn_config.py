# gunicorn_config.py
import multiprocessing

# 绑定地址
bind = "0.0.0.0:80"

# 工作进程数 (建议为CPU核心数*2+1)
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = 'gevent'

# 每个工作进程的最大客户端连接数
worker_connections = 1000

# 超时设置
timeout = 30
keepalive = 2

# 日志配置
accesslog = '/var/log/treehole/access.log'
errorlog = '/var/log/treehole/error.log'
loglevel = 'info'

# 进程名称
proc_name = 'treehole_app'

# 防止启动时出现文件描述符错误
limit_request_field_size = 8190