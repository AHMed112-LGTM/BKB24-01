from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField, SelectMultipleField, PasswordField, \
    SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from models import User, Category, Tag


class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(),
        Length(min=3, max=80, message='Имя должно быть от 3 до 80 символов')
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Length(max=120, message='Email не должен превышать 120 символов')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(),
        Length(min=6, message='Пароль должен быть минимум 6 символов')
    ])
    confirm_password = PasswordField('Подтверждение пароля', validators=[
        DataRequired(),
        EqualTo('password', message='Пароли должны совпадать')
    ])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Это имя пользователя уже занято')

    def validate_email(self, email):
        # Простая проверка формата email
        if '@' not in email.data or '.' not in email.data:
            raise ValidationError('Введите корректный email адрес')
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Этот email уже зарегистрирован')


class PostForm(FlaskForm):
    title = StringField('Заголовок', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Содержание', validators=[DataRequired()])
    category_id = SelectField('Категория', coerce=int, validators=[DataRequired()])
    tags = SelectMultipleField('Теги', coerce=int, choices=[],
                               validators=[DataRequired()])  # Изменено на SelectMultipleField
    is_private = BooleanField('Приватный пост (виден только авторизованным)')
    submit = SubmitField('Сохранить')


class CategoryForm(FlaskForm):
    name = StringField('Название категории', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Описание')
    submit = SubmitField('Сохранить')

    def validate_name(self, name):
        category = Category.query.filter_by(name=name.data).first()
        if category:
            raise ValidationError('Категория с таким названием уже существует')


class TagForm(FlaskForm):
    name = StringField('Название тега', validators=[DataRequired(), Length(max=50)])
    submit = SubmitField('Сохранить')

    def validate_name(self, name):
        tag = Tag.query.filter_by(name=name.data).first()
        if tag:
            raise ValidationError('Тег с таким названием уже существует')