from . import core
from .core import (
    _execute_query,
    _execute_sync,
    _get_db_connection,
    db_lock,
    db_logger,
    get_new_user_notifier,
    register_new_user_notifier,
    set_database_name,
)
from .migrations import setup_database, setup_database_sync
from .users_repo import (
    add_or_update_user,
    block_user,
    get_first_interaction_date,
    get_user_api_key,
    get_user_bot_style,
    get_user_gemini_model,
    get_user_language,
    get_user_persona,
    is_user_blocked,
    set_user_api_key,
    set_user_bot_style,
    set_user_gemini_model,
    set_user_language,
    set_user_persona,
    unblock_user,
)
from .dialogs_repo import (
    create_dialog,
    delete_dialog,
    get_active_dialog_id,
    get_user_context_info,
    get_user_dialogs,
    rename_dialog,
    set_active_dialog,
    start_fresh_dialog,
)
from .conversations_repo import (
    get_conversation_history,
    get_conversation_history_by_date,
    get_token_usage_by_period,
    get_total_user_message_count,
    store_message,
)
from .settings_repo import get_app_setting, set_app_setting
from .admin_repo import (
    get_active_users_count,
    get_all_user_ids,
    get_all_users_for_export,
    get_blocked_users_count,
    get_new_users_count,
    get_total_users_count,
    get_user_info_for_admin,
)

__all__ = [
    'DATABASE_NAME',
    'set_database_name',
    'register_new_user_notifier',
    'get_new_user_notifier',
    '_get_db_connection',
    '_execute_sync',
    '_execute_query',
    'db_lock',
    'db_logger',
    'setup_database_sync',
    'setup_database',
    'add_or_update_user',
    'create_dialog',
    'start_fresh_dialog',
    'get_user_dialogs',
    'set_active_dialog',
    'rename_dialog',
    'delete_dialog',
    'get_active_dialog_id',
    'get_user_context_info',
    'store_message',
    'get_conversation_history',
    'get_conversation_history_by_date',
    'get_total_user_message_count',
    'set_user_bot_style',
    'get_user_bot_style',
    'set_user_api_key',
    'get_user_api_key',
    'set_user_language',
    'get_user_language',
    'set_user_gemini_model',
    'get_user_gemini_model',
    'set_user_persona',
    'get_user_persona',
    'get_first_interaction_date',
    'get_token_usage_by_period',
    'set_app_setting',
    'get_app_setting',
    'is_user_blocked',
    'block_user',
    'unblock_user',
    'get_all_user_ids',
    'get_total_users_count',
    'get_blocked_users_count',
    'get_active_users_count',
    'get_new_users_count',
    'get_user_info_for_admin',
    'get_all_users_for_export',
]


def __getattr__(name):
    if name == 'DATABASE_NAME':
        return core.DATABASE_NAME
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
