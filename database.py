# database.py
import sqlite3
import os
from config import logger

USER_DB = "users.db"
LEADERBOARD_DB = USER_DB  # both tables in same DB

def init_databases():
    db_path = os.path.abspath(USER_DB)
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT
                )
            ''')
            # leaderboard table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leaderboard (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    score INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error initializing database: {e}")
        raise

def save_user(user_id, username, first_name, admin_ids):
    # Do not save admin users (keeps parity with original)
    if user_id in admin_ids:
        return
    try:
        with sqlite3.connect(USER_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO users (user_id, username, first_name) VALUES (?, ?, ?)',
                (user_id, username if username else "ندارد", first_name if first_name else "بدون نام")
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error saving user {user_id}: {e}")

def update_leaderboard(user_id, first_name, points):
    try:
        with sqlite3.connect(LEADERBOARD_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT OR REPLACE INTO leaderboard (user_id, first_name, score)
                   VALUES (?, ?, COALESCE((SELECT score FROM leaderboard WHERE user_id = ?), 0) + ?)''',
                (user_id, first_name, user_id, points)
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error updating leaderboard for user {user_id}: {e}")

def get_leaderboard():
    try:
        with sqlite3.connect(LEADERBOARD_DB) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT l.first_name, u.username, l.score
                FROM leaderboard l
                JOIN users u ON l.user_id = u.user_id
                ORDER BY l.score DESC LIMIT 5
            ''')
            return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Error fetching leaderboard: {e}")
        return []
