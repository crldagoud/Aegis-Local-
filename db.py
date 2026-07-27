"""
Stockage local des entrées du coffre dans une base SQLite.
Les mots de passe sont TOUJOURS stockés chiffrés (jamais en clair).
"""

import os
import sqlite3
from datetime import datetime, timezone


def get_connection(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site TEXT NOT NULL,
            username TEXT,
            password_enc BLOB NOT NULL,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.commit()
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_entry(conn: sqlite3.Connection, site: str, username: str, password_enc: bytes) -> int:
    now = _now()
    cur = conn.execute(
        "INSERT INTO entries (site, username, password_enc, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (site, username, password_enc, now, now),
    )
    conn.commit()
    return cur.lastrowid


def add_entries_bulk(conn: sqlite3.Connection, entries: list[tuple[str, str, bytes]]) -> int:
    """Insertion groupée (utilisée par l'import navigateur). Retourne le nombre inséré."""
    now = _now()
    conn.executemany(
        "INSERT INTO entries (site, username, password_enc, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        [(site, username, pwd_enc, now, now) for site, username, pwd_enc in entries],
    )
    conn.commit()
    return len(entries)


def update_entry(conn: sqlite3.Connection, entry_id: int, *, site=None, username=None, password_enc=None) -> None:
    fields = []
    values = []
    if site is not None:
        fields.append("site = ?")
        values.append(site)
    if username is not None:
        fields.append("username = ?")
        values.append(username)
    if password_enc is not None:
        fields.append("password_enc = ?")
        values.append(password_enc)
    fields.append("updated_at = ?")
    values.append(_now())
    values.append(entry_id)

    conn.execute(f"UPDATE entries SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()


def delete_entry(conn: sqlite3.Connection, entry_id: int) -> None:
    conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    conn.commit()


def get_all_entries(conn: sqlite3.Connection):
    """Retourne une liste de tuples (id, site, username, password_enc), triée par site."""
    cur = conn.execute("SELECT id, site, username, password_enc FROM entries ORDER BY site COLLATE NOCASE")
    return cur.fetchall()


def reencrypt_all(conn: sqlite3.Connection, old_fernet, new_fernet) -> None:
    """Déchiffre tout avec l'ancienne clé et rechiffre avec la nouvelle (changement de mot de passe maître)."""
    rows = conn.execute("SELECT id, password_enc FROM entries").fetchall()
    for entry_id, password_enc in rows:
        plain = old_fernet.decrypt(password_enc)
        new_enc = new_fernet.encrypt(plain)
        conn.execute("UPDATE entries SET password_enc = ? WHERE id = ?", (new_enc, entry_id))
    conn.commit()
