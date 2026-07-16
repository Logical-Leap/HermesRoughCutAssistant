from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 2
TABLES = {
    "project": "id TEXT PRIMARY KEY, name TEXT NOT NULL, path TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL",
    "media_asset": "id TEXT PRIMARY KEY, project_id TEXT NOT NULL, checksum TEXT NOT NULL, source_path TEXT NOT NULL, payload TEXT NOT NULL, mtime_ns INTEGER, size INTEGER",
    "transcript_word": "id TEXT PRIMARY KEY, project_id TEXT NOT NULL, media_asset_id TEXT NOT NULL, start REAL NOT NULL, end REAL NOT NULL, payload TEXT NOT NULL",
    "transcript_sentence": "id TEXT PRIMARY KEY, project_id TEXT NOT NULL, media_asset_id TEXT NOT NULL, start REAL NOT NULL, end REAL NOT NULL, payload TEXT NOT NULL",
    "scene": "id TEXT PRIMARY KEY, project_id TEXT NOT NULL, media_asset_id TEXT NOT NULL, start REAL NOT NULL, end REAL NOT NULL, payload TEXT NOT NULL",
    "audio_region": "id TEXT PRIMARY KEY, project_id TEXT NOT NULL, media_asset_id TEXT NOT NULL, start REAL NOT NULL, end REAL NOT NULL, payload TEXT NOT NULL",
    "retake_group": "id TEXT PRIMARY KEY, project_id TEXT NOT NULL, payload TEXT NOT NULL",
    "editorial_unit": "id TEXT PRIMARY KEY, project_id TEXT NOT NULL, media_asset_id TEXT NOT NULL, start REAL NOT NULL, end REAL NOT NULL, payload TEXT NOT NULL",
    "edit_decision": "id TEXT PRIMARY KEY, project_id TEXT NOT NULL, timeline_id TEXT NOT NULL, payload TEXT NOT NULL",
    "timeline_version": "id TEXT PRIMARY KEY, project_id TEXT NOT NULL, mode TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL",
    "approval": "id TEXT PRIMARY KEY, project_id TEXT NOT NULL, timeline_id TEXT NOT NULL, decision_id TEXT NOT NULL, action TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', payload TEXT NOT NULL",
    "model_cache": "cache_key TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL",
    "benchmark": "id TEXT PRIMARY KEY, project_id TEXT NOT NULL, payload TEXT NOT NULL",
}

class ProjectStore:
    def __init__(self, project: str | Path):
        self.project = Path(project).expanduser().resolve()
        self.path = self.project / ".hermes" / "project.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.migrate()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def migrate(self) -> None:
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS schema_info(version INTEGER NOT NULL)")
            if not db.execute("SELECT 1 FROM schema_info").fetchone():
                db.execute("INSERT INTO schema_info VALUES (?)", (SCHEMA_VERSION,))
            else:
                db.execute("UPDATE schema_info SET version=?", (SCHEMA_VERSION,))
            for name, columns in TABLES.items():
                db.execute(f"CREATE TABLE IF NOT EXISTS {name}({columns})")
            db.execute("CREATE INDEX IF NOT EXISTS media_checksum_idx ON media_asset(checksum)")
            db.execute("CREATE INDEX IF NOT EXISTS sentence_asset_idx ON transcript_sentence(media_asset_id,start)")

    def upsert(self, table: str, row: dict[str, Any]) -> None:
        if table not in TABLES:
            raise ValueError(f"Unknown table: {table}")
        keys = list(row)
        sql = f"INSERT INTO {table} ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)}) ON CONFLICT({keys[0]}) DO UPDATE SET " + ",".join(f"{k}=excluded.{k}" for k in keys[1:])
        values = [json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for v in row.values()]
        with self.connect() as db:
            db.execute(sql, values)

    def replace_project_rows(self, table: str, project_id: str, rows: Iterable[dict[str, Any]]) -> None:
        with self.connect() as db:
            db.execute(f"DELETE FROM {table} WHERE project_id=?", (project_id,))
        for row in rows:
            self.upsert(table, row)

    def rows(self, table: str, where: str = "", params: tuple = ()) -> list[dict[str, Any]]:
        if table not in TABLES:
            raise ValueError(f"Unknown table: {table}")
        with self.connect() as db:
            result = db.execute(f"SELECT * FROM {table}" + (f" WHERE {where}" if where else ""), params).fetchall()
        output = []
        for row in result:
            item = dict(row)
            if "payload" in item:
                item["payload"] = json.loads(item["payload"])
            output.append(item)
        return output

    def cached_asset(self, source_path: Path) -> dict[str, Any] | None:
        stat = source_path.stat()
        rows = self.rows("media_asset", "source_path=? AND mtime_ns=? AND size=?", (str(source_path.resolve()), stat.st_mtime_ns, stat.st_size))
        return rows[0]["payload"] if rows else None
