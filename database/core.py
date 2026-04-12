import asyncio
import sqlite3
from typing import Any, Optional

from config.settings import DATABASE_NAME as CONFIG_DATABASE_NAME
from logger_config import get_logger


db_logger = get_logger('database', user_id='System')
db_lock = asyncio.Lock()
DATABASE_NAME = CONFIG_DATABASE_NAME
_new_user_notifier = None


def set_database_name(path: str):
    global DATABASE_NAME
    DATABASE_NAME = path


def register_new_user_notifier(notifier):
    global _new_user_notifier
    _new_user_notifier = notifier


def get_new_user_notifier():
    return _new_user_notifier


def _get_db_connection() -> sqlite3.Connection:
    try:
        conn = sqlite3.connect(
            DATABASE_NAME,
            check_same_thread=False,
            timeout=10.0,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn
    except sqlite3.Error as e:
        db_logger.exception(f"Ошибка подключения к базе данных {DATABASE_NAME}: {e}")
        raise


def _execute_sync(
    query: str,
    params: tuple = (),
    fetch_one: bool = False,
    fetch_all: bool = False,
    is_write_operation: bool = False,
) -> Optional[Any]:
    conn = None
    result = None
    try:
        conn = _get_db_connection()
        if is_write_operation:
            conn.isolation_level = 'IMMEDIATE'
            conn.execute('BEGIN IMMEDIATE')

        cursor = conn.cursor()
        cursor.execute(query, params)

        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        elif "count(" in query.lower() or "sum(" in query.lower():
            count_result = cursor.fetchone()
            result = count_result[0] if count_result and count_result[0] is not None else 0

        if is_write_operation:
            if query.strip().upper().startswith("INSERT"):
                result = cursor.lastrowid
            elif query.strip().upper().startswith(("UPDATE", "DELETE")):
                result = cursor.rowcount
            conn.commit()

    except sqlite3.Error as e:
        db_logger.exception(f"Ошибка выполнения SQL: {query} | Params: {params} | Error: {e}")
        if conn and is_write_operation:
            try:
                conn.rollback()
            except sqlite3.Error as rb_err:
                db_logger.error(f"Ошибка при откате транзакции: {rb_err}")
        if fetch_all:
            return []
        raise e
    finally:
        if conn:
            conn.close()
    return result


async def _execute_query(
    query: str,
    params: tuple = (),
    fetch_one: bool = False,
    fetch_all: bool = False,
    is_write_operation: bool = False,
) -> Optional[Any]:
    try:
        if is_write_operation:
            async with db_lock:
                return await asyncio.to_thread(
                    _execute_sync, query, params, fetch_one, fetch_all, is_write_operation
                )
        return await asyncio.to_thread(
            _execute_sync, query, params, fetch_one, fetch_all, is_write_operation
        )
    except Exception as e:
        db_logger.error(f"Перехвачена ошибка из _execute_sync в _execute_query: {e}")
        if fetch_all:
            return []
        return None
