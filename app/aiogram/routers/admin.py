from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandObject, Command
from loguru import logger

from app.aiogram.common.messages import get_text
from app.aiogram.filters.get_user_info import GetUserInfoFilter
from app.aiogram.keyboards.markup_kb import MainKeyboard
from app.db.dao import UserDAO, PromocodeDAO
from app.db.database import connection
from app.db.models import User
from app.db.shemas import TelegramIDModel, PromocodeFilter
from app.config import bot

admin_router = Router()


@admin_router.message(Command("send_promo"), GetUserInfoFilter())
@connection()
async def cmd_send_promo(
    message: Message, command: CommandObject, user_info: User, session, **kwargs
):
    try:
        if command.args is None:
            await message.answer(
                get_text("error_no_arguments_passed", lang=user_info.language_code)
            )
            return

        try:
            user_id, promo_name = command.args.split(" ", maxsplit=1)
        except ValueError:
            await message.answer(
                get_text("error_wrong_promo_args", lang=user_info.language_code)
            )
            return

        user = await UserDAO.find_one_or_none(
            session, TelegramIDModel(telegram_id=user_id)
        )
        if not user:
            await message.answer(
                get_text("error_user_not_found", lang=user_info.language_code)
            )
            return
        promo = await PromocodeDAO.find_one_or_none(
            session, PromocodeFilter(promo_name=promo_name)
        )
        if not promo:
            await message.answer(
                get_text("error_promo_not_found", lang=user_info.language_code)
            )
            return
        await bot.send_message(
            user.telegram_id,
            get_text(
                "promo_message",
                lang=user.language_code,
                promo_code=promo.promo_name,
                activate_button=MainKeyboard.get_user_kb_texts(user.language_code).get(
                    "activate_promo"
                ),
            ),
        )
    except Exception as e:
        logger.error(
            f"При отсылке промокода произошла командой /send_promo произошла ошибка: {str(e)}"
        )
        await message.answer(get_text("error_occurred", lang=user_info.language_code))
