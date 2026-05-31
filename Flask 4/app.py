from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from models import db, User, Category, Tag, Post
from forms import LoginForm, RegistrationForm, PostForm, CategoryForm, TagForm
from datetime import datetime
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, авторизуйтесь для доступа к этой странице'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Создание таблиц и добавление начальных данных
def init_db():
    with app.app_context():
        db.create_all()

        # Создание тестового администратора, если нет пользователей
        if User.query.count() == 0:
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('Admin123')
            db.session.add(admin)

            # Создание начальных категорий
            categories = ['Технологии', 'Путешествия', 'Кулинария', 'Спорт', 'Искусство']
            for cat_name in categories:
                category = Category(name=cat_name)
                db.session.add(category)

            # Создание начальных тегов
            tags = ['Новости', 'Обзор', 'Советы', 'Инструкция', 'Интересное']
            for tag_name in tags:
                tag = Tag(name=tag_name)
                db.session.add(tag)

            db.session.commit()
            print("База данных инициализирована с тестовым администратором")


# Маршруты
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category', type=int)
    author_id = request.args.get('author', type=int)
    tag_id = request.args.get('tag', type=int)

    query = Post.query

    # Фильтрация
    if category_id:
        query = query.filter_by(category_id=category_id)
    if author_id:
        query = query.filter_by(author_id=author_id)
    if tag_id:
        query = query.join(Post.tags).filter(Tag.id == tag_id)

    # Скрываем приватные посты от анонимных пользователей
    if not current_user.is_authenticated:
        query = query.filter_by(is_private=False)

    posts = query.order_by(Post.created_at.desc()).paginate(page=page, per_page=10, error_out=False)

    categories = Category.query.all()
    authors = User.query.all()
    tags = Tag.query.all()

    return render_template('index.html',
                           posts=posts,
                           categories=categories,
                           authors=authors,
                           tags=tags,
                           current_category=category_id,
                           current_author=author_id,
                           current_tag=tag_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Вы успешно авторизованы!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')

    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Регистрация успешна! Теперь вы можете войти', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


# CRUD для постов
@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def create_post():
    form = PostForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    form.tags.choices = [(t.id, t.name) for t in Tag.query.all()]

    if form.validate_on_submit():
        post = Post(
            title=form.title.data,
            content=form.content.data,
            is_private=form.is_private.data,
            author_id=current_user.id,
            category_id=form.category_id.data
        )
        # Проверяем, что теги выбраны (form.tags.data теперь будет списком)
        if form.tags.data:
            post.tags = Tag.query.filter(Tag.id.in_(form.tags.data)).all()
        db.session.add(post)
        db.session.commit()
        flash('Пост успешно создан!', 'success')
        return redirect(url_for('index'))

    return render_template('post_form.html', form=form, title='Создать пост')


@app.route('/post/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    post = Post.query.get_or_404(id)

    # Проверка прав: автор или администратор
    if post.author_id != current_user.id and not current_user.is_admin:
        flash('У вас нет прав для редактирования этого поста', 'danger')
        return redirect(url_for('index'))

    form = PostForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    form.tags.choices = [(t.id, t.name) for t in Tag.query.all()]

    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.is_private = form.is_private.data
        post.category_id = form.category_id.data
        # Проверяем, что теги выбраны (form.tags.data теперь будет списком)
        if form.tags.data:
            post.tags = Tag.query.filter(Tag.id.in_(form.tags.data)).all()
        else:
            post.tags = []
        post.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Пост обновлен!', 'success')
        return redirect(url_for('index'))

    form.title.data = post.title
    form.content.data = post.content
    form.is_private.data = post.is_private
    form.category_id.data = post.category_id
    form.tags.data = [tag.id for tag in post.tags] if post.tags else []

    return render_template('post_form.html', form=form, title='Редактировать пост')


@app.route('/post/<int:id>/delete')
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id)

    if post.author_id != current_user.id and not current_user.is_admin:
        flash('У вас нет прав для удаления этого поста', 'danger')
        return redirect(url_for('index'))

    db.session.delete(post)
    db.session.commit()
    flash('Пост удален!', 'success')
    return redirect(url_for('index'))


# CRUD для категорий
@app.route('/categories')
def categories():
    categories_list = Category.query.all()
    return render_template('categories.html', categories=categories_list)


@app.route('/category/new', methods=['GET', 'POST'])
@login_required
def create_category():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(name=form.name.data, description=form.description.data)
        db.session.add(category)
        db.session.commit()
        flash('Категория создана!', 'success')
        return redirect(url_for('categories'))
    return render_template('category_form.html', form=form, title='Создать категорию')


@app.route('/category/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    form = CategoryForm()

    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        db.session.commit()
        flash('Категория обновлена!', 'success')
        return redirect(url_for('categories'))

    form.name.data = category.name
    form.description.data = category.description
    return render_template('category_form.html', form=form, title='Редактировать категорию')


@app.route('/category/<int:id>/delete')
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    if category.posts:
        flash('Нельзя удалить категорию, в которой есть посты', 'danger')
    else:
        db.session.delete(category)
        db.session.commit()
        flash('Категория удалена!', 'success')
    return redirect(url_for('categories'))


# CRUD для тегов
@app.route('/tags')
def tags():
    tags_list = Tag.query.all()
    return render_template('tags.html', tags=tags_list)


@app.route('/tag/new', methods=['GET', 'POST'])
@login_required
def create_tag():
    form = TagForm()
    if form.validate_on_submit():
        tag = Tag(name=form.name.data)
        db.session.add(tag)
        db.session.commit()
        flash('Тег создан!', 'success')
        return redirect(url_for('tags'))
    return render_template('tag_form.html', form=form, title='Создать тег')


@app.route('/tag/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_tag(id):
    tag = Tag.query.get_or_404(id)
    form = TagForm()

    if form.validate_on_submit():
        tag.name = form.name.data
        db.session.commit()
        flash('Тег обновлен!', 'success')
        return redirect(url_for('tags'))

    form.name.data = tag.name
    return render_template('tag_form.html', form=form, title='Редактировать тег')


@app.route('/tag/<int:id>/delete')
@login_required
def delete_tag(id):
    tag = Tag.query.get_or_404(id)
    db.session.delete(tag)
    db.session.commit()
    flash('Тег удален!', 'success')
    return redirect(url_for('tags'))


# Импорт/Экспорт дампа
@app.route('/dump/export')
@login_required
def export_dump():
    if not current_user.is_admin:
        flash('Только администратор может экспортировать данные', 'danger')
        return redirect(url_for('index'))

    data = {
        'categories': [{'id': c.id, 'name': c.name, 'description': c.description} for c in Category.query.all()],
        'tags': [{'id': t.id, 'name': t.name} for t in Tag.query.all()],
        'users': [{'id': u.id, 'username': u.username, 'email': u.email, 'is_admin': u.is_admin} for u in
                  User.query.all()],
        'posts': [{
            'id': p.id,
            'title': p.title,
            'content': p.content,
            'is_private': p.is_private,
            'created_at': p.created_at.isoformat(),
            'updated_at': p.updated_at.isoformat(),
            'author_id': p.author_id,
            'category_id': p.category_id,
            'tags': [tag.id for tag in p.tags]
        } for p in Post.query.all()]
    }

    with open('dump.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    flash('Данные экспортированы в dump.json', 'success')
    return redirect(url_for('index'))


@app.route('/dump/import', methods=['GET', 'POST'])
@login_required
def import_dump():
    if not current_user.is_admin:
        flash('Только администратор может импортировать данные', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        file = request.files.get('dump_file')
        if file and file.filename.endswith('.json'):
            data = json.load(file)

            # Импорт категорий
            for cat_data in data.get('categories', []):
                if not Category.query.get(cat_data['id']):
                    category = Category(name=cat_data['name'], description=cat_data.get('description'))
                    db.session.add(category)

            # Импорт тегов
            for tag_data in data.get('tags', []):
                if not Tag.query.get(tag_data['id']):
                    tag = Tag(name=tag_data['name'])
                    db.session.add(tag)

            db.session.commit()

            # Импорт пользователей
            for user_data in data.get('users', []):
                if not User.query.get(user_data['id']):
                    user = User(
                        username=user_data['username'],
                        email=user_data['email'],
                        is_admin=user_data['is_admin']
                    )
                    user.set_password('Temp123')  # Временный пароль
                    db.session.add(user)

            db.session.commit()

            # Импорт постов
            for post_data in data.get('posts', []):
                if not Post.query.get(post_data['id']):
                    post = Post(
                        title=post_data['title'],
                        content=post_data['content'],
                        is_private=post_data['is_private'],
                        author_id=post_data['author_id'],
                        category_id=post_data['category_id']
                    )
                    post.tags = Tag.query.filter(Tag.id.in_(post_data['tags'])).all()
                    db.session.add(post)

            db.session.commit()
            flash('Данные успешно импортированы!', 'success')
        else:
            flash('Пожалуйста, загрузите JSON файл', 'danger')

        return redirect(url_for('index'))

    return render_template('dump_import.html')


if __name__ == '__main__':
    init_db()
    app.run(debug=True , port=5001)