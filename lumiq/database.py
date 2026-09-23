from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY, strategy_id TEXT NOT NULL, strategy_path TEXT NOT NULL,
                mode TEXT NOT NULL, broker TEXT NOT NULL, parameters TEXT NOT NULL,
                status TEXT NOT NULL, pid INTEGER, created_at TEXT NOT NULL, started_at TEXT,
                stopped_at TEXT, heartbeat_at TEXT, exit_code INTEGER, error TEXT,
                stdout_path TEXT NOT NULL, stderr_path TEXT NOT NULL
            )""")

    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def create(self, **values: Any) -> None:
        values.setdefault("created_at", utc_now())
        columns = ",".join(values)
        placeholders = ",".join("?" for _ in values)
        with self.connect() as db:
            db.execute(f"INSERT INTO runs ({columns}) VALUES ({placeholders})", tuple(values.values()))

    def update(self, run_id: str, **values: Any) -> None:
        if not values:
            return
        values.setdefault("heartbeat_at", utc_now())
        clause = ",".join(f"{key}=?" for key in values)
        with self.connect() as db:
            db.execute(f"UPDATE runs SET {clause} WHERE run_id=?", (*values.values(), run_id))

    def get(self, run_id: str):
        with self.connect() as db:
            return db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()

    def all(self):
        with self.connect() as db:
            return db.execute("SELECT * FROM runs ORDER BY created_at DESC").fetchall()

    @staticmethod
    def public(row):
        if row is None:
            return None
        result = dict(row)
        result["parameters"] = json.loads(result["parameters"])
        return result
