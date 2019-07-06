from datetime import datetime
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, PostForm, ResetPasswordRequestForm, \
    ResetPasswordForm
from app.models import User, Post
from app.email import send_password_reset_email
from app.forms import ResetPasswordRequestForm


@app.before_request
def before_request():  # 每次请求前执行 设置时间
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


# 判断用户是否登陆 如果没有跳到登陆界面
# 当一个没有登录的用户访问被@login_required装饰器保护的视图函数时，装饰器将重定向到登录页面
# 但是它会添加一个查询字符串参数来丰富这个URL，如/login?next=/index*。
# 原始URL设置了next查询字符串参数后，应用就可以在登录后使用它来重定向。

# 浏览器现在被指示发送GET请求来获取重定向中指定的页面，所以现在最后一个请求不再是'POST'请求了，
# 刷新命令就能以更可预测的方式工作。这个简单的技巧叫做Post/Redirect/Get模式。
# 它避免了用户在提交网页表单后无意中刷新页面时插入重复的动态
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        return redirect(url_for('index'))  # 提交post后 重定向
    page = request.args.get('page', 1, type=int)
    print(page, "===========================")
    posts = current_user.followed_posts().paginate(page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) if posts.has_prev else None
    return render_template('index.html', title='Home', form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


""" 
Flask-SQLAlchemy的paginate()方法原生就支持分页。
例如，我想要获取用户关注的前20个动态，我可以将all()结束调用替换成如下的查询：
>>> user.followed_posts().paginate(1, 20, False).items

has_next: 当前页之后存在后续页面时为真
has_prev: 当前页之前存在前置页面时为真
next_num: 下一页的页码
prev_num: 上一页的页码
"""


@app.route('/login', methods=['GET', 'POST'])
def login():  # 回调函数 生成了current_user 并提取cook
    if current_user.is_authenticated:  # 一个用来表示用户是否通过登录认证的属性，用True和False表示。
        return redirect(url_for('index'))  # 如果用户登陆回调到index
    form = LoginForm()  # 一个表单
    if form.validate_on_submit():  # 如果表单提交
        user = User.query.filter_by(username=form.username.data).first()  # 返回一个User实例
        if user is None or not user.check_password(form.password.data):  # 检验user 将user的密码摘要与数据库中的对比
            flash('Invalid username or password')
            return redirect(url_for('login'))  # 回调
        login_user(user, remember=form.remember_me.data)  # 登陆 设置cook
        """“记住我”功能的实现很棘手。尽管如此，Flask-Login 几乎透明地实现了这
        ——只需要向 login_user 调用传递 remember=True 。
        一个 cookie 就会存储在用户的电脑上， 
        且之后如果会话中没有用户 ID，Flask-Login 会自动从那个 cookie 上恢复用户 ID。
         这个 cookie 是防篡改的，所以如果用户篡改了它（插入其它用户的 ID 来替代自己 的），
         这个 cookie 只不过会被拒绝，就如同没有一样。"""
        # Flask提供一个request变量，其中包含客户端随请求发送的所有信息。 特别是request.args属性
        next_page = request.args.get('next')  # 如果用户是从其他界面重定向来login的 它会有一个next 参数 这可以取出原界面的url
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')  # 如果不是去index
        return redirect(next_page)  # 回调 此时已有cook可直接登陆
    return render_template('login.html', title='Sign In', form=form)


"""
如果登录URL中不含next参数，那么将会重定向到本应用的主页。
如果登录URL中包含next参数，其值是一个相对路径（换句话说，该URL不含域名信息），那么将会重定向到本应用的这个相对路径。
如果登录URL中包含next参数，其值是一个包含域名的完整URL，那么重定向到本应用的主页
"""


@app.route('/logout')  # 登出 清空cook
def logout():
    logout_user()  # 好像是把服务器上对应的用户的cook删除
    return redirect(url_for('index'))  # 重定向到index


@app.route('/register', methods=['GET', 'POST'])  # 注册用户
def register():
    if current_user.is_authenticated:  # current_user是User的一个实例 看用户是否登陆
        return redirect(url_for('index'))  # 回调
    form = RegistrationForm()  # 接收注册表单
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)  # 接收username and email
        user.set_password(form.password.data)  # 生成摘要 摘要算法不可逆
        db.session.add(user)  # 提交到数据库
        """
        session(会话)可以看成一个管理数据库持久连接的对象
        session.add函数会把Model加入持久空间
        """
        db.session.commit()  # 提交完毕
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/edit_profile', methods=['GET', 'POST'])  # 修改
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)  # 只有登陆了才可以修改资料
    if form.validate_on_submit():  # current_user.username这里表示正在登陆的用户名
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))  # 当为POST请求时
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',  # 当为GET请求时 执行此处
                           form=form)


@app.route('/unfollow/<username>')
@login_required
def unfollow(username):  # 取注
    user = User.query.filter_by(username=username).first()
    if user is None:  # 如果用户不存在
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:  # 不可取关自己
        flash('You cannot unfollow yourself!')
        return redirect(url_for('user', username=username))
    current_user.unfollow(user)  # 取关
    db.session.commit()
    flash('You are not following {}.'.format(username))
    return redirect(url_for('user', username=username))


@app.route('/follow/<username>')
@login_required
def follow(username):  # 关注
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('user', username=username))


@login_required
@app.route('/username', methods=['POST', "GET"])
def username():
    user_list = User.query.all()  # 返回一个列表 列表重是User的实例
    return render_template("user_list.html", user_list=user_list)


@app.route('/explore')
@login_required  # 返回规定个数的post
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('explore', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) if posts.has_prev else None
    return render_template("index.html", title='Explore', posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@app.route('/user/<username>')
@login_required
def user(username):  # 你登陆后 由此路由进入其他用户的主页
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    # paginate()的返回是Pagination类的实例
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(page, app.config['POSTS_PER_PAGE'], False)
    # 判断下一页是否存在 如果存在 给一个链接
    next_url = url_for('user', username=user.username, page=posts.next_num) if posts.has_next else None
    # 判断上一页是否存在 如果存在 给一个链接
    prev_url = url_for('user', username=user.username, page=posts.prev_num) if posts.has_prev else None
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)
