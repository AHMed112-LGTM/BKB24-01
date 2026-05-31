import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


class UserModel:
    USERS_FILE = 'users.json'

    @staticmethod
    def load_users():
        """Загрузка пользователей из JSON файла"""
        if not os.path.exists(UserModel.USERS_FILE):
            # Создаем файл с администратором по умолчанию
            default_admin = {
                "admin": {
                    "password": generate_password_hash("Admin@123"),
                    "registration_date": datetime.now().isoformat(),
                    "last_login": None,
                    "role": "admin"
                }
            }
            UserModel.save_users(default_admin)
            return default_admin

        with open(UserModel.USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def save_users(users):
        """Сохранение пользователей в JSON файл"""
        with open(UserModel.USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=4)

    @staticmethod
    def user_exists(username):
        """Проверка существования пользователя"""
        users = UserModel.load_users()
        return username in users

    @staticmethod
    def is_admin(username):
        """Проверка является ли пользователь администратором"""
        users = UserModel.load_users()
        if username in users:
            return users[username].get('role') == 'admin'
        return False

    @staticmethod
    def register_user(username, password, is_admin=False):
        """Регистрация нового пользователя"""
        users = UserModel.load_users()

        # Проверка на существование пользователя
        if UserModel.user_exists(username):
            return False, "Пользователь с таким именем уже существует"

        # Создание нового пользователя
        users[username] = {
            "password": generate_password_hash(password),
            "registration_date": datetime.now().isoformat(),
            "last_login": None,
            "role": "admin" if is_admin else "user"
        }

        UserModel.save_users(users)
        role_text = "администратор" if is_admin else "пользователь"
        return True, f"Пользователь {username} успешно создан как {role_text}"

    @staticmethod
    def delete_user(username):
        """Удаление пользователя"""
        users = UserModel.load_users()

        if username not in users:
            return False, "Пользователь не найден"

        if username == "admin":
            return False, "Нельзя удалить главного администратора"

        # Нельзя удалить самого себя
        return True, "Пользователь удален"

    @staticmethod
    def perform_delete(username):
        """Выполнение удаления пользователя"""
        users = UserModel.load_users()
        del users[username]
        UserModel.save_users(users)

    @staticmethod
    def authenticate_user(username, password):
        """Аутентификация пользователя"""
        users = UserModel.load_users()

        if username not in users:
            return False

        if check_password_hash(users[username]["password"], password):
            # Обновляем дату последней авторизации
            users[username]["last_login"] = datetime.now().isoformat()
            UserModel.save_users(users)
            return True

        return False

    @staticmethod
    def get_all_users():
        """Получить всех пользователей"""
        return UserModel.load_users()