import os
import sqlite3
from typing import Dict, List

import pandas as pd


class PlanningService:
    """Persist targets and campaign plans for the portal."""

    def __init__(self, db_path: str = "data/planning.db"):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS targets (
                    fy TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    target_value REAL NOT NULL,
                    owner TEXT,
                    notes TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (fy, metric)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    focus_metric TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    goal_value REAL DEFAULT 0,
                    owner TEXT,
                    status TEXT DEFAULT 'Planned',
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def upsert_targets(self, targets: List[Dict]):
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO targets (fy, metric, target_value, owner, notes, updated_at)
                VALUES (:fy, :metric, :target_value, :owner, :notes, CURRENT_TIMESTAMP)
                ON CONFLICT(fy, metric) DO UPDATE SET
                    target_value = excluded.target_value,
                    owner = excluded.owner,
                    notes = excluded.notes,
                    updated_at = CURRENT_TIMESTAMP
                """,
                targets,
            )
            conn.commit()

    def list_targets(self, fy: str | None = None) -> pd.DataFrame:
        query = "SELECT fy, metric, target_value, owner, notes, updated_at FROM targets"
        params = []
        if fy:
            query += " WHERE fy = ?"
            params.append(fy)
        query += " ORDER BY fy DESC, metric"
        with self._connect() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def replace_targets_from_frame(self, frame: pd.DataFrame, fy: str, owner: str = "") -> int:
        if frame.empty:
            return 0
        normalized = frame.copy()
        normalized.columns = [str(c).strip().lower() for c in normalized.columns]
        metric_col = "metric" if "metric" in normalized.columns else None
        value_col = "target_value" if "target_value" in normalized.columns else None
        if value_col is None:
            for candidate in ["target", "value", "fy_target", "annual_target"]:
                if candidate in normalized.columns:
                    value_col = candidate
                    break
        if metric_col is None or value_col is None:
            raise ValueError("Target file must include 'metric' and 'target_value' or equivalent columns.")

        rows = []
        for _, row in normalized.iterrows():
            metric = str(row.get(metric_col, "")).strip()
            if not metric:
                continue
            rows.append(
                {
                    "fy": fy,
                    "metric": metric,
                    "target_value": float(row.get(value_col, 0) or 0),
                    "owner": owner,
                    "notes": str(row.get("notes", "") or ""),
                }
            )
        self.upsert_targets(rows)
        return len(rows)

    def create_campaign(
        self,
        title: str,
        focus_metric: str,
        start_date: str,
        end_date: str,
        goal_value: float,
        owner: str,
        status: str,
        notes: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO campaigns (title, focus_metric, start_date, end_date, goal_value, owner, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (title, focus_metric, start_date, end_date, goal_value, owner, status, notes),
            )
            conn.commit()

    def list_campaigns(self) -> pd.DataFrame:
        with self._connect() as conn:
            return pd.read_sql_query(
                """
                SELECT id, title, focus_metric, start_date, end_date, goal_value, owner, status, notes, created_at
                FROM campaigns
                ORDER BY
                    CASE status
                        WHEN 'Active' THEN 1
                        WHEN 'Planned' THEN 2
                        WHEN 'Completed' THEN 3
                        ELSE 4
                    END,
                    start_date
                """,
                conn,
            )
