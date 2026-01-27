import aiosqlite
import os
from config import DATABASE_PATH

class Database:
    """Класс для работы с базой данных"""
    
    @staticmethod
    async def init():
        """Инициализация базы данных и создание таблиц"""
        # Создаём папку database если её нет
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Таблица предупреждений
            await db.execute('''
                CREATE TABLE IF NOT EXISTS warns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    date TEXT NOT NULL
                )
            ''')
            
            # Таблица участников
            await db.execute('''
                CREATE TABLE IF NOT EXISTS members (
                    user_id INTEGER PRIMARY KEY,
                    nickname TEXT NOT NULL,
                    join_date TEXT NOT NULL,
                    rank TEXT DEFAULT 'Новичок',
                    activity_points INTEGER DEFAULT 0
                )
            ''')
            
            # Таблица отчётов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    participants INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    screenshot_url TEXT,
                    date TEXT NOT NULL
                )
            ''')
            
            # Таблица заявок
            await db.execute('''
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    nickname TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    experience TEXT NOT NULL,
                    about TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    date TEXT NOT NULL,
                    reviewed_by INTEGER,
                    review_date TEXT
                )
            ''')
            
            await db.commit()
            print('✅ База данных инициализирована')
    
    @staticmethod
    async def add_warn(user_id: int, moderator_id: int, reason: str, date: str):
        """Добавить предупреждение"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                'INSERT INTO warns (user_id, moderator_id, reason, date) VALUES (?, ?, ?, ?)',
                (user_id, moderator_id, reason, date)
            )
            await db.commit()
    
    @staticmethod
    async def get_warns(user_id: int):
        """Получить все предупреждения пользователя"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                'SELECT id, reason, date, moderator_id FROM warns WHERE user_id = ? ORDER BY date DESC',
                (user_id,)
            )
            return await cursor.fetchall()
    
    @staticmethod
    async def get_warn_count(user_id: int):
        """Получить количество предупреждений"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                'SELECT COUNT(*) FROM warns WHERE user_id = ?',
                (user_id,)
            )
            return (await cursor.fetchone())[0]
    
    @staticmethod
    async def remove_warn(warn_id: int):
        """Удалить предупреждение по ID"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute('DELETE FROM warns WHERE id = ?', (warn_id,))
            await db.commit()
    
    @staticmethod
    async def add_member(user_id: int, nickname: str, join_date: str):
        """Добавить участника в базу"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                'INSERT OR REPLACE INTO members (user_id, nickname, join_date) VALUES (?, ?, ?)',
                (user_id, nickname, join_date)
            )
            await db.commit()
    
    @staticmethod
    async def get_member(user_id: int):
        """Получить информацию об участнике"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                'SELECT * FROM members WHERE user_id = ?',
                (user_id,)
            )
            return await cursor.fetchone()
    
    @staticmethod
    async def add_report(user_id: int, event_type: str, participants: int, 
                        description: str, date: str, screenshot_url: str = None):
        """Добавить отчёт"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                'INSERT INTO reports (user_id, event_type, participants, description, date, screenshot_url) VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, event_type, participants, description, date, screenshot_url)
            )
            await db.commit()
    
    @staticmethod
    async def get_user_reports(user_id: int, limit: int = 10):
        """Получить отчёты пользователя"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                'SELECT * FROM reports WHERE user_id = ? ORDER BY date DESC LIMIT ?',
                (user_id, limit)
            )
            return await cursor.fetchall()
