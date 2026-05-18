import os
import json
import hashlib
import secrets
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError

app = Flask(__name__)
app.secret_key = 'my_secret_key_12345'

# Файл для хранения пользователей
USERS_FILE = 'users.json'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'Admin123!'

# Требования к паролю
PASSWORD_REQUIREMENTS = {
    'min_length': 8,
    'require_uppercase': True,
    'require_lowercase': True,
    'require_digits': True,
    'require_special': True
}


def init_users_file():
    """Создание файла с пользователями и администратором"""
    if not os.path.exists(USERS_FILE):
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256(f"{ADMIN_PASSWORD}{salt}".encode()).hexdigest()

        users = {
            ADMIN_USERNAME: {
                "username": ADMIN_USERNAME,
                "password_hash": password_hash,
                "salt": salt,
                "is_admin": True,
                "created_at": datetime.now().isoformat(),
                "last_login": None
            }
        }
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)


def load_users():
    """Загрузка пользователей"""
    if not os.path.exists(USERS_FILE):
        init_users_file()
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_users(users):
    """Сохранение пользователей"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def verify_password(username, password):
    """Проверка пароля"""
    users = load_users()
    if username not in users:
        return False
    user = users[username]
    expected = hashlib.sha256(f"{password}{user['salt']}".encode()).hexdigest()
    return user['password_hash'] == expected


def update_last_login(username):
    """Обновление времени последнего входа"""
    users = load_users()
    if username in users:
        users[username]['last_login'] = datetime.now().isoformat()
        save_users(users)


def validate_password_strength(password):
    """Проверка сложности пароля"""
    errors = []
    if len(password) < PASSWORD_REQUIREMENTS['min_length']:
        errors.append(f"Пароль должен быть минимум {PASSWORD_REQUIREMENTS['min_length']} символов")
    if PASSWORD_REQUIREMENTS['require_uppercase'] and not re.search(r'[A-Z]', password):
        errors.append("Пароль должен содержать заглавную букву")
    if PASSWORD_REQUIREMENTS['require_lowercase'] and not re.search(r'[a-z]', password):
        errors.append("Пароль должен содержать строчную букву")
    if PASSWORD_REQUIREMENTS['require_digits'] and not re.search(r'\d', password):
        errors.append("Пароль должен содержать цифру")
    if PASSWORD_REQUIREMENTS['require_special'] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Пароль должен содержать спецсимвол")
    return errors


def is_admin_logged_in():
    """Проверка, авторизован ли администратор"""
    return session.get('logged_in') and session.get('is_admin', False)


# Формы
class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class CreateUserForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(), Length(min=3, max=50)
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(), Length(min=8)
    ])
    confirm_password = PasswordField('Подтверждение пароля', validators=[
        DataRequired(), EqualTo('password')
    ])
    is_admin = BooleanField('Администратор')
    submit = SubmitField('Создать')

    def validate_username(self, field):
        users = load_users()
        if field.data in users:
            raise ValidationError('Пользователь уже существует')


# Маршруты
@app.route('/')
def index():
    if is_admin_logged_in():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_admin_logged_in():
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        users = load_users()
        if username in users and verify_password(username, password):
            session['logged_in'] = True
            session['username'] = username
            session['is_admin'] = users[username].get('is_admin', False)
            update_last_login(username)
            flash(f'Добро пожаловать, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')

    return render_template('login.html', form=form)


@app.route('/dashboard')
def dashboard():
    if not is_admin_logged_in():
        flash('Доступ запрещен', 'error')
        return redirect(url_for('login'))

    users = load_users()
    users_list = []
    for username, data in users.items():
        users_list.append({
            'username': username,
            'is_admin': data.get('is_admin', False),
            'created_at': data.get('created_at', ''),
            'last_login': data.get('last_login', 'Никогда')
        })
    users_list.sort(key=lambda x: x['created_at'], reverse=True)

    return render_template('dashboard.html', users=users_list, admin_username=session.get('username'))


@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if not is_admin_logged_in():
        flash('Доступ запрещен', 'error')
        return redirect(url_for('login'))

    form = CreateUserForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        errors = validate_password_strength(password)
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('create_user.html', form=form, password_requirements=PASSWORD_REQUIREMENTS)

        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

        users = load_users()
        users[username] = {
            "username": username,
            "password_hash": password_hash,
            "salt": salt,
            "is_admin": form.is_admin.data,
            "created_at": datetime.now().isoformat(),
            "last_login": None
        }
        save_users(users)

        role = "администратором" if form.is_admin.data else "пользователем"
        flash(f'Пользователь {username} создан как {role}', 'success')
        return redirect(url_for('dashboard'))

    return render_template('create_user.html', form=form, password_requirements=PASSWORD_REQUIREMENTS)


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    init_users_file()
    app.run(debug=True, port=5777)