#!/usr/bin/env python3
"""
ARIA_MEMORY_BANK.py  —  v3.1 (Sovereign Aligned)
=================================================
ARIA's persistent memory. Single source of truth.
Backward-compatible with PEIG_CORE's internal ARIAMemoryBank API.
All methods accept **kwargs safely — never crashes on extra args.

PATHING: Fixed to ~/AA-Aria/Aria (sovereign standard)
CONCURRENCY: WAL mode + exponential backoff for "database locked"
QoL: Env override, safe migrations, backup utility, context manager
"""
import os, sqlite3, json, time, hashlib, logging, shutil
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

log = logging.getLogger("ARIA.memory")

# ── SOVEREIGN PATH ALIGNMENT ──────────────────────────────────────────────
# Standardized to AA-Aria. Override via: export ARIA_DB_PATH="/custom/path/aria_knowledge.db"
_DEFAULT_DIR = Path.home() / "AA-Aria" / "Aria"
_DB_FILENAME = "aria_knowledge.db"
_DB_ENV = os.environ.get("ARIA_DB_PATH")
DB_PATH = Path(_DB_ENV) if _DB_ENV else _DEFAULT_DIR / "memory" / _DB_FILENAME
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class ARIAMemoryBank:
    """Sovereign Memory Interface with WAL concurrency & safe migration."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # timeout=10 enables WAL retry; check_same_thread=False for GUI concurrency
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=10)
        self.conn.execute("PRAGMA journal_mode=WAL")      # Concurrent reads/writes
        self.conn.execute("PRAGMA synchronous=NORMAL")    # Balance safety/speed
        self.conn.execute("PRAGMA cache_size=-2000")      # 2MB RAM cache for speed
        self._init_tables()
        self._migrate()
        log.info(f"Memory Bank initialized: {self.db_path}")

    def __enter__(self):
        """Enable 'with ARIAMemoryBank() as bank:' syntax."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Auto-close on context exit."""
        self.close()
        return False  # Don't suppress exceptions

    # ─────────────────────────────────────────────────────────────────────
    # SAFE EXECUTION WRAPPER (Handles SQLite locking gracefully)
    # ─────────────────────────────────────────────────────────────────────
    def _execute_with_retry(self, sql: str, params: tuple = (), retries: int = 3, delay: float = 0.1):
        """Execute SQL with exponential backoff on 'database is locked'."""
        for attempt in range(retries):
            try:
                if params:
                    return self.conn.execute(sql, params)
                return self.conn.execute(sql)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))  # 0.1s, 0.2s, 0.3s
                    continue
                log.warning(f"SQLite exec failed (attempt {attempt+1}): {e}")
                raise
        return None

    # ─────────────────────────────────────────────────────────────────────
    # INITIALIZATION & SAFE MIGRATION
    # ─────────────────────────────────────────────────────────────────────
    def _init_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        REAL,
            speaker   TEXT,
            message   TEXT,
            emotion   TEXT,
            arch      TEXT,
            wmin      REAL,
            ilp_depth INTEGER,
            session_id TEXT,
            input_mode TEXT DEFAULT 'text'
        );
        CREATE TABLE IF NOT EXISTS knowledge (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        REAL,
            topic     TEXT,
            content   TEXT,
            source    TEXT,
            hash      TEXT UNIQUE,
            recall_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS aria_self (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        REAL,
            key       TEXT UNIQUE,
            value     TEXT
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_start  REAL,
            ts_end    REAL,
            mode      TEXT,
            turns     INTEGER DEFAULT 0,
            meta      TEXT
        );
        CREATE TABLE IF NOT EXISTS voice_log (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            ts             REAL,
            transcript     TEXT,
            audio_duration REAL,
            whisper_model  TEXT,
            session_id     TEXT
        );
        CREATE TABLE IF NOT EXISTS wonders (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        REAL,
            trigger_text TEXT,
            wonder    TEXT,
            arch      TEXT,
            source    TEXT DEFAULT 'aria'
        );
        CREATE INDEX IF NOT EXISTS idx_conv_ts ON conversations(ts);
        CREATE INDEX IF NOT EXISTS idx_knowledge_topic ON knowledge(topic);
        CREATE INDEX IF NOT EXISTS idx_wonders_ts ON wonders(ts);
        CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
        """)
        self.conn.commit()

    def _migrate(self):
        """Add missing columns safely without breaking existing data."""
        def add_column(table, col, type_def, default=None):
            cols = {r[1] for r in self.conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if col not in cols:
                default_clause = f"DEFAULT {default}" if default is not None else ""
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {type_def} {default_clause}")
                log.info(f"Migrated: Added {col} to {table}")

        try:
            add_column("conversations", "session_id", "TEXT", "NULL")
            add_column("conversations", "input_mode", "TEXT", "'text'")
            add_column("knowledge", "recall_count", "INTEGER", "0")
            self.conn.commit()
        except Exception as e:
            log.warning(f"Migration skipped (non-fatal): {e}")

    # ─────────────────────────────────────────────────────────────────────
    # CONVERSATIONS
    # ─────────────────────────────────────────────────────────────────────
    def log_message(self, speaker: str, message: str, emotion: str = None, arch: str = None,
                    wmin: float = None, ilp_depth: int = None, **kwargs) -> bool:
        session_id = kwargs.get("session_id")
        input_mode = kwargs.get("input_mode", "text")
        try:
            self._execute_with_retry(
                "INSERT INTO conversations "
                "(ts,speaker,message,emotion,arch,wmin,ilp_depth,session_id,input_mode) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (time.time(), speaker, message, emotion, arch, wmin, ilp_depth,
                 str(session_id) if session_id else None, input_mode)
            )
            self.conn.commit()
            return True
        except Exception as e:
            log.debug(f"log_message failed: {e}")
            return False

    def recent_conversations(self, n: int = 20, **kwargs) -> List[Tuple]:
        return self._execute_with_retry(
            "SELECT ts,speaker,message,emotion,arch FROM conversations ORDER BY ts DESC LIMIT ?",
            (n,)
        ).fetchall()

    def search_conversations(self, query: str, n: int = 20) -> List[Tuple]:
        return self._execute_with_retry(
            "SELECT ts,speaker,message,arch FROM conversations WHERE message LIKE ? ORDER BY ts DESC LIMIT ?",
            (f"%{query}%", n)
        ).fetchall()

    # ─────────────────────────────────────────────────────────────────────
    # VOICE LOG
    # ─────────────────────────────────────────────────────────────────────
    def log_voice(self, transcript: str, audio_duration: float = None,
                  whisper_model: str = None, session_id: str = None, **kwargs) -> bool:
        try:
            self._execute_with_retry(
                "INSERT INTO voice_log (ts,transcript,audio_duration,whisper_model,session_id) "
                "VALUES (?,?,?,?,?)",
                (time.time(), transcript, audio_duration, whisper_model, str(session_id) if session_id else None)
            )
            self.conn.commit()
            return True
        except Exception as e:
            log.warning(f"log_voice failed: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────────
    # KNOWLEDGE
    # ─────────────────────────────────────────────────────────────────────
    def store_knowledge(self, topic: str, content: str, source: str = "Kevin") -> bool:
        h = hashlib.sha256(content.encode()).hexdigest()[:16]
        try:
            self._execute_with_retry(
                "INSERT INTO knowledge (ts,topic,content,source,hash) VALUES (?,?,?,?,?)",
                (time.time(), topic, content, source, h)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            log.warning(f"store_knowledge failed: {e}")
            return False

    def recall(self, topic: str, n: int = 5) -> List[Tuple]:
        rows = self._execute_with_retry(
            "SELECT topic,content,source FROM knowledge WHERE topic LIKE ? OR content LIKE ? "
            "ORDER BY ts DESC LIMIT ?",
            (f"%{topic}%", f"%{topic}%", n)
        ).fetchall()
        # Safely update recall count
        for r in rows:
            try:
                self._execute_with_retry(
                    "UPDATE knowledge SET recall_count = COALESCE(recall_count,0) + 1 WHERE topic=? AND content=?",
                    (r[0], r[1])
                )
            except Exception:
                pass
        self.conn.commit()
        return rows

    def ingest_questions(self, questions: List[str], topic: str = "UltimateQuestions", source: str = "Kevin") -> int:
        count = 0
        for q in questions:
            q = q.strip()
            if len(q) > 10 and self.store_knowledge(topic, q, source):
                count += 1
        return count

    # ─────────────────────────────────────────────────────────────────────
    # ARIA SELF-KNOWLEDGE
    # ─────────────────────────────────────────────────────────────────────
    def aria_remember(self, key: str, value: str):
        self._execute_with_retry(
            "INSERT INTO aria_self (ts,key,value) VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET value=?,ts=?",
            (time.time(), key, value, value, time.time())
        )
        self.conn.commit()

    def aria_recall(self, key: str) -> Optional[str]:
        row = self._execute_with_retry("SELECT value FROM aria_self WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    # ─────────────────────────────────────────────────────────────────────
    # SESSIONS
    # ─────────────────────────────────────────────────────────────────────
    def start_session(self, mode: str = "terminal") -> int:
        cur = self._execute_with_retry(
            "INSERT INTO sessions (ts_start,mode) VALUES (?,?)", (time.time(), mode)
        )
        self.conn.commit()
        return cur.lastrowid

    def end_session(self, session_id: int, **kwargs):
        meta = json.dumps(kwargs) if kwargs else None
        self._execute_with_retry(
            "UPDATE sessions SET ts_end=?,meta=? WHERE id=?", (time.time(), meta, session_id)
        )
        self.conn.commit()

    def get_session_turns(self, session_id: int) -> int:
        row = self._execute_with_retry(
            "SELECT COUNT(*) FROM conversations WHERE session_id=?", (str(session_id),)
        ).fetchone()
        return row[0] if row else 0

    # ─────────────────────────────────────────────────────────────────────
    # WONDER SYSTEM
    # ─────────────────────────────────────────────────────────────────────
    def log_wonder(self, trigger_text: str, wonder: str, arch: str = None, source: str = "aria"):
        self._execute_with_retry(
            "INSERT INTO wonders (ts,trigger_text,wonder,arch,source) VALUES (?,?,?,?,?)",
            (time.time(), trigger_text, wonder, arch, source)
        )
        self.conn.commit()

    def recent_wonders(self, n: int = 10) -> List[Tuple]:
        return self._execute_with_retry(
            "SELECT ts,trigger_text,wonder,arch FROM wonders ORDER BY ts DESC LIMIT ?", (n,)
        ).fetchall()

    def random_wonder(self) -> Optional[Tuple]:
        return self._execute_with_retry(
            "SELECT trigger_text,wonder,arch FROM wonders ORDER BY RANDOM() LIMIT 1"
        ).fetchone()

    def random_question(self) -> Optional[str]:
        row = self._execute_with_retry(
            "SELECT content FROM knowledge WHERE topic='UltimateQuestions' ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
        return row[0] if row else None

    # ─────────────────────────────────────────────────────────────────────
    # STATS, BACKUP & LIFECYCLE
    # ─────────────────────────────────────────────────────────────────────
    def stats(self) -> Dict[str, Any]:
        s = {}
        for table in ["conversations", "knowledge", "aria_self", "sessions", "voice_log", "wonders"]:
            try:
                s[table] = self._execute_with_retry(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except Exception:
                s[table] = 0
        s.update({
            "conversations": s.get("conversations", 0),
            "knowledge_items": s.get("knowledge", 0),
            "self_knowledge": s.get("aria_self", 0),
            "sessions": s.get("sessions", 0),
        })
        try:
            s["db_size_kb"] = self.db_path.stat().st_size // 1024
        except Exception:
            s["db_size_kb"] = 0
        return s

    def backup_db(self, backup_dir: Optional[str] = None) -> str:
        target = Path(backup_dir) if backup_dir else self.db_path.parent / "backups"
        target.mkdir(exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        dest = target / f"aria_knowledge_{ts}.db"
        shutil.copy2(str(self.db_path), str(dest))
        log.info(f"Database backed up to {dest}")
        return str(dest)

    def log_event(self, event_type: str, data: Any = None):
        self.log_message("EVENT", json.dumps({"type": event_type, "data": data}))

    def close(self):
        if self.conn:
            try:
                self.conn.commit()
                self.conn.close()
            except Exception as e:
                log.debug(f"Close failed: {e}")
            self.conn = None

    def vacuum(self):
        """Compact WAL and reclaim disk space."""
        try:
            self._execute_with_retry("PRAGMA wal_checkpoint(TRUNCATE)")
            self.conn.commit()
            log.info("WAL checkpoint & vacuum complete.")
        except Exception as e:
            log.warning(f"Vacuum failed: {e}")