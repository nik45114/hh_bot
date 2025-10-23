"""Database module for storing user preferences and bot state"""
import sqlite3
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    """SQLite database for user preferences and bot state"""
    
    def __init__(self, db_path: str = 'bot.db'):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # User preferences table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preferences (
                    chat_id INTEGER PRIMARY KEY,
                    role_domain TEXT DEFAULT 'IT',
                    remote_only BOOLEAN DEFAULT 0,
                    city TEXT DEFAULT 'Москва',
                    area_id INTEGER DEFAULT 1,
                    keywords TEXT,
                    role_level TEXT,
                    salary_min INTEGER DEFAULT 0,
                    schedule TEXT DEFAULT 'remote',
                    employment TEXT DEFAULT 'full',
                    experience TEXT DEFAULT 'between3And6',
                    auto_apply BOOLEAN DEFAULT 0,
                    prompt TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES users(chat_id)
                )
            ''')
            
            # Applications log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    vacancy_id TEXT NOT NULL,
                    vacancy_title TEXT,
                    company_name TEXT,
                    cover_letter TEXT,
                    status TEXT DEFAULT 'pending',
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    FOREIGN KEY (chat_id) REFERENCES users(chat_id)
                )
            ''')
            
            # Processed vacancies table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_vacancies (
                    chat_id INTEGER,
                    vacancy_id TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chat_id, vacancy_id),
                    FOREIGN KEY (chat_id) REFERENCES users(chat_id)
                )
            ''')
            
            logger.info("Database initialized successfully")
    
    def get_or_create_user(self, chat_id: int, username: str = None) -> Dict:
        """Get or create user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
            user = cursor.fetchone()
            
            if not user:
                # Create new user
                cursor.execute(
                    'INSERT INTO users (chat_id, username) VALUES (?, ?)',
                    (chat_id, username)
                )
                # Create default preferences
                cursor.execute(
                    'INSERT INTO preferences (chat_id) VALUES (?)',
                    (chat_id,)
                )
                logger.info(f"Created new user: {chat_id}")
                
                # Fetch the newly created user
                cursor.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
                user = cursor.fetchone()
            
            return dict(user) if user else None
    
    def get_user(self, chat_id: int) -> Optional[Dict]:
        """Get user by chat_id"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
            user = cursor.fetchone()
            return dict(user) if user else None
    
    def get_preferences(self, chat_id: int) -> Dict:
        """Get user preferences"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM preferences WHERE chat_id = ?', (chat_id,))
            prefs = cursor.fetchone()
            
            if prefs:
                result = dict(prefs)
                # Parse JSON fields
                if result.get('keywords'):
                    try:
                        result['keywords'] = json.loads(result['keywords'])
                    except:
                        result['keywords'] = []
                else:
                    result['keywords'] = []
                return result
            
            # Return defaults if not found
            return {
                'chat_id': chat_id,
                'role_domain': 'IT',
                'remote_only': False,
                'city': 'Москва',
                'area_id': 1,
                'keywords': [],
                'role_level': None,
                'salary_min': 0,
                'schedule': 'remote',
                'employment': 'full',
                'experience': 'between3And6',
                'auto_apply': False,
                'prompt': None
            }
    
    def update_preferences(self, chat_id: int, **kwargs):
        """Update user preferences"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Convert keywords list to JSON if present
            if 'keywords' in kwargs and isinstance(kwargs['keywords'], list):
                kwargs['keywords'] = json.dumps(kwargs['keywords'], ensure_ascii=False)
            
            # Build update query
            fields = ', '.join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values())
            values.append(chat_id)
            
            cursor.execute(
                f'UPDATE preferences SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE chat_id = ?',
                values
            )
            
            logger.info(f"Updated preferences for user {chat_id}")
    
    def log_application(self, chat_id: int, vacancy_id: str, vacancy_title: str,
                       company_name: str, cover_letter: str, status: str = 'success',
                       error_message: str = None):
        """Log job application"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO applications 
                (chat_id, vacancy_id, vacancy_title, company_name, cover_letter, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (chat_id, vacancy_id, vacancy_title, company_name, cover_letter, status, error_message))
            
            logger.info(f"Logged application: {vacancy_id} for user {chat_id} - {status}")
    
    def mark_vacancy_processed(self, chat_id: int, vacancy_id: str):
        """Mark vacancy as processed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR IGNORE INTO processed_vacancies (chat_id, vacancy_id) VALUES (?, ?)',
                (chat_id, vacancy_id)
            )
    
    def is_vacancy_processed(self, chat_id: int, vacancy_id: str) -> bool:
        """Check if vacancy was already processed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT 1 FROM processed_vacancies WHERE chat_id = ? AND vacancy_id = ?',
                (chat_id, vacancy_id)
            )
            return cursor.fetchone() is not None
    
    def get_applications_count(self, chat_id: int, since: datetime = None) -> int:
        """Get count of applications"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if since:
                cursor.execute(
                    'SELECT COUNT(*) FROM applications WHERE chat_id = ? AND applied_at >= ?',
                    (chat_id, since)
                )
            else:
                cursor.execute(
                    'SELECT COUNT(*) FROM applications WHERE chat_id = ?',
                    (chat_id,)
                )
            
            return cursor.fetchone()[0]
    
    def get_recent_applications(self, chat_id: int, limit: int = 10) -> List[Dict]:
        """Get recent applications"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM applications 
                WHERE chat_id = ? 
                ORDER BY applied_at DESC 
                LIMIT ?
            ''', (chat_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
