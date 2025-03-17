from typing import Callable, Awaitable, Dict, Any

from aiogram import BaseMiddleware
from aiogram.types import Message

from app.aiogram.common.messages import get_text
from app.db.dao import UserDAO
from app.db.models import User
from app.db.database import async_session_maker

class CheckIsBanned(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session_maker() as session:
            blocked_users = [user.telegram_id for user in await UserDAO.get_blocked_users(session)]
            if event.from_user.id  not in blocked_users:
                return await handler(event, data) 
            else:
                await event.answer(
                    get_text("user_is_banned",lang = event.from_user.language_code)
                )
