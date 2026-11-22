"""Audit trail. PostgreSQL when it is reachable, otherwise memory."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("infragpt-audit")


class AuditStore:
    def __init__(self) -> None:
        self._memory: list[dict[str, Any]] = []
        self._conn = None
        self.backend = "memory"
        self.last_error: str | None = None
        self._connect()

    def _connect(self) -> None:
        try:
            import psycopg
        except ImportError:
            self.last_error = "psycopg is not installed"
            return

        try:
            self._conn = psycopg.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                dbname=os.getenv("POSTGRES_DB", "infragpt_audit"),
                user=os.getenv("POSTGRES_USER", "infragpt"),
                password=os.getenv("POSTGRES_PASSWORD", "infragpt_secret"),
                connect_timeout=2,
                autocommit=True,
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT,
                    user_name TEXT,
                    status TEXT,
                    details JSONB NOT NULL DEFAULT '{}'::jsonb,
                    session_id TEXT
                )
                """
            )
            self.backend = "postgres"
            self.last_error = None
            logger.info("Audit log connected to PostgreSQL.")
        except Exception as exc:
            self._conn = None
            self.backend = "memory"
            self.last_error = str(exc).splitlines()[-1][:240]
            logger.info("PostgreSQL audit log is offline (%s). Using memory.", self.last_error)

    def add(self, event: dict[str, Any]) -> None:
        self._memory.insert(0, event)
        del self._memory[200:]
        if self._conn is None:
            return
        try:
            self._conn.execute(
                """
                INSERT INTO audit_events
                    (id, timestamp, action, target, user_name, status, details, session_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    event["id"],
                    event["timestamp"],
                    event["action"],
                    event.get("target"),
                    event.get("user"),
                    event.get("status"),
                    json.dumps(event.get("details") or {}, default=str),
                    event.get("session_id"),
                ),
            )
        except Exception as exc:
            self.last_error = str(exc).splitlines()[-1][:240]
            logger.warning("Failed to persist audit event: %s", self.last_error)

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        if self._conn is not None:
            try:
                rows = self._conn.execute(
                    """
                    SELECT id, timestamp, action, target, user_name, status, details, session_id
                    FROM audit_events
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    (limit,),
                ).fetchall()
                events = []
                for row in rows:
                    timestamp = row[1].isoformat() if hasattr(row[1], "isoformat") else str(row[1])
                    details = row[6] if isinstance(row[6], dict) else json.loads(row[6] or "{}")
                    events.append(
                        {
                            "id": row[0],
                            "timestamp": timestamp,
                            "action": row[2],
                            "target": row[3],
                            "user": row[4],
                            "status": row[5],
                            "details": details,
                            "session_id": row[7],
                        }
                    )
                return events
            except Exception as exc:
                self.last_error = str(exc).splitlines()[-1][:240]
                logger.warning("Failed to read audit events: %s", self.last_error)
        return self._memory[:limit]
