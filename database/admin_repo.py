import datetime
from typing import Any, Dict, List, Optional

from .core import _execute_query


async def get_all_user_ids() -> List[int]:
    rows = await _execute_query("SELECT user_id FROM users", fetch_all=True)
    return [row['user_id'] for row in rows] if rows else []


async def get_total_users_count() -> int:
    count = await _execute_query("SELECT COUNT(*) FROM users")
    return count if count is not None else 0


async def get_blocked_users_count() -> int:
    count = await _execute_query("SELECT COUNT(*) FROM users WHERE is_blocked = 1")
    return count if count is not None else 0


async def get_active_users_count(days: int = 7) -> int:
    start_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    query = "SELECT COUNT(DISTINCT user_id) FROM conversations WHERE timestamp >= ?"
    count = await _execute_query(query, (start_date.isoformat(),))
    return count if count is not None else 0


async def get_new_users_count(days: int = 7) -> int:
    start_date = datetime.date.today() - datetime.timedelta(days=days)
    query = "SELECT COUNT(*) FROM users WHERE first_interaction_date >= ?"
    count = await _execute_query(query, (start_date.strftime('%Y-%m-%d'),))
    return count if count is not None else 0


async def get_user_info_for_admin(user_id: int) -> Optional[Dict[str, Any]]:
    query = """
        SELECT
            u.user_id,
            u.username,
            u.first_name,
            u.last_name,
            u.language_code,
            u.first_interaction_date,
            u.is_blocked,
            (SELECT COUNT(*) FROM conversations WHERE user_id = u.user_id) as message_count
        FROM users u
        WHERE u.user_id = ?
    """
    row = await _execute_query(query, (user_id,), fetch_one=True)
    if row:
        return dict(row)
    return None


async def get_all_users_for_export() -> List[Dict[str, Any]]:
    query = """
        SELECT
            user_id,
            username,
            first_name,
            last_name,
            language_code,
            first_interaction_date,
            is_blocked
        FROM users
        ORDER BY user_id ASC
    """
    rows = await _execute_query(query, fetch_all=True)
    return [dict(row) for row in rows] if rows else []
