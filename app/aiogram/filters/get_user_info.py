from aiogram.filters import BaseFilter
from typing import Any, Dict, Optional, Union
from aiogram.types import Message, User
from loguru import logger

from app.aiogram.common.messages import get_text
from app.db.shemas import UserModel
from app.db.dao import UserDAO
from app.db.database import async_session_maker



class GetUserInfoFilter(BaseFilter):
    async def __call__(
        self,
        message: Message,
    ) -> Union[bool, UserModel]:
        async with async_session_maker() as session:
            logger.info(message.from_user.id)
            user_info:Optional[UserModel] = await UserDAO.find_by_telegram_id(session,message.from_user.id)
            if user_info:
                return {'user_info':user_info}
            else:
                await message.answer(get_text("user_is_not_registered",lang = message.from_user.language_code))
                return False