from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from models import UserModel


class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(),
        Length(min=3, max=50, message='Имя пользователя должно быть от 3 до 50 символов')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(),
        Length(min=8, message='Пароль должен быть минимум 8 символов')
    ])
    confirm_password = PasswordField('Подтверждение пароля', validators=[
        DataRequired(),
        EqualTo('password', message='Пароли должны совпадать')
    ])
    is_admin = BooleanField('Создать как администратора')
    submit = SubmitField('Зарегистрировать пользователя')

    def validate_username(self, username):
        """Валидация уникальности username"""
        if UserModel.user_exists(username.data):
            raise ValidationError('Пользователь с таким именем уже существует')