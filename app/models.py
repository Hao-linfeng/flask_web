from datetime import datetime
from app import db  # 导入数据库
from werkzeug.security import generate_password_hash, check_password_hash  # hash摘要算法
from app import login
from flask_login import UserMixin
from hashlib import md5
import jwt
from app import app
from time import time
''' 作为一个附加手段，多次哈希相同的密码，你将得到不同的结果，
    所以这使得无法通过查看它们的哈希值来确定两个用户是否具有相同的密码。'''
"""
一旦创建，该对象就包含sqlalchemy和sqlalchemy.orm中的所有函数和帮助程序。 
此外，它提供了一个名为Model的类，它是一个声明性基础，可用于声明模型
"""

"""下面创建的User类继承自db.Model，它是Flask-SQLAlchemy中所有模型的基类"""
"""
Flask-Login插件需要在用户模型上实现某些属性和方法。
这种做法很棒，因为只要将这些必需项添加到模型中，Flask-Login就没有其他依赖了，
它就可以与基于任何数据库系统的用户模型一起工作Flask-Login提供了一个叫做UserMixin的mixin类来将它们归纳其中。
下面演示了如何将mixin类添加到模型中
"""
followers = db.Table('followers',
                     db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
                     db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
                     )


class User(db.Model, UserMixin):  # 设置数据库User表
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    posts = db.relationship('Post', backref='author', lazy='dynamic')

    """lazy 通俗了说，select就是访问到属性的时候，就会全部加载该属性的数据。
    joined则是在对关联的两个表进行join操作，从而获取到所有相关的对象。
    dynamic则不一样，在访问属性的时候，并没有在内存中加载数据，而是返回一个query对象,
     需要执行相应方法才可以获取对象，比如.all().下面结合实例解释这几个的使用场景"""

    """User类有一个新的posts字段，用db.relationship初始化。这不是实际的数据库字段，
    而是用户和其动态之间关系的高级视图，因此它不在数据库图表中。
    对于一对多关系，db.relationship字段通常在“一”的这边定义，并用作访问“多”的便捷方式。
    因此，如果我有一个用户实例u，表达式u.posts将运行一个数据库查询，返回该用户发表过的所有动态。
     db.relationship的第一个参数表示代表关系“多”的类。 
     backref参数定义了代表“多”的类的实例反向调用“一”的时候的属性名称。
     这将会为用户动态添加一个属性post.author，调用它将返回给该用户动态的用户实例。 
     lazy参数定义了这种关系调用的数据库查询是如何执行的"""

    """user1.followed.append(user2)
        要取消关注该用户，我可以这么做：
        user1.followed.remove(user2)"""

    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)  # 将password转换成hash字符串

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)  # 用户输入用户名和密码
        # 将数据库里用户的密码摘要,与用户输入的密码摘要对比

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def avatar(self, size):  # 生成图片并返回
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()  # 生成唯一图片
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)  # 返回图片

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):  # 发出一个关于followed关系的查询来检查两个用户之间的关系是否已经存在
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0  # followers.c.follower_id表达式引用了该关系表中的follower_id

    def followed_posts(self):  # 找出关注的人
        return Post.query\
            .join(followers,(followers.c.followed_id == Post.user_id)) \
            .filter(followers.c.follower_id == self.id)\
            .order_by(Post.timestamp.desc())

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)
"""
followed_posts()函数已被扩展成通过联合查询来并入用户自己的动态：
def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
                followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())"""

"""
Post.query.join(followers, (followers.c.followed_id == Post.user_id))
第一个参数是followers关联表，第二个参数是join条件。
我的这个调用表达的含义是我希望数据库创建一个临时表，        就是合并一个临时表
它将用户动态表和关注者表中的数据结合在一起。 
数据将根据参数传递的条件进行合并

filter(followers.c.follower_id == self.id)
filter()来剔除所有我不需要的数据。
这是过滤部分的查询语句：
该查询是User类的一个方法，self.id表达式是指我感兴趣的用户的ID。         就是过滤
filter()挑选临时表中follower_id列等于这个ID的行，换句话说，
我只保留follower(粉丝)是该用户的数据

order_by(Post.timestamp.desc())
在这里，我要说的是，我希望使用用户动态产生的时间戳按降序排列结果列表
"""


class Post(db.Model):  # 设置post表
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post {}>'.format(self.body)


"""
post表将具有必须的id、用户动态的body和timestamp字段。
除了这些预期的字段之外，我还添加了一个user_id字段，将该用户动态链接到其作者。
你已经看到所有用户都有一个唯一的id主键， 将用户动态链接到其作者的方法是添加对用户id的引用，
这正是user_id字段所在的位置。 这个user_id字段被称为外键。 
上面的数据库图显示了外键作为该字段和它引用的表的id字段之间的链接。 
这种关系被称为一对多，因为“一个”用户写了“多”条动态。
"""


# 装饰器来为用户加载功能注册函数
@login.user_loader
def load_user(id):
    return User.query.get(int(id))


'''
它是一个回调函数，在每次请求过来后，Flask-Login都会从Session中寻找”user_id”的值，
如果找到的话，就会用这个”user_id”值来调用此回调函数，
并构建一个用户类对象。因此，没有这个回调的话，Flask-Login将无法工作
'''
