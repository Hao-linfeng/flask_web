from flask import Flask
from config import Config  # 数据库的配置信息
from flask_sqlalchemy import SQLAlchemy  # ORM的工作就是将高级操作转换成数据库命令。
from flask_migrate import Migrate
# 第一次创建数据库时使用   数据库迁移增加了启动数据库时候的一些工作，
# 这是一项困难的工作，因为关系数据库是以结构化数据为中心的，
# 所以当结构发生变化时，数据库中的已有数据需要被迁移到修改后的结构中
from flask_login import LoginManager  # 用户登陆的  它处理在长时间内登录，注销和记住用户会话的常见任务。
from flask_mail import Mail
import logging
from logging.handlers import SMTPHandler
import os
from logging.handlers import RotatingFileHandler
from flask_bootstrap import Bootstrap
from flask_moment import Moment

'''
将活动用户的ID存储在会话中，让您轻松登录和注销。
允许您将视图限制为已登录（或已注销）的用户。
处理通常棘手的“记住我”功能。
帮助保护用户的会话不被cookie窃贼窃取。
稍后可能会与Flask-Principal或其他授权扩展集成

is_authenticated()
        当用户通过验证时，也即提供有效证明时返回 True 。
        （只有通过验证的用户 会满足 login_required 的条件。）
is_active()
        如果这是一个活动用户且通过验证，账户也已激活，未被停用，
        也不符合任何你 的应用拒绝一个账号的条件，返回 True 。
        不活动的账号可能不会登入（当然， 是在没被强制的情况下）。
is_anonymous()
        如果是一个匿名用户，返回 True 。（真实用户应返回 False 。）
get_id()
        返回一个能唯一识别用户的，并能用于从 user_loader 回调中 加载用户的 unicode 。
        注意着 必须 是一个 unicode ——如果 ID 原本是 一个 int 或其它类型，你需要把它转换为 unicode 。
'''

app = Flask(__name__)  # 一个flask实例
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)  # 数据库迁移引擎migrate
login = LoginManager(app)
login.login_view = 'login'  # 如果未设定登入视图，会以 401 错误退 出。@login_require 判断未登录 跳到 login 函数
mail = Mail(app)
bootstrap = Bootstrap(app)
moment = Moment(app)
""" 
>>> from datetime import datetime
>>> str(datetime.now())           时间模块
'2019-04-02 16:24:49.657745'

datetime.now()调用返回我所处位置的本地时间，而datetime.utcnow()调用则返回UTC时区中的时间。
如果我可以让遍布世界不同地区的多人同时运行上面的代码，那么datetime.now()函数将为他们每个人返回不同的结果，
但是无论位置如何，datetime.utcnow()总是会返回同一时间
"""

if not app.debug:
    if app.config['MAIL_SERVER']:
        auth = None
        if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
            auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        secure = None
        if app.config['MAIL_USE_TLS']:
            secure = ()
        mail_handler = SMTPHandler(
            mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
            fromaddr='no-reply@' + app.config['MAIL_SERVER'],
            toaddrs=app.config['ADMINS'], subject='Microblog Failure',
            credentials=auth, secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/microblog.log', maxBytes=10240,
                                       backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Microblog startup')

from app import routes, models, errors
