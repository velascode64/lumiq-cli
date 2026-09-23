from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
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
            db.execute("""CREATE TABLE IF NOT EXISTS strategy_parameters (
                strategy_id TEXT PRIMARY KEY, parameters TEXT NOT NULL, updated_at TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS parameter_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, strategy_id TEXT NOT NULL, timestamp TEXT NOT NULL,
                parameter TEXT NOT NULL, previous_value TEXT, new_value TEXT NOT NULL, source TEXT NOT NULL
            )""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        finally:
            db.close()

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

    def parameters_for(self, strategy_id: str, defaults: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT parameters FROM strategy_parameters WHERE strategy_id=?", (strategy_id,)
            ).fetchone()
        return {**defaults, **(json.loads(row["parameters"]) if row else {})}

    def save_parameters(self, strategy_id: str, parameters: dict[str, Any], source: str) -> None:
        existing = self.parameters_for(strategy_id, {})
        timestamp = utc_now()
        with self.connect() as db:
            db.execute(
                """INSERT INTO strategy_parameters (strategy_id, parameters, updated_at) VALUES (?, ?, ?)
                   ON CONFLICT(strategy_id) DO UPDATE SET parameters=excluded.parameters, updated_at=excluded.updated_at""",
                (strategy_id, json.dumps(parameters, sort_keys=True), timestamp),
            )
            for key, value in parameters.items():
                if existing.get(key) == value:
                    continue
                db.execute(
                    """INSERT INTO parameter_history
                       (strategy_id, timestamp, parameter, previous_value, new_value, source)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        strategy_id,
                        timestamp,
                        key,
                        json.dumps(existing.get(key)),
                        json.dumps(value),
                        source,
                    ),
                )

    def parameter_history(self, strategy_id: str):
        with self.connect() as db:
            return db.execute(
                """SELECT timestamp, parameter, previous_value, new_value, source
                   FROM parameter_history WHERE strategy_id=? ORDER BY id DESC""",
                (strategy_id,),
            ).fetchall()

    @staticmethod
    def public(row):
        if row is None:
            return None
        result = dict(row)
        result["parameters"] = json.loads(result["parameters"])
        return result