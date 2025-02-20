# article_cache.py
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json

class ArticleCache:
    def __init__(self, db_path: str = "article_cache.db", cache_days: int = 7):
        """
        Initialize article cache with SQLite backend
        
        Args:
            db_path: Path to SQLite database file
            cache_days: Number of days to keep articles in cache
        """
        self.db_path = db_path
        self.cache_days = cache_days
        self._init_db()

    def _init_db(self):
        """Initialize database table if it doesn't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS article_scores (
                    url TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    reason TEXT,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def get_cached_score(self, url: str) -> Optional[Dict]:
        """
        Get cached score for article if it exists and is not expired
        
        Returns:
            Dict with score info or None if not found/expired
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cutoff_date = datetime.now() - timedelta(days=self.cache_days)
            
            result = conn.execute("""
                SELECT url, title, score, reason, cached_at
                FROM article_scores
                WHERE url = ? AND cached_at > ?
            """, (url, cutoff_date)).fetchone()
            
            if result:
                return dict(result)
            return None

    def cache_score(self, url: str, title: str, score: int, reason: str):
        """Cache a new article score"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO article_scores (url, title, score, reason)
                VALUES (?, ?, ?, ?)
            """, (url, title, score, reason))
            conn.commit()

    def get_all_cached(self) -> List[Dict]:
        """Get all non-expired cached articles"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cutoff_date = datetime.now() - timedelta(days=self.cache_days)
            
            results = conn.execute("""
                SELECT url, title, score, reason, cached_at
                FROM article_scores
                WHERE cached_at > ?
                ORDER BY score DESC
            """, (cutoff_date,)).fetchall()
            
            return [dict(row) for row in results]

    def cleanup_expired(self):
        """Remove expired cache entries"""
        with sqlite3.connect(self.db_path) as conn:
            cutoff_date = datetime.now() - timedelta(days=self.cache_days)
            conn.execute("DELETE FROM article_scores WHERE cached_at < ?", (cutoff_date,))
            conn.commit()
