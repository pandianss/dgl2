import os
import json
import sqlite3
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict

@dataclass
class Signatory:
    name_en: str
    name_ta: str = ""
    name_hi: str = ""
    designation_en: str = ""
    is_initiator: bool = False

@dataclass
class DocumentEntry:
    id: Optional[int] = None
    ref_no: str = ""
    date: str = ""
    doc_type: str = ""
    subject: str = ""
    department: str = ""
    created_by: str = ""
    content: Dict = field(default_factory=dict)
    frozen: bool = False
    batch_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class DocumentService:
    """
    Service to manage document generation, registration, and auditing.
    Acts as the 'Register' for all office notes and reports.
    """
    def __init__(self, db_path: str = "data/document_register.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            # Ensure we are using the connection correctly for the context manager
            conn.execute("""
                CREATE TABLE IF NOT EXISTS register (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ref_no TEXT UNIQUE,
                    date TEXT,
                    doc_type TEXT,
                    subject TEXT,
                    department TEXT,
                    created_by TEXT,
                    content TEXT,
                    timestamp TEXT,
                    frozen INTEGER DEFAULT 0,
                    batch_id TEXT
                )
            """)
            
            # Migration check: Ensure columns exist in older databases
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(register)")
            cols = [c[1] for c in cursor.fetchall()]
            
            if 'frozen' not in cols:
                conn.execute("ALTER TABLE register ADD COLUMN frozen INTEGER DEFAULT 0")
            if 'batch_id' not in cols:
                conn.execute("ALTER TABLE register ADD COLUMN batch_id TEXT")
            
            conn.commit()

    def register_document(self, entry: DocumentEntry):
        """Adds a document to the audit register."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO register (ref_no, date, doc_type, subject, department, created_by, content, timestamp, frozen, batch_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.ref_no, entry.date, entry.doc_type, entry.subject, 
                entry.department, entry.created_by, json.dumps(entry.content), 
                entry.timestamp, 1 if entry.frozen else 0, entry.batch_id
            ))
            conn.commit()
            entry.id = cursor.lastrowid
        return entry

    def get_all_entries(self) -> List[DocumentEntry]:
        """Retrieves all registered documents."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM register ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            entries = []
            for row in rows:
                d = dict(row)
                content_raw = d.pop('content', '{}')
                content = json.loads(content_raw)
                # Filter d to only include keys that are in DocumentEntry
                # and handle the boolean conversion for frozen
                if 'frozen' in d:
                    d['frozen'] = bool(d['frozen'])
                
                # Get the valid fields for DocumentEntry to avoid TypeError if DB has extra columns
                import inspect
                sig = inspect.signature(DocumentEntry)
                valid_keys = [p.name for p in sig.parameters.values()]
                filtered_d = {k: v for k, v in d.items() if k in valid_keys}
                
                entries.append(DocumentEntry(**filtered_d, content=content))
            return entries

            return cursor.rowcount

    def purge_unfrozen_by_type_and_date(self, doc_type: str, date_str: str) -> int:
        """Deletes documents of a specific type and date that are not frozen."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM register 
                WHERE doc_type = ? 
                AND date = ? 
                AND frozen = 0
            """, (doc_type, date_str))
            return cursor.rowcount

    def freeze_documents_by_type_and_date(self, doc_type: str, date_str: str) -> int:
        """Freezes all documents of a specific type and date."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE register 
                SET frozen = 1 
                WHERE doc_type = ? 
                AND date = ?
            """, (doc_type, date_str))
            return cursor.rowcount

    def freeze_document(self, ref_no: str) -> bool:
        """Freezes a specific document by its reference number."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE register SET frozen = 1 WHERE ref_no = ?", (ref_no,))
            return cursor.rowcount > 0

    def get_entries_by_type_and_date(self, doc_type: str, date_str: str) -> List[DocumentEntry]:
        """Retrieves documents of a specific type and date."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM register WHERE doc_type = ? AND date = ?", (doc_type, date_str))
            rows = cursor.fetchall()
            entries = []
            for row in rows:
                d = dict(row)
                content = json.loads(d.pop('content', '{}'))
                if 'frozen' in d: d['frozen'] = bool(d['frozen'])
                entries.append(DocumentEntry(**d, content=content))
            return entries

    def purge_unfrozen_documents(self, age_hours: int = 24) -> int:
        """Deletes documents that are not frozen and older than age_hours."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # ISO format comparison
            cursor.execute("""
                DELETE FROM register 
                WHERE frozen = 0 
                AND datetime(timestamp) < datetime('now', ?)
            """, (f'-{age_hours} hours',))
            return cursor.rowcount

    def generate_ref_no(self, doc_type: str, dept: str) -> str:
        """Generates a standard reference number: IOB/RO/DEPT/YYYY/SEQ"""
        year = datetime.now().year
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM register WHERE ref_no LIKE ?", (f"IOB/RO/{dept}/{year}%",))
            count = cursor.fetchone()[0] + 1
        return f"IOB/RO/{dept}/{year}/{count:03d}"
