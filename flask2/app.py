import os
import uuid
import hashlib
import json
import mimetypes
from datetime import datetime
from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_in_production'

# Конфигурация
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['ALLOWED_EXTENSIONS'] = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx',
    'xls', 'xlsx', 'mp3', 'mp4', 'zip', 'rar', '7z'
}
app.config['FORBIDDEN_EXTENSIONS'] = {'exe', 'sh', 'php', 'js', 'py', 'bat', 'cmd', 'vbs'}

# Файл для хранения метаданных
DATA_FILE = 'files_data.json'

def init_data_file():
    """Инициализация JSON файла с данными о файлах"""
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def load_files_data():
    """Загрузка данных о файлах из JSON"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_files_data(files_data):
    """Сохранение данных о файлах в JSON"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(files_data, f, indent=2, ensure_ascii=False)

def get_file_hash(file_data):
    """Вычисление MD5 хэша файла"""
    return hashlib.md5(file_data).hexdigest()

def is_duplicate(file_hash):
    """Проверка, существует ли уже файл с таким MD5 хэшем"""
    files_data = load_files_data()
    return any(file['file_hash'] == file_hash for file in files_data)

def get_file_extension(filename):
    """Получение расширения файла"""
    return os.path.splitext(filename)[1][1:].lower()

def allowed_file(filename):
    """Проверка, разрешен ли тип файла"""
    ext = get_file_extension(filename)

    # Проверка на запрещенные расширения
    if ext in app.config['FORBIDDEN_EXTENSIONS']:
        return False, f"Запрещенное расширение файла: .{ext}"

    # Проверка на разрешенные расширения (если список не пуст)
    if app.config['ALLOWED_EXTENSIONS'] and ext not in app.config['ALLOWED_EXTENSIONS']:
        return False, f"Неподдерживаемый тип файла. Разрешенные расширения: {', '.join(app.config['ALLOWED_EXTENSIONS'])}"

    # Дополнительная проверка MIME-типа
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type and 'application/x-msdownload' in mime_type:
        return False, "Запрещенный тип файла"

    return True, "OK"

def generate_uuid_path(original_filename):
    """Генерация пути с UUID в поддиректориях"""
    # Генерируем UUID
    file_uuid = uuid.uuid4().hex

    # Создаем путь из первых двух символов UUID как поддиректории
    subdir1 = file_uuid[:2]
    subdir2 = file_uuid[2:4]

    # Получаем расширение
    ext = get_file_extension(original_filename)

    # Формируем имя файла с UUID
    if ext:
        filename = f"{file_uuid}.{ext}"
    else:
        filename = file_uuid

    # Создаем полный путь с поддиректориями
    relative_path = os.path.join(subdir1, subdir2, filename)

    return relative_path, file_uuid

def save_file_with_uuid(file, original_filename):
    """Сохранение файла с UUID именем и поддиректориями"""
    # Генерируем путь
    relative_path, file_uuid = generate_uuid_path(original_filename)
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], relative_path)

    # Создаем директории, если их нет
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    # Сохраняем файл
    file.save(full_path)

    return relative_path, file_uuid

def format_file_size(size_bytes):
    """Форматирование размера файла"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} ТБ"

@app.route('/')
def index():
    """Главная страница со списком файлов"""
    files_data = load_files_data()
    # Сортируем по дате загрузки (новые сверху)
    files_data.sort(key=lambda x: x['upload_date'], reverse=True)

    # Добавляем форматированный размер для отображения
    for file in files_data:
        file['size_formatted'] = format_file_size(file['file_size'])

    return render_template('index.html', files=files_data)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Обработка загрузки файла"""
    # Проверяем, был ли файл отправлен
    if 'file' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('index'))

    file = request.files['file']

    # Проверяем, выбран ли файл
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('index'))

    original_filename = file.filename

    # Проверяем расширение файла
    is_valid, error_message = allowed_file(original_filename)
    if not is_valid:
        flash(error_message, 'error')
        return redirect(url_for('index'))

    # Читаем содержимое файла для вычисления хэша
    file_data = file.read()
    file_hash = get_file_hash(file_data)
    file_size = len(file_data)

    # Проверяем на дубликат
    if is_duplicate(file_hash):
        flash(f'Файл "{original_filename}" уже существует в хранилище (дубликат)', 'error')
        return redirect(url_for('index'))

    # Сбросим указатель файла в начало, чтобы сохранить
    file.seek(0)

    try:
        # Сохраняем файл с UUID
        relative_path, file_uuid = save_file_with_uuid(file, original_filename)

        # Сохраняем информацию в JSON
        files_data = load_files_data()
        file_info = {
            'uuid_name': file_uuid,
            'original_name': original_filename,
            'relative_path': relative_path,
            'extension': get_file_extension(original_filename),
            'upload_date': datetime.now().isoformat(),
            'file_size': file_size,
            'file_hash': file_hash
        }
        files_data.append(file_info)
        save_files_data(files_data)

        flash(f'Файл "{original_filename}" успешно загружен! UUID: {file_uuid[:8]}...', 'success')

    except Exception as e:
        flash(f'Ошибка при загрузке файла: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/file/<uuid_name>')
def view_file_info(uuid_name):
    """Просмотр информации о конкретном файле"""
    files_data = load_files_data()
    file_info = next((f for f in files_data if f['uuid_name'] == uuid_name), None)

    if file_info:
        file_info['size_formatted'] = format_file_size(file_info['file_size'])
        return render_template('file_info.html', file=file_info)
    else:
        flash('Файл не найден', 'error')
        return redirect(url_for('index'))

@app.route('/delete_file/<uuid_name>')
def delete_file(uuid_name):
    """Удаление файла (опционально)"""
    files_data = load_files_data()
    file_info = next((f for f in files_data if f['uuid_name'] == uuid_name), None)

    if file_info:
        # Удаляем физический файл
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_info['relative_path'])
        if os.path.exists(file_path):
            os.remove(file_path)

        # Удаляем запись из JSON
        files_data = [f for f in files_data if f['uuid_name'] != uuid_name]
        save_files_data(files_data)

        flash(f'Файл "{file_info["original_name"]}" удален', 'success')
    else:
        flash('Файл не найден', 'error')

    return redirect(url_for('index'))

if __name__ == '__main__':
    # Создаем директорию для загрузок, если её нет
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # Инициализируем JSON файл
    init_data_file()
    app.run(debug=True, port=5000)
