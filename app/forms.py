from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField  # 表单内容
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length  # 表单内容的类型 格式
from app.models import User  # 导入数据库类


# 表单

class LoginForm(FlaskForm):  # 登陆表单
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):  # 注册表单
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):  # 不能相同
        user = User.query.filter_by(username=username.data).first()  # 看数据库中有没有重名的
        if user is not None:
            raise ValidationError('Please use a different username.')  # 出现错误这句会输出到web页面上？？？？

        # {% for error in form.username.errors %}
        # <span style="color: red;">[{{ error }}]</span>

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()  # 每个email只可以注册一个用户
        if user is not None:
            raise ValidationError('Please use a different email address.')

        # {% for error in form.email.errors %}
        #   <span style="color: red;">[{{ error }}]</span>


"""
    当添加任何匹配模式validate_ <field_name>的方法时，
    WTForms将这些方法作为自定义验证器，并在已设置验证器之后调用它们。
    本处，我想确保用户输入的username和email不会与数据库中已存在的数据冲突，
    所以这两个方法执行数据库查询，并期望结果集为空。 否则，则通过ValidationError触发验证错误。 
    异常中作为参数的消息将会在对应字段旁边显示，以供用户查看
"""


class EditProfileForm(FlaskForm):  # 修改页面的表单
    username = StringField('Username', validators=[DataRequired()])
    about_me = TextAreaField('About me', validators=[Length(min=0, max=140)])
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):  # 继承父类的__init__
        super(EditProfileForm, self).__init__(*args, **kwargs)  # 并加上 self.original_username = original_username
        self.original_username = original_username

    def validate_username(self, username):  # 如果名字没有修改 则通过
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()  # 看数据库有没有重名
            if user is not None:
                raise ValidationError('Please use a different username.')


class PostForm(FlaskForm):
    post = TextAreaField('Say something', validators=[
        DataRequired(), Length(min=1, max=140)])
    submit = SubmitField('Submit')


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Request Password Reset')