from contextlib import asynccontextmanager

from telebot import types
from telebot.async_telebot import AsyncTeleBot

from database import db_manager


async def ensure_user_context(message_or_call: types.Message | types.CallbackQuery) -> tuple[int, str]:
    """Synchronize user profile and return (user_id, lang_code).

    This is the common entrypoint bootstrap for Telegram handlers.
    It keeps the repetitive "upsert user + load language" flow in one place.
    """
    user = message_or_call.from_user
    user_id = user.id
    await db_manager.add_or_update_user(user.id, user.username, user.first_name, user.last_name)
    lang_code = await db_manager.get_user_language(user_id)
    return user_id, lang_code


def resolve_chat_id(message_or_call: types.Message | types.CallbackQuery) -> int:
    """Return the effective chat id for a Telegram message or callback."""
    if isinstance(message_or_call, types.CallbackQuery):
        if message_or_call.message:
            return message_or_call.message.chat.id
        return message_or_call.from_user.id
    return message_or_call.chat.id


def resolve_state_scope(message_or_call: types.Message | types.CallbackQuery) -> tuple[int, int]:
    """Return the (user_id, chat_id) tuple used by the bot FSM API."""
    user_id = message_or_call.from_user.id
    return user_id, resolve_chat_id(message_or_call)


async def set_state(bot: AsyncTeleBot, message_or_call: types.Message | types.CallbackQuery, state: str) -> None:
    user_id, chat_id = resolve_state_scope(message_or_call)
    await bot.set_state(user_id, state, chat_id)


async def get_state(bot: AsyncTeleBot, message_or_call: types.Message | types.CallbackQuery):
    user_id, chat_id = resolve_state_scope(message_or_call)
    return await bot.get_state(user_id, chat_id)


async def delete_state(bot: AsyncTeleBot, message_or_call: types.Message | types.CallbackQuery) -> None:
    user_id, chat_id = resolve_state_scope(message_or_call)
    await bot.delete_state(user_id, chat_id)


async def add_state_data(bot: AsyncTeleBot, message_or_call: types.Message | types.CallbackQuery, **data) -> None:
    user_id, chat_id = resolve_state_scope(message_or_call)
    await bot.add_data(user_id, chat_id, **data)


@asynccontextmanager
async def retrieve_state_data(bot: AsyncTeleBot, message_or_call: types.Message | types.CallbackQuery):
    user_id, chat_id = resolve_state_scope(message_or_call)
    async with bot.retrieve_data(user_id, chat_id) as data:
        yield data
