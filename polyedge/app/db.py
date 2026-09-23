from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS scans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  markets_seen INTEGER NOT NULL DEFAULT 0,
  news_seen INTEGER NOT NULL DEFAULT 0,
  signals_created INTEGER NOT NULL DEFAULT 0,
  error TEXT
);
CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  market_id TEXT NOT NULL,
  market_slug TEXT,
  question TEXT NOT NULL,
  market_yes REAL NOT NULL,
  estimated_yes REAL NOT NULL,
  edge REAL NOT NULL,
  side TEXT NOT NULL,
  relevance REAL NOT NULL,
  confidence REAL NOT NULL,
  headline TEXT,
  news_url TEXT,
  rationale TEXT,
  UNIQUE(market_id, news_url, side)
);
CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  signal_id INTEGER NOT NULL,
  market_id TEXT NOT NULL,
  market_slug TEXT,
  side TEXT NOT NULL,
  entry_price REAL NOT NULL,
  amount_usd REAL NOT NULL,
  shares REAL NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPEN',
  pnl REAL NOT NULL DEFAULT 0,
  FOREIGN KEY(signal_id) REFERENCES signals(id)
);
CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at DESC);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        with self._lock, self.connect() as conn:
            cur = conn.execute(sql, params)
            conn.commit()
            return int(cur.lastrowid)

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._lock, self.connect() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def scalar(self, sql: str, params: tuple[Any, ...] = (), default: Any = 0) -> Any:
        rows = self.query(sql, params)
        if not rows:
            return default
        first = rows[0]
        return next(iter(first.values())) if first else default
