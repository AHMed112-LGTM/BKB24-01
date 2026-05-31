from flask import Flask, render_template, redirect, url_for, flash, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re
from functools import wraps
from forms import LoginForm, RegistrationForm
from models import UserModel

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'


# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Пожалуйста, авторизуйтесь', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# Декоратор для проверки прав администратора
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Пожалуйста, авторизуйтесь', 'warning')
            return redirect(url_for('login'))
        if not UserModel.is_admin(session['username']):
            flash('Доступ запрещен. Требуются права администратора', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    return decorated_function


# Вспомогательная функция для проверки сложности пароля
def check_password_strength(password):
    """
    Проверка сложности пароля:
    - минимум 8 символов
    - хотя бы одна заглавная буква
    - хотя бы одна строчная буква
    - хотя бы одна цифра
    - хотя бы один специальный символ
    """
    if len(password) < 8:
        return False, "Пароль должен содержать минимум 8 символов"

    if not re.search(r'[A-Z]', password):
        return False, "Пароль должен содержать хотя бы одну заглавную букву"

    if not re.search(r'[a-z]', password):
        return False, "Пароль должен содержать хотя бы одну строчную букву"

    if not re.search(r'[0-9]', password):
        return False, "Пароль должен содержать хотя бы одну цифру"

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Пароль должен содержать хотя бы один специальный символ"

    return True, "Пароль надежный"


# Регистрация с проверкой пароля
def register_user_with_validation(username, password, is_admin=False):
    """Регистрация с проверкой сложности пароля"""
    # Проверка сложности пароля
    is_strong, message = check_password_strength(password)
    if not is_strong:
        return False, message

    return UserModel.register_user(username, password, is_admin)


# Главная страница
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


# Страница авторизации
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        if UserModel.authenticate_user(username, password):
            session['username'] = username
            flash('Вы успешно авторизованы!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')

    return render_template('login.html', form=form)


# Панель управления (список пользователей)
@app.route('/dashboard')
@login_required
def dashboard():
    users = UserModel.get_all_users()
    current_user = session['username']
    is_admin = UserModel.is_admin(current_user)

    return render_template('dashboard.html',
                           users=users,
                           current_user=current_user,
                           is_admin=is_admin)


# Страница регистрации нового пользователя (только для админа)
@app.route('/register', methods=['GET', 'POST'])
@admin_required
def register_user():
    form = RegistrationForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        is_admin = form.is_admin.data

        success, message = register_user_with_validation(username, password, is_admin)

        if success:
            flash(message, 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(message, 'danger')

    return render_template('register_user.html', form=form)


# Удаление пользователя (только для админа)
@app.route('/delete_user/<username>')
@admin_required
def delete_user(username):
    current_user = session['username']

    if username == current_user:
        flash('Нельзя удалить самого себя', 'danger')
        return redirect(url_for('dashboard'))

    if username == 'admin':
        flash('Нельзя удалить главного администратора', 'danger')
        return redirect(url_for('dashboard'))

    if UserModel.user_exists(username):
        UserModel.perform_delete(username)
        flash(f'Пользователь {username} успешно удален', 'success')
    else:
        flash('Пользователь не найден', 'danger')

    return redirect(url_for('dashboard'))


# Выход из системы
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)