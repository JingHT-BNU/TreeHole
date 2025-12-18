import argparse
import os
import uuid
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import ipaddress

app = Flask(__name__)
if os.environ.get('FLASK_ENV') == 'production':
    app.config.from_pyfile('config_prod.py')
else:
    app.config.from_pyfile('config.py')

# 数据库配置
db = SQLAlchemy(app)

# 确保上传文件夹存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.context_processor
def utility_processor():
    """注入函数到模板上下文"""
    return dict(is_admin_ip=is_admin_ip)

# 数据库模型
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(200))
    user_ip = db.Column(db.String(45), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_anonymous = db.Column(db.Boolean, default=True)
    # 可见性选项 (public, admin_only, private)
    visibility = db.Column(db.String(20), default='public')
    replies = db.relationship('Reply', backref='post', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'image_filename': self.image_filename,
            'user_ip': self.user_ip,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'reply_count': len(self.replies),
            'visibility': self.visibility
        }

class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_ip = db.Column(db.String(45), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)


# 辅助函数
def get_client_ip():
    """获取客户端IP地址"""
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0]
    else:
        ip = request.remote_addr
    return ip


def is_admin_ip(ip):
    """检查IP是否为管理员IP"""
    return ip in app.config['ADMIN_IP']


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# 创建数据库表
with app.app_context():
    db.create_all()


# 路由定义
@app.route('/')
def index():
    """首页 - 根据IP显示用户界面或管理员界面"""
    user_ip = get_client_ip()

    # 获取当前用户的所有帖子（包括所有可见性）
    user_posts = Post.query.filter_by(user_ip=user_ip).order_by(Post.created_at.desc()).all()

    # 获取公开帖子（visibility为'public'且不是当前用户的）
    public_posts = Post.query.filter(
        Post.visibility == 'public',
        Post.user_ip != user_ip
    ).order_by(Post.created_at.desc()).limit(20).all()

    return render_template('index.html',
                           user_ip=user_ip,
                           user_posts=user_posts,
                           public_posts=public_posts)


@app.route('/post', methods=['POST'])
def create_post():
    """创建新帖子"""
    user_ip = get_client_ip()

    content = request.form.get('content', '').strip()
    image = request.files.get('image')
    visibility = request.form.get('visibility', 'public')  # 获取可见性选项

    # 验证可见性选项
    if visibility not in ['public', 'admin_only', 'private']:
        visibility = 'public'

    if not content:
        flash('内容不能为空', 'danger')
        return redirect(url_for('index'))

    if len(content) > 1000:
        flash('内容过长，请限制在1000字以内', 'danger')
        return redirect(url_for('index'))

    # 处理图片上传
    image_filename = None
    if image and image.filename:
        if allowed_file(image.filename):
            # 生成唯一文件名
            ext = image.filename.rsplit('.', 1)[1].lower()
            image_filename = f"{uuid.uuid4().hex}.{ext}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image.save(image_path)
        else:
            flash('不支持的文件类型', 'danger')
            return redirect(url_for('index'))

    # 创建新帖子
    new_post = Post(
        content=content,
        image_filename=image_filename,
        user_ip=user_ip,
        is_anonymous=True,
        visibility=visibility  # 设置可见性
    )

    db.session.add(new_post)
    db.session.commit()

    # 根据可见性给出不同的提示
    visibility_messages = {
        'public': '帖子已发布到公共树洞',
        'admin_only': '帖子已发送给心理委员',
        'private': '帖子已保存，仅自己可见'
    }

    flash(visibility_messages.get(visibility, '帖子发布成功'), 'success')
    return redirect(url_for('index'))


@app.route('/reply/<int:post_id>', methods=['POST'])
def add_reply(post_id):
    """添加回复"""
    user_ip = get_client_ip()
    post = Post.query.get_or_404(post_id)

    content = request.form.get('content', '').strip()

    if not content:
        flash('回复内容不能为空', 'danger')
        return redirect(url_for('view_post', post_id=post_id))

    if len(content) > 500:
        flash('回复内容过长，请限制在500字以内', 'danger')
        return redirect(url_for('view_post', post_id=post_id))

    # 创建回复
    new_reply = Reply(
        content=content,
        user_ip=user_ip,
        post_id=post_id
    )

    db.session.add(new_reply)
    db.session.commit()

    flash('回复成功', 'success')
    return redirect(url_for('view_post', post_id=post_id))


