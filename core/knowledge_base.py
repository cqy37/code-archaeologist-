import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class KnowledgeBase:
    def __init__(self, db_path: str = ".code_archaeologist.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    language TEXT,
                    lines INTEGER,
                    functions TEXT,
                    classes TEXT,
                    imports TEXT,
                    content_preview TEXT,
                    scanned_at TEXT
                );

                CREATE TABLE IF NOT EXISTS findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT,
                    agent TEXT,
                    category TEXT,
                    finding TEXT,
                    confidence REAL,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS dependency_edges (
                    source TEXT,
                    target TEXT,
                    type TEXT,
                    PRIMARY KEY (source, target)
                );

                CREATE TABLE IF NOT EXISTS refactor_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_file TEXT,
                    plan_json TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    approved_at TEXT
                );
            """)

    def store_file(self, file_info: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO files
                (path, language, lines, functions, classes, imports, content_preview, scanned_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_info["file_path"],
                file_info.get("language", ""),
                file_info.get("lines_of_code", 0),
                json.dumps(file_info.get("functions", [])),
                json.dumps(file_info.get("classes", [])),
                json.dumps(file_info.get("imports", [])),
                file_info.get("content_preview", ""),
                datetime.now().isoformat(),
            ))

    def store_finding(self, file_path: str, agent: str, category: str,
                     finding: str, confidence: float = 0.9):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO findings (file_path, agent, category, finding, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (file_path, agent, category, finding, confidence, datetime.now().isoformat()))

    def store_edge(self, source: str, target: str, edge_type: str = "import"):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO dependency_edges (source, target, type)
                VALUES (?, ?, ?)
            """, (source, target, edge_type))

    def store_plan(self, target_file: str, plan: Dict[str, Any]) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO refactor_plans (target_file, plan_json, status, created_at)
                VALUES (?, ?, 'pending', ?)
            """, (target_file, json.dumps(plan, ensure_ascii=False), datetime.now().isoformat()))
            return cursor.lastrowid

    def get_findings(self, file_path: Optional[str] = None,
                    agent: Optional[str] = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM findings WHERE 1=1"
            params = []
            if file_path:
                query += " AND file_path = ?"
                params.append(file_path)
            if agent:
                query += " AND agent = ?"
                params.append(agent)
            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_file(self, path: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM files WHERE path = ?", (path,)).fetchone()
            if row:
                d = dict(row)
                d["functions"] = json.loads(d["functions"])
                d["classes"] = json.loads(d["classes"])
                d["imports"] = json.loads(d["imports"])
                d["lines_of_code"] = d.pop("lines", 0)
                return d
            return None

    def get_all_files(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM files").fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["functions"] = json.loads(d["functions"])
                d["classes"] = json.loads(d["classes"])
                d["imports"] = json.loads(d["imports"])
                d["lines_of_code"] = d.pop("lines", 0)
                result.append(d)
            return result

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                DELETE FROM files;
                DELETE FROM findings;
                DELETE FROM dependency_edges;
                DELETE FROM refactor_plans;
            """)
