"""Persistent single-host device registry and telemetry replay state."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Protocol


class ConstructionIoTReplayState(Protocol):
    def register_device(self, *, device_id: str, credential_ref: str) -> None: ...

    def credential_ref(self, *, device_id: str) -> str | None: ...

    def peek_freshness(self, *, device_id: str, counter: int, nonce: str) -> tuple[bool, bool]: ...

    def commit_if_fresh(
        self,
        *,
        device_id: str,
        counter: int,
        nonce: str,
    ) -> tuple[bool, bool, bool]: ...


class SQLiteConstructionIoTReplayState:
    """SQLite-backed replay state for one service instance or shared host volume."""

    capability_boundary = (
        "SQLite 单主机持久化：设备凭据仅保存引用，不保存密钥；"
        "支持进程重启后的防重放，但不等于跨地域分布式一致性。"
    )

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS construction_iot_devices (
                    device_id TEXT PRIMARY KEY,
                    credential_ref TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS construction_iot_counters (
                    device_id TEXT PRIMARY KEY,
                    last_counter INTEGER NOT NULL,
                    FOREIGN KEY(device_id) REFERENCES construction_iot_devices(device_id)
                );
                CREATE TABLE IF NOT EXISTS construction_iot_nonces (
                    device_id TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    PRIMARY KEY(device_id, nonce),
                    FOREIGN KEY(device_id) REFERENCES construction_iot_devices(device_id)
                );
                """
            )
            connection.commit()

    def register_device(self, *, device_id: str, credential_ref: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO construction_iot_devices(device_id, credential_ref, active)
                VALUES (?, ?, 1)
                ON CONFLICT(device_id) DO UPDATE SET
                    credential_ref = excluded.credential_ref,
                    active = 1
                """,
                (device_id, credential_ref),
            )
            connection.execute(
                """
                INSERT INTO construction_iot_counters(device_id, last_counter)
                VALUES (?, -1)
                ON CONFLICT(device_id) DO NOTHING
                """,
                (device_id,),
            )
            connection.commit()

    def credential_ref(self, *, device_id: str) -> str | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT credential_ref
                FROM construction_iot_devices
                WHERE device_id = ? AND active = 1
                """,
                (device_id,),
            ).fetchone()
        return str(row[0]) if row else None

    def peek_freshness(self, *, device_id: str, counter: int, nonce: str) -> tuple[bool, bool]:
        with closing(self._connect()) as connection:
            counter_row = connection.execute(
                "SELECT last_counter FROM construction_iot_counters WHERE device_id = ?",
                (device_id,),
            ).fetchone()
            nonce_row = connection.execute(
                "SELECT 1 FROM construction_iot_nonces WHERE device_id = ? AND nonce = ?",
                (device_id, nonce),
            ).fetchone()
        last_counter = int(counter_row[0]) if counter_row else -1
        return counter > last_counter, bool(nonce) and nonce_row is None

    def commit_if_fresh(
        self,
        *,
        device_id: str,
        counter: int,
        nonce: str,
    ) -> tuple[bool, bool, bool]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            counter_row = connection.execute(
                "SELECT last_counter FROM construction_iot_counters WHERE device_id = ?",
                (device_id,),
            ).fetchone()
            nonce_row = connection.execute(
                "SELECT 1 FROM construction_iot_nonces WHERE device_id = ? AND nonce = ?",
                (device_id, nonce),
            ).fetchone()
            last_counter = int(counter_row[0]) if counter_row else -1
            counter_valid = counter > last_counter
            nonce_valid = bool(nonce) and nonce_row is None
            accepted = counter_valid and nonce_valid
            if accepted:
                connection.execute(
                    "UPDATE construction_iot_counters SET last_counter = ? WHERE device_id = ?",
                    (counter, device_id),
                )
                connection.execute(
                    "INSERT INTO construction_iot_nonces(device_id, nonce) VALUES (?, ?)",
                    (device_id, nonce),
                )
            connection.commit()
            return counter_valid, nonce_valid, accepted
        except sqlite3.Error:
            connection.rollback()
            raise
        finally:
            connection.close()