@app.route('/post/<int:post_id>')
def view_post(post_id):
    """查看帖子详情"""
    user_ip = get_client_ip()
    post = Post.query.get_or_404(post_id)
    is_owner = (post.user_ip == user_ip)
    is_admin = is_admin_ip(user_ip)

    # 检查访问权限
    can_view = False

    if is_owner:  # 发帖人可以看到自己的所有帖子
        can_view = True
    elif post.visibility == 'public':  # 公开帖子所有人都可以看
        can_view = True
    elif post.visibility == 'admin_only' and is_admin:  # 仅管理员可见的帖子，管理员可以看
        can_view = True
    # private帖子：只有发帖人自己可以看到，管理员也看不到（除非是管理员自己发布的）
    # 这个情况已经由上面的is_owner条件覆盖了

    if not can_view:
        flash('无权查看此帖子', 'danger')
        return redirect(url_for('index'))

    return render_template('post_detail.html',
                           post=post,
                           user_ip=user_ip,
                           is_owner=is_owner,
                           is_admin=is_admin)


@app.route('/admin')
def admin_dashboard():
    """管理员后台"""
    user_ip = get_client_ip()

    if not is_admin_ip(user_ip):
        flash('无权访问管理员界面', 'danger')
        return redirect(url_for('index'))

    # 获取所有帖子，但过滤掉普通用户的private帖子
    all_posts = Post.query.filter(
        (Post.visibility != 'private') |
        (Post.user_ip == user_ip)
    ).order_by(Post.created_at.desc()).all()
    all_posts2 = Post.query.order_by(Post.created_at.desc()).all()

    # 计算统计信息
    stats = {
        'total': len(all_posts2),
        'private': sum(1 for post in all_posts2 if post.visibility == 'private'),
        'admin_only': sum(1 for post in all_posts if post.visibility == 'admin_only'),
        'public': sum(1 for post in all_posts if post.visibility == 'public'),
        'with_images': sum(1 for post in all_posts2 if post.image_filename),
        'with_replies': sum(1 for post in all_posts2 if len(post.replies) > 0),
        'today': sum(1 for post in all_posts2 if post.created_at.date() == datetime.utcnow().date())
    }

    return render_template('admin.html',
                           posts=all_posts,
                           user_ip=user_ip,
                           stats=stats,
                           now=datetime.utcnow())


@app.route('/admin/delete/<int:post_id>', methods=['POST'])
def admin_delete_post(post_id):
    """管理员删除帖子"""
    user_ip = get_client_ip()

    if not is_admin_ip(user_ip):
        return jsonify({'success': False, 'message': '无权操作'}), 403

    post = Post.query.get_or_404(post_id)

    # 删除关联的图片文件
    if post.image_filename:
        try:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)
        except:
            pass

    db.session.delete(post)
    db.session.commit()

    return jsonify({'success': True, 'message': '删除成功'})


@app.route('/delete_my_post/<int:post_id>', methods=['POST'])
def delete_my_post(post_id):
    """用户删除自己的帖子"""
    user_ip = get_client_ip()
    post = Post.query.get_or_404(post_id)

    if post.user_ip != user_ip and not is_admin_ip(user_ip):
        return jsonify({'success': False, 'message': '无权操作'}), 403

    # 删除关联的图片文件
    if post.image_filename:
        try:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)
        except:
            pass

    db.session.delete(post)
    db.session.commit()

    return jsonify({'success': True, 'message': '删除成功'})


# API端点
@app.route('/api/posts')
def api_posts():
    """获取帖子列表API"""
    user_ip = get_client_ip()
    posts = Post.query.order_by(Post.created_at.desc()).all()

    posts_data = []
    for post in posts:
        post_data = post.to_dict()
        post_data['is_owner'] = (post.user_ip == user_ip) or is_admin_ip(user_ip)
        posts_data.append(post_data)

    return jsonify(posts_data)


@app.route('/api/my_posts')
def api_my_posts():
    """获取当前用户的帖子API"""
    user_ip = get_client_ip()
    posts = Post.query.filter_by(user_ip=user_ip).order_by(Post.created_at.desc()).all()

    return jsonify([post.to_dict() for post in posts])


if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='运行匿名树洞服务器')
    parser.add_argument('--host', default='0.0.0.0', help='主机地址 (默认: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='端口号 (默认: 5000)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')

    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=args.debug)