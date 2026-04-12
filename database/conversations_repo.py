import datetime
from typing import Dict, List

from .core import _execute_query


async def store_message(
    user_id: int,
    dialog_id: int,
    role: str,
    message_text: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
):
    if role not in ('user', 'bot'):
        return
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    query = """
        INSERT INTO conversations
        (user_id, dialog_id, timestamp, role, message_text, prompt_tokens, completion_tokens, total_tokens)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (user_id, dialog_id, timestamp, role, message_text, prompt_tokens, completion_tokens, total_tokens)
    await _execute_query(query, params, is_write_operation=True)


async def get_conversation_history(dialog_id: int, limit: int = 20) -> List[Dict[str, str]]:
    query = "SELECT role, message_text FROM conversations WHERE dialog_id = ? ORDER BY conversation_id DESC LIMIT ?"
    rows = await _execute_query(query, (dialog_id, limit), fetch_all=True)
    return [dict(row) for row in reversed(rows)] if rows else []


async def get_conversation_history_by_date(dialog_id: int, history_date: datetime.date) -> List[Dict[str, str]]:
    start_dt = datetime.datetime.combine(history_date, datetime.time.min, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime.combine(history_date, datetime.time.max, tzinfo=datetime.timezone.utc)
    query = "SELECT role, message_text FROM conversations WHERE dialog_id = ? AND timestamp BETWEEN ? AND ? ORDER BY timestamp ASC"
    rows = await _execute_query(query, (dialog_id, start_dt.isoformat(), end_dt.isoformat()), fetch_all=True)
    return [dict(row) for row in rows] if rows else []


async def get_total_user_message_count(user_id: int) -> int:
    query = "SELECT COUNT(*) FROM conversations WHERE user_id = ?"
    count = await _execute_query(query, (user_id,))
    return count if count is not None else 0


async def get_token_usage_by_period(user_id: int, period: str) -> Dict[str, int]:
    if period == 'today':
        start_date_str = datetime.date.today().isoformat() + "T00:00:00Z"
    elif period == 'month':
        start_date_str = datetime.date.today().replace(day=1).isoformat() + "T00:00:00Z"
    else:
        return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}

    query = "SELECT SUM(prompt_tokens), SUM(completion_tokens), SUM(total_tokens) FROM conversations WHERE user_id = ? AND timestamp >= ?"
    result_row = await _execute_query(query, (user_id, start_date_str), fetch_one=True)

    if result_row and result_row[0] is not None:
        return {
            'prompt_tokens': int(result_row[0]),
            'completion_tokens': int(result_row[1]),
            'total_tokens': int(result_row[2]),
        }
    return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
