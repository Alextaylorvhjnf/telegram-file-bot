import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="films_bot.db"):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS films (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                film_code TEXT UNIQUE NOT NULL,
                file_id TEXT NOT NULL,
                title TEXT,
                caption TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ دیتابیس آماده است")
    
    def add_film(self, film_code, file_id, title=None, caption=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO films (film_code, file_id, title, caption)
                VALUES (?, ?, ?, ?)
            ''', (film_code, file_id, title, caption))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"خطا در ذخیره فیلم: {e}")
            return False
        finally:
            conn.close()
    
    def get_film(self, film_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT film_code, file_id, title, caption FROM films WHERE film_code = ?', (film_code,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'film_code': result[0],
                'file_id': result[1],
                'title': result[2],
                'caption': result[3]
            }
        return None
    
    def get_all_films(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT film_code, title FROM films ORDER BY added_at DESC')
        results = cursor.fetchall()
        conn.close()
        
        return [{'film_code': row[0], 'title': row[1] or row[0]} for row in results]
    
    def add_user(self, user_id, username, first_name, last_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"خطا در ذخیره کاربر: {e}")
            return False
        finally:
            conn.close()
