# core/db.py
import sqlite3
from contextlib import contextmanager
from core.config import DB_PATH


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db():
    """Create the SQLite schema if it doesn't exist."""
    with _connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                modality TEXT NOT NULL,
                event TEXT,
                score REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                fused_score REAL NOT NULL,
                video_label TEXT,
                video_score REAL,
                audio_label TEXT,
                audio_score REAL,
                text_label TEXT,
                text_score REAL,
                raw_text TEXT,
                lat REAL,
                lon REAL,
                summary TEXT
            )
        """)


# ── Write helpers ───────────────────────────────────────────────────
def log_event(timestamp, modality, event, score):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO events (timestamp, modality, event, score) VALUES (?, ?, ?, ?)",
            (timestamp, modality, event, score),
        )


def log_incident(incident):
    with _connect() as conn:
        conn.execute(
            """INSERT INTO incidents (
                timestamp, type, fused_score,
                video_label, video_score,
                audio_label, audio_score,
                text_label, text_score,
                raw_text, lat, lon, summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                incident.timestamp,
                incident.type,
                round(incident.fused_score, 3),
                getattr(incident.video, "label", None) if incident.video else None,
                round(getattr(incident.video, "score", 0.0), 3) if incident.video else None,
                getattr(incident.audio, "label", None) if incident.audio else None,
                round(getattr(incident.audio, "score", 0.0), 3) if incident.audio else None,
                getattr(incident.text, "label", None) if incident.text else None,
                round(getattr(incident.text, "score", 0.0), 3) if incident.text else None,
                " | ".join(incident.raw_text) if incident.raw_text else "",
                incident.lat,
                incident.lon,
                incident.summary or "",
            ),
        )


# ── Read helpers (for API) ──────────────────────────────────────────
def read_incidents():
    """Return all fused incidents as list of dicts, oldest first."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM incidents ORDER BY id ASC").fetchall()
    return [dict(row) for row in rows]


def read_events():
    """Return all raw modality events as list of dicts, oldest first."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM events ORDER BY id ASC").fetchall()
    return [dict(row) for row in rows]
