import asyncio
import datetime

from config.settings import DEFAULT_LLM_BACKEND
from logger_config import get_logger
from .core import _get_db_connection


db_logger = get_logger('database', user_id='System')


def setup_database_sync():
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        db_logger.info("Таблица 'app_settings' проверена/создана.")

        cursor.execute("PRAGMA table_info(users)")
        user_columns = {col['name'] for col in cursor.fetchall()}
        if not user_columns:
            db_logger.info("Таблица 'users' не найдена, создаем...")
            cursor.execute(
                f"""
                CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    bot_style TEXT DEFAULT 'default' NOT NULL,
                    first_interaction_date TEXT,
                    api_key TEXT DEFAULT NULL,
                    language_code TEXT DEFAULT 'ru' NOT NULL,
                    gemini_model TEXT DEFAULT NULL,
                    llm_backend TEXT DEFAULT '{DEFAULT_LLM_BACKEND}' NOT NULL,
                    openai_api_key TEXT DEFAULT NULL,
                    openai_model TEXT DEFAULT NULL,
                    active_persona TEXT DEFAULT 'default' NOT NULL,
                    active_dialog_id INTEGER REFERENCES dialogs(dialog_id) ON DELETE SET NULL,
                    is_blocked INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        else:
            required_user_columns = {
                'active_dialog_id', 'active_persona', 'is_blocked',
                'username', 'first_name', 'last_name',
                'llm_backend', 'openai_api_key', 'openai_model'
            }
            missing_user_columns = required_user_columns - user_columns
            for col in missing_user_columns:
                db_logger.info(f"Добавляем отсутствующий столбец '{col}' в 'users'...")
                if col == 'active_persona':
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT 'default' NOT NULL")
                elif col == 'is_blocked':
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0")
                elif col == 'llm_backend':
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT '{DEFAULT_LLM_BACKEND}' NOT NULL")
                elif col in ['username', 'first_name', 'last_name', 'openai_api_key', 'openai_model']:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
                else:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER REFERENCES dialogs(dialog_id) ON DELETE SET NULL")

        cursor.execute("PRAGMA table_info(dialogs)")
        if not cursor.fetchall():
            db_logger.info("Таблица 'dialogs' не найдена, создаем...")
            cursor.execute(
                """
                CREATE TABLE dialogs (
                    dialog_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dialogs_user ON dialogs (user_id)")

        cursor.execute("PRAGMA table_info(conversations)")
        conversation_columns = {col['name'] for col in cursor.fetchall()}
        if not conversation_columns:
            db_logger.info("Таблица 'conversations' не найдена, создаем...")
            cursor.execute(
                """
                CREATE TABLE conversations (
                    conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'bot')),
                    message_text TEXT,
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    dialog_id INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (dialog_id) REFERENCES dialogs(dialog_id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_dialog_time ON conversations (dialog_id, timestamp)")
        elif 'dialog_id' not in conversation_columns:
            db_logger.info("Добавляем отсутствующий столбец 'dialog_id' в 'conversations'...")
            cursor.execute("ALTER TABLE conversations ADD COLUMN dialog_id INTEGER REFERENCES dialogs(dialog_id) ON DELETE CASCADE")

        conn.commit()

        cursor.execute("SELECT user_id FROM users WHERE active_dialog_id IS NULL")
        users_to_migrate = cursor.fetchall()
        if users_to_migrate:
            db_logger.info(f"Найдено {len(users_to_migrate)} пользователей для миграции на систему диалогов...")
            for row in users_to_migrate:
                user_id = row['user_id']
                default_dialog_name = "Основной диалог"
                now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                cursor.execute(
                    "INSERT INTO dialogs (user_id, name, created_at) VALUES (?, ?, ?)",
                    (user_id, default_dialog_name, now_str),
                )
                new_dialog_id = cursor.lastrowid
                cursor.execute("UPDATE users SET active_dialog_id = ? WHERE user_id = ?", (new_dialog_id, user_id))
                cursor.execute(
                    "UPDATE conversations SET dialog_id = ? WHERE user_id = ? AND dialog_id IS NULL",
                    (new_dialog_id, user_id),
                )
                db_logger.info(f"Пользователь {user_id} успешно мигрирован. Создан диалог ID: {new_dialog_id}.")
            conn.commit()

            db_logger.info("Пересоздание таблицы 'conversations', чтобы сделать столбец 'dialog_id' NOT NULL...")
            cursor.execute("PRAGMA foreign_keys=off")
            cursor.execute("BEGIN TRANSACTION")
            cursor.execute(
                """
                CREATE TABLE conversations_new (
                    conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'bot')),
                    message_text TEXT,
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    dialog_id INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (dialog_id) REFERENCES dialogs(dialog_id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute("INSERT INTO conversations_new SELECT * FROM conversations WHERE dialog_id IS NOT NULL")
            cursor.execute("DROP TABLE conversations")
            cursor.execute("ALTER TABLE conversations_new RENAME TO conversations")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_dialog_time ON conversations (dialog_id, timestamp)")
            cursor.execute("COMMIT")
            cursor.execute("PRAGMA foreign_keys=on")
            db_logger.info("Столбец 'dialog_id' в таблице 'conversations' успешно обновлен.")

        db_logger.info("Проверка и настройка базы данных завершена.")
    except Exception as e:
        db_logger.exception(f"Критическая ошибка при настройке/миграции базы данных: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


async def setup_database():
    await asyncio.to_thread(setup_database_sync)
