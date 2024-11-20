import sqlite3
from typing import List, Dict, Optional
import json
from datetime import datetime

class Database:
    def __init__(self, db_path="summaries.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Create summaries table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    input_text TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    prompt_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    original_filename TEXT,
                    file_type TEXT,
                    metadata TEXT
                )
            """)
            
            # Create versions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS summary_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    summary_id INTEGER,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (summary_id) REFERENCES summaries(id) ON DELETE CASCADE
                )
            """)

    def save_summary(self, input_text: str, summary: str, prompt_type: str, 
                    original_filename: Optional[str] = None, 
                    file_type: Optional[str] = None,
                    metadata: Optional[Dict] = None) -> int:
        metadata_json = json.dumps(metadata) if metadata else None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO summaries 
                (input_text, summary, prompt_type, original_filename, file_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (input_text, summary, prompt_type, original_filename, file_type, metadata_json)
            )
            return cursor.lastrowid

    def save_summary_version(self, summary_id: int, content: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO summary_versions (summary_id, content)
                VALUES (?, ?)
                """,
                (summary_id, content)
            )
            return cursor.lastrowid

    def get_summaries(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT 
                    id,
                    prompt_type,
                    created_at,
                    original_filename,
                    file_type,
                    substr(input_text, 1, 200) as input_preview,
                    substr(summary, 1, 200) as summary_preview,
                    metadata
                FROM summaries 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_summaries_count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM summaries")
            return cursor.fetchone()[0]

    def get_summary_versions(self, summary_id: int) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM summary_versions 
                WHERE summary_id = ? 
                ORDER BY created_at DESC
                """,
                (summary_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_summary(self, summary_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM summaries WHERE id = ?",
                (summary_id,)
            )
            result = cursor.fetchone()
            if not result:
                return None
            
            # Convert to dict
            summary_dict = dict(result)
            
            # Parse metadata if exists
            if summary_dict.get('metadata'):
                summary_dict['metadata'] = json.loads(summary_dict['metadata'])
            
            return summary_dict

    def delete_summary(self, summary_id: int) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "DELETE FROM summaries WHERE id = ?",
                    (summary_id,)
                )
                return True
        except Exception:
            return False

    def update_summary(self, summary_id: int, content: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                # First, copy current version to versions table
                current = self.get_summary(summary_id)
                if current:
                    self.save_summary_version(summary_id, current['summary'])
                
                # Then update the main summary
                conn.execute(
                    "UPDATE summaries SET summary = ? WHERE id = ?",
                    (content, summary_id)
                )
                return True
        except Exception:
            return False