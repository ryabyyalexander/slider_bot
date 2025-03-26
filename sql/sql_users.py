import sqlite3
from data import name_bot


class BotDatabase:
    def __init__(self, db_name):
        self.db_name = f"{db_name}.db"

    def execute_query(self, query, params=()):
        with sqlite3.connect(self.db_name) as db:
            cursor = db.cursor()
            cursor.execute(query, params)
            return cursor

    def sql_new_user(self, user_id, first_name, last_name, user_name, is_admin, is_vendor=False):
        data = (user_id, first_name, last_name, user_name, is_admin, is_vendor)
        cursor = self.execute_query("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone() is None:
            self.execute_query('''
                INSERT INTO users (user_id, first_name, last_name, user_name, is_admin, is_vendor)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', data)
            return True
        else:
            return False

    def sql_get_user(self, user_id, *fields):
        fields_to_select = ', '.join(fields) if fields else '*'
        cursor = self.execute_query(f"SELECT {fields_to_select} FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            return result
        else:
            return None

    def sql_user_exists(self, user_id):
        """
        Проверяет, существует ли пользователь с указанным user_id в базе данных.
        Возвращает True, если пользователь существует, и False, если нет.
        """
        cursor = self.execute_query("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None

    def update_restart_count(self, user_id):
        self.execute_query('''
            UPDATE users SET restart_count = restart_count + 1 WHERE user_id = ?
            ''', (user_id,))

    def update_user_blocked(self, user_id, status):
        self.execute_query(f'''
            UPDATE users SET user_blocked = {status} WHERE user_id = ?
            ''', (user_id,))

    def get_restart_count(self, user_id):
        cursor = self.execute_query("SELECT restart_count FROM users WHERE user_id=?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0


# Инициализация базы данных и создание таблиц
data_users = BotDatabase(name_bot)
data_users.execute_query("""CREATE TABLE IF NOT EXISTS users(
    user_id INT PRIMARY KEY,
    first_name VARCHAR,
    last_name VARCHAR,
    user_name TEXT,
    is_admin BOOL,
    is_vendor BOOL,
    restart_count INT DEFAULT 0,
    user_blocked BOOL DEFAULT 0)""")
