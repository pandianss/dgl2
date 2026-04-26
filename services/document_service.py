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
                    timestamp TEXT
                )
            """)

    def register_document(self, entry: DocumentEntry):
        """Adds a document to the audit register."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO register (ref_no, date, doc_type, subject, department, created_by, content, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.ref_no, entry.date, entry.doc_type, entry.subject, 
                entry.department, entry.created_by, json.dumps(entry.content), entry.timestamp
            ))
            entry.id = cursor.lastrowid
        return entry

    def get_all_entries(self) -> List[DocumentEntry]:
        """Retrieves all registered documents."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM register ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            return [DocumentEntry(**{k: v for k, v in dict(row).items() if k != 'content'}, 
                                 content=json.loads(row['content'])) for row in rows]

    def generate_ref_no(self, doc_type: str, dept: str) -> str:
        """Generates a standard reference number: IOB/RO/DEPT/YYYY/SEQ"""
        year = datetime.now().year
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM register WHERE ref_no LIKE ?", (f"IOB/RO/{dept}/{year}%",))
            count = cursor.fetchone()[0] + 1
        return f"IOB/RO/{dept}/{year}/{count:03d}"
