from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
from functools import wraps
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here_change_in_production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


# Модели
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, авторизуйтесь для доступа к этой странице', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# Декоратор для проверки прав на редактирование
def author_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        post_id = kwargs.get('post_id')
        post = Post.query.get_or_404(post_id)
        if post.user_id != session.get('user_id'):
            flash('У вас нет прав на редактирование этого поста', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


# Маршруты
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    user_id = session.get('user_id')

    if user_id:
        # Авторизованный пользователь видит все посты + свои приватные
        posts = Post.query.filter(
            (Post.is_private == False) | (Post.user_id == user_id)
        ).order_by(Post.created_at.desc()).paginate(page=page, per_page=10)
    else:
        # Анонимный пользователь видит только публичные посты
        posts = Post.query.filter_by(is_private=False).order_by(
            Post.created_at.desc()
        ).paginate(page=page, per_page=10)

    return render_template('index.html', posts=posts, user_id=user_id)


@app.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    user_id = session.get('user_id')

    # Проверка доступа к приватному посту
    if post.is_private and post.user_id != user_id:
        flash('У вас нет доступа к этому посту', 'danger')
        return redirect(url_for('index'))

    return render_template('post_detail.html', post=post)


@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        is_private = request.form.get('is_private') == 'on'

        if not title or not content:
            flash('Заполните все поля', 'danger')
            return render_template('create_post.html')

        post = Post(
            title=title,
            content=content,
            is_private=is_private,
            user_id=session['user_id']
        )

        db.session.add(post)
        db.session.commit()

        flash('Пост успешно создан!', 'success')
        return redirect(url_for('index'))

    return render_template('create_post.html')


@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
@author_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        is_private = request.form.get('is_private') == 'on'

        if not title or not content:
            flash('Заполните все поля', 'danger')
            return render_template('edit_post.html', post=post)

        post.title = title
        post.content = content
        post.is_private = is_private
        post.updated_at = datetime.utcnow()

        db.session.commit()

        flash('Пост успешно обновлен!', 'success')
        return redirect(url_for('post_detail', post_id=post.id))

    return render_template('edit_post.html', post=post)


@app.route('/delete_post/<int:post_id>')
@login_required
@author_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()

    flash('Пост успешно удален!', 'success')
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Валидация
        errors = []

        if not username or len(username) < 3:
            errors.append('Имя пользователя должно содержать минимум 3 символа')

        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            errors.append('Имя пользователя может содержать только буквы, цифры, _, -, .')

        if not email or '@' not in email:
            errors.append('Введите корректный email')

        if len(password) < 6:
            errors.append('Пароль должен содержать минимум 6 символов')

        if password != confirm_password:
            errors.append('Пароли не совпадают')

        # Проверка уникальности
        if User.query.filter_by(username=username).first():
            errors.append('Пользователь с таким именем уже существует')

        if User.query.filter_by(email=email).first():
            errors.append('Пользователь с таким email уже существует')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html')

        # Создание пользователя
        user = User(username=username, email=email)
        user.set_password(password)

        # Первый пользователь становится админом
        if User.query.count() == 0:
            user.is_admin = True

        db.session.add(user)
        db.session.commit()

        flash('Регистрация успешна! Теперь вы можете войти', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


@app.route('/my_posts')
@login_required
def my_posts():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(user_id=session['user_id']).order_by(
        Post.created_at.desc()
    ).paginate(page=page, per_page=10)

    return render_template('my_posts.html', posts=posts)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5988)
