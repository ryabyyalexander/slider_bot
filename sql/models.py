# models.py
import sqlite3


class BotDatabase:
    def __init__(self, db_name):
        self.db_name = f"{db_name}.db"

    def execute_query(self, query, params=()):
        with sqlite3.connect(self.db_name) as db:
            cursor = db.cursor()
            cursor.execute(query, params)
            db.commit()  # Добавлено явное подтверждение изменений
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
        return False

    def sql_get_user(self, user_id, *fields):
        fields_to_select = ', '.join(fields) if fields else '*'
        cursor = self.execute_query(f"SELECT {fields_to_select} FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()

    def sql_user_exists(self, user_id):
        cursor = self.execute_query("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None

    def update_restart_count(self, user_id):
        self.execute_query('''
            UPDATE users SET restart_count = restart_count + 1 WHERE user_id = ?
            ''', (user_id,))

    def update_user_blocked(self, user_id, status):
        self.execute_query('''
            UPDATE users SET user_blocked = ? WHERE user_id = ?
            ''', (status, user_id))

    def get_restart_count(self, user_id):
        cursor = self.execute_query("SELECT restart_count FROM users WHERE user_id=?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0

    def add_photo(self, file_id, added_by, caption=None):
        if not self.sql_user_exists(added_by):
            raise ValueError("User does not exist")

        self.execute_query('''
            INSERT INTO photos (file_id, added_by, caption, added_date)
            VALUES (?, ?, ?, datetime('now'))
            ''', (file_id, added_by, caption))
        return self.execute_query("SELECT last_insert_rowid()").fetchone()[0]

    def get_all_photos(self):
        return self.execute_query("SELECT file_id FROM photos").fetchall()

    def get_user_photos(self, user_id):
        return self.execute_query("SELECT file_id FROM photos WHERE added_by = ?", (user_id,)).fetchall()

    def delete_photo(self, photo_id):
        self.execute_query("DELETE FROM photos WHERE id = ?", (photo_id,))

    def get_photo_count(self):
        return self.execute_query("SELECT COUNT(*) FROM photos").fetchone()[0]


# Инициализация базы данных и создание таблиц
data_users = BotDatabase('slider.db')

data_users.execute_query("""CREATE TABLE IF NOT EXISTS users(
    user_id INT PRIMARY KEY,
    first_name VARCHAR,
    last_name VARCHAR,
    user_name TEXT,
    is_admin BOOL,
    is_vendor BOOL,
    restart_count INT DEFAULT 0,
    user_blocked BOOL DEFAULT 0)""")

data_users.execute_query("""CREATE TABLE IF NOT EXISTS photos(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT NOT NULL,
    added_by INT NOT NULL,
    caption TEXT,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(added_by) REFERENCES users(user_id))""")