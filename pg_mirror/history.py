"""History / sqlite-based tracking for backups

Stores basic metadata about performed backups in a sqlite database
located by default at ~/.pg_mirror/pg_mirror.db
"""
from pathlib import Path
import sqlite3
import json
from datetime import datetime
from typing import Optional

DEFAULT_DIR = Path.home() / '.pg_mirror'
DEFAULT_DB = DEFAULT_DIR / 'pg_mirror.db'

SCHEMA = '''
CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    database TEXT NOT NULL,
    username TEXT NOT NULL,
    backup_path TEXT NOT NULL,
    size_mb REAL,
    status TEXT,
    extra TEXT
);
'''


def _ensure_db(db_path: Optional[Path]):
    db = db_path or DEFAULT_DB
    db_parent = db.parent
    db_parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def record_backup(host: str, port: int, database: str, username: str, backup_path: str, size_mb: float = None, status: str = 'created', extra: dict = None, db_path: Optional[str] = None):
    """Insert a backup record and return the inserted row id"""
    db = Path(db_path) if db_path else DEFAULT_DB
    conn = _ensure_db(db)
    cur = conn.cursor()

    now = datetime.utcnow().isoformat() + 'Z'
    extra_text = json.dumps(extra) if extra else None

    cur.execute(
        '''INSERT INTO backups (created_at, host, port, database, username, backup_path, size_mb, status, extra)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (now, host, port, database, username, backup_path, size_mb, status, extra_text)
    )
    conn.commit()
    rowid = cur.lastrowid
    conn.close()
    return rowid


def update_backup(backup_id: int, status: Optional[str] = None, extra: Optional[dict] = None, db_path: Optional[str] = None):
    db = Path(db_path) if db_path else DEFAULT_DB
    conn = _ensure_db(db)
    cur = conn.cursor()
    updates = []
    params = []
    if status is not None:
        updates.append('status = ?')
        params.append(status)
    if extra is not None:
        updates.append('extra = ?')
        params.append(json.dumps(extra))
    if not updates:
        conn.close()
        return False
    params.append(backup_id)
    cur.execute(f"UPDATE backups SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return True


def get_backup(backup_id: int, db_path: Optional[str] = None):
    db = Path(db_path) if db_path else DEFAULT_DB
    conn = _ensure_db(db)
    cur = conn.cursor()
    cur.execute('SELECT id, created_at, host, port, database, username, backup_path, size_mb, status, extra FROM backups WHERE id = ?', (backup_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    (id_, created_at, host, port, database, username, backup_path, size_mb, status, extra) = row
    return {
        'id': id_,
        'created_at': created_at,
        'host': host,
        'port': port,
        'database': database,
        'username': username,
        'backup_path': backup_path,
        'size_mb': size_mb,
        'status': status,
        'extra': json.loads(extra) if extra else None
    }
