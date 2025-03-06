from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandObject, Command
from loguru import logger

from app.aiogram.keyboards.markup_kb import MainKeyboard
from app.db.dao import UserDAO, PromocodeDAO
from app.db.database import connection
from app.db.shemas import TelegramIDModel, PromocodeFilter
from app.config import bot

admin_router = Router()


@admin_router.message(Command("send_promo"))
@connection()
async def cmd_send_promo(message: Message, command: CommandObject, session, **kwargs):
    try:
        if command.args is None:
            await message.answer("Ошибка: не переданы аргументы")
            return

        try:
            user_id, promo_name = command.args.split(" ", maxsplit=1)
        except ValueError:
            await message.answer(
                "Ошибка: неправильный формат команды. Пример:\n"
                "/send_promo <id> <promo>"
            )
            return

        user = await UserDAO.find_one_or_none(session, TelegramIDModel(telegram_id=user_id))
        if not user:
            await message.answer("Ошибка: не найден юзер")
            return
        promo = await PromocodeDAO.find_one_or_none(
            session, PromocodeFilter(promo_name=promo_name)
        )
        if not promo:
            await message.answer("Ошибка: не найден промокод")
            return
        await bot.send_message(
            user.telegram_id,
            f"Ваш промокод: <code>{promo.promo_name}</code> \nДля активации подписки нажмите кнопку \'{MainKeyboard.get_user_kb_texts().get('activate_promo')}\'"
        )
    except Exception as e:
        logger.error(f'При отсылке промокода произошла командой /send_promo произошла ошибка: {str(e)}')
        await message.answer('Что-то пошло не так')