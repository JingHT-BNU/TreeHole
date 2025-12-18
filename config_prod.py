# config_prod.py
import os

# 安全密钥（生成一个新的）
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secure-production-key-change-this')

# 关闭调试模式
DEBUG = False

# 数据库配置
basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'database.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# 文件上传配置
UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

# 管理员IP配置（设置为树莓派局域网IP或特定管理员IP）
ADMIN_IP = ['172.23.1.107', '127.0.0.1']

# 服务器配置
HOST = '0.0.0.0'
PORT = 80  # 使用非标准端口，避免权限问题