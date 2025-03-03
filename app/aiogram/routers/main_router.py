from aiogram import Router,F
from aiogram.types import Message
from aiogram.filters import CommandStart
from loguru import logger
from app.aiogram.common.messages import start_message
from app.aiogram.keyboards.markup_kb import MainKeyboard
from app.aiogram.middlewarres.is_admin import CheckIsAdmin
from app.aiogram.middlewarres.is_banned import CheckIsBanned
from app.db.dao import UserDAO
from app.db.database import connection
from app.db.models import User
from app.db.shemas import TelegramIDModel, UserModel
from app.aiogram.routers.user_router import user_router
from app.aiogram.routers.receiving_messages import receiving_message_router
from app.aiogram.routers.admin import admin_router
from app.config import admins,bot

user_router.message.middleware(CheckIsBanned())
receiving_message_router.message.middleware(CheckIsAdmin())
admin_router.message.middleware(CheckIsAdmin())

main_router = Router()
main_router.include_router(user_router)
main_router.include_router(receiving_message_router)
main_router.include_router(admin_router)

@main_router.message(CommandStart())
@connection()
async def cmd_start(message: Message, session, **kwargs):
    try:
        user_id = message.from_user.id
        user_info = await UserDAO.find_one_or_none(
            session=session, filters=TelegramIDModel(telegram_id=user_id)
        )
        if user_info:
            msg = start_message("Приветик")
            await message.answer(msg, reply_markup=MainKeyboard.build_main_kb())
            return
        if user_id in admins:
            values = UserModel(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name= message.from_user.first_name,
                promo_code=None,
                subscription_end=None,
                is_blocked=False,
                role=User.Role.admin,
            )
            await UserDAO.add(session=session, values=values)
            await message.answer(
                "Привет администрации", reply_markup=MainKeyboard.build_main_kb()
            )
            return
        values = UserModel(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name= message.from_user.first_name,
                promo_code=None,
                subscription_end=None,
                is_blocked=False,
                role=User.Role.user,
            )
        await UserDAO.add(session=session, values=values)
        msg = start_message(message.from_user.first_name, MainKeyboard.get_user_kb_texts().get('oplata'))
        await message.answer(msg, reply_markup=MainKeyboard.build_main_kb())
        for admin in admins:
            await bot.send_message(admin,f'К тебе зашел новый юзер {message.from_user.first_name} [id: {message.from_user.id}]')

    except Exception as e:
        logger.error(
            f"Ошибка при выполнении команды /start для пользователя {message.from_user.id}: {e}"
        )
        await message.answer(
            "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте снова позже."
        )
