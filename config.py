import os

# 基础配置
SECRET_KEY = 'AMTqS1YhniAkSB1jLr78S789wae3mS3CjcM4uFH92Uo='
DEBUG = True

# 数据库配置
basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'database.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# 文件上传配置
UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB最大文件大小

ADMIN_IP = ['172.23.1.107', '127.0.0.1']